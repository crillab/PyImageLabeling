"""
UPDATED MLPredictor.py with Paintbrush Segmentation Support

Key changes:
1. Collects paintbrush overlay data from image_item.labeling_overlays
2. Trains segmentation head on painted pixels
3. Predicts pixel-level segmentation masks
4. Returns predictions as QPixmap that can be merged with labeling_overlay
"""

from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtGui import QPen, QColor, QBrush, QPixmap, QImage, QPainter
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem
from PyImageLabeling.model.Labeling.RectangleItem import RectangleItem
import os
import cv2
import numpy as np
import pickle
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
from torchvision.models import resnet18, ResNet18_Weights
from torchvision.ops import nms

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    ALBUMENTATIONS_AVAILABLE = True
    albu_version = tuple(map(int, A.__version__.split('.')[:2]))
    print(f"Albumentations version: {A.__version__}")
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    print("Warning: Albumentations not installed. Using basic augmentation.")
    A = None
    ToTensorV2 = None


class ObjectDetectionDataset(Dataset):
    """Custom dataset for object detection training"""
    
    def __init__(self, image_paths, annotations_list, label_to_id, image_size=416, augment=True):
        self.image_paths = image_paths
        self.annotations_list = annotations_list
        self.label_to_id = label_to_id  # NEW: label mapping
        self.image_size = image_size
        self.augment = augment
        self.use_albumentations = ALBUMENTATIONS_AVAILABLE
        
        # Setup transforms as before...
        if ALBUMENTATIONS_AVAILABLE:
            try:
                if augment:
                    self.transform = A.Compose([
                        A.Resize(height=image_size, width=image_size),
                        A.HorizontalFlip(p=0.5),
                        A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
                        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                        ToTensorV2()
                    ], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['labels']))
                else:
                    self.transform = A.Compose([
                        A.Resize(height=image_size, width=image_size),
                        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                        ToTensorV2()
                    ], bbox_params=A.BboxParams(format='pascal_voc', label_fields=['labels']))
            except:
                self.use_albumentations = False
    
    def _basic_transform(self, image, boxes):
        """Fallback transform using OpenCV"""
        h, w = image.shape[:2]
        image = cv2.resize(image, (self.image_size, self.image_size))
        
        if self.augment and np.random.random() > 0.5:
            image = cv2.flip(image, 1)
            boxes = [[self.image_size - b[2], b[1], self.image_size - b[0], b[3]] for b in boxes]
        
        image = image.astype(np.float32) / 255.0
        image = (image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        image = torch.from_numpy(image).permute(2, 0, 1).float()
        
        scale_x = self.image_size / w
        scale_y = self.image_size / h
        boxes = [[b[0]*scale_x, b[1]*scale_y, b[2]*scale_x, b[3]*scale_y] for b in boxes]
        
        return image, boxes
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        annotations = self.annotations_list[idx]
        
        image = cv2.imread(image_path)
        if image is None:
            dummy_image = torch.zeros(3, self.image_size, self.image_size)
            dummy_boxes = torch.zeros(1, 4)
            dummy_labels = torch.zeros(1, dtype=torch.int64)
            return dummy_image, dummy_boxes, dummy_labels
            
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        
        boxes = []
        labels = []
        
        for x, y, box_w, box_h, label_name in annotations:
            x1 = max(0, min(x, w - 1))
            y1 = max(0, min(y, h - 1))
            x2 = max(0, min(x + box_w, w))
            y2 = max(0, min(y + box_h, h))
            
            if (x2 - x1) >= 2 and (y2 - y1) >= 2:
                boxes.append([float(x1), float(y1), float(x2), float(y2)])
                # FIX: Use actual label ID from label_name
                label_id = self.label_to_id.get(label_name, 0)
                labels.append(label_id)
        
        if len(boxes) == 0:
            boxes = [[0.0, 0.0, 2.0, 2.0]]
            labels = [0]
        
        if not self.use_albumentations:
            image, boxes = self._basic_transform(image, boxes)
            boxes = torch.tensor(boxes, dtype=torch.float32)
            labels = torch.tensor(labels, dtype=torch.int64)
            return image, boxes, labels
        
        try:
            transformed = self.transform(image=image, bboxes=boxes, labels=labels)
            image = transformed['image']
            boxes = transformed.get('bboxes', [])
            labels = transformed.get('labels', [])
            
            if len(boxes) == 0:
                boxes = [[0.0, 0.0, 2.0, 2.0]]
                labels = [0]
        except:
            if idx == 0:
                print("Albumentations failed, using basic transforms")
            self.use_albumentations = False
            image, boxes = self._basic_transform(image, boxes)
            
        if len(boxes) == 0:
            boxes = [[0.0, 0.0, 2.0, 2.0]]
            labels = [0]
            
        boxes = torch.tensor(boxes, dtype=torch.float32)
        labels = torch.tensor(labels, dtype=torch.int64)
        
        return image, boxes, labels


class SegmentationDataset(Dataset):
    """Dataset for segmentation training from paintbrush overlays"""
    
    def __init__(self, image_paths, masks, image_size=416, augment=True):
        self.image_paths = image_paths
        self.masks = masks
        self.image_size = image_size
        self.augment = augment
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        mask = self.masks[idx]  # numpy array [H, W] with class IDs
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            dummy_image = torch.zeros(3, self.image_size, self.image_size)
            dummy_mask = torch.zeros(self.image_size, self.image_size, dtype=torch.long)
            return dummy_image, dummy_mask
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize both image and mask
        image = cv2.resize(image, (self.image_size, self.image_size))
        mask = cv2.resize(mask, (self.image_size, self.image_size), 
                         interpolation=cv2.INTER_NEAREST)
        
        # Data augmentation
        if self.augment and np.random.random() > 0.5:
            # Horizontal flip
            image = cv2.flip(image, 1)
            mask = cv2.flip(mask, 1)
        
        if self.augment and np.random.random() > 0.5:
            # Brightness/contrast
            alpha = np.random.uniform(0.8, 1.2)
            beta = np.random.randint(-20, 20)
            image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        
        # Normalize image
        image = image.astype(np.float32) / 255.0
        image = (image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        image = torch.from_numpy(image).permute(2, 0, 1).float()
        
        # Convert mask to tensor
        mask = torch.from_numpy(mask).long()
        
        return image, mask


class SegmentationHead(nn.Module):
    """Segmentation head for pixel-level predictions"""
    
    def __init__(self, in_channels=512, num_classes=2):
        super().__init__()
        
        self.upsample1 = nn.ConvTranspose2d(in_channels, 256, kernel_size=4, stride=2, padding=1)
        self.bn1 = nn.BatchNorm2d(256)
        
        self.upsample2 = nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(128)
        
        self.upsample3 = nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        
        self.upsample4 = nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1)
        self.bn4 = nn.BatchNorm2d(32)
        
        self.final = nn.Conv2d(32, num_classes, kernel_size=1)
    
    def forward(self, x):
        x = F.relu(self.bn1(self.upsample1(x)))
        x = F.relu(self.bn2(self.upsample2(x)))
        x = F.relu(self.bn3(self.upsample3(x)))
        x = F.relu(self.bn4(self.upsample4(x)))
        x = self.final(x)
        x = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)
        return x


class FastObjectDetectorWithSegmentation(nn.Module):
    """Enhanced detector that supports BOTH bounding boxes AND segmentation"""
    
    def __init__(self, num_classes=2, pretrained=True, enable_segmentation=True):
        super().__init__()
        
        # Shared backbone
        if pretrained:
            self.backbone = resnet18(weights=ResNet18_Weights.DEFAULT)
        else:
            self.backbone = resnet18(weights=None)
        
        # Get intermediate features
        self.layer1 = nn.Sequential(*list(self.backbone.children())[:5])
        self.layer2 = list(self.backbone.children())[5]
        self.layer3 = list(self.backbone.children())[6]
        self.layer4 = list(self.backbone.children())[7]
        
        # Detection head
        self.conv1 = nn.Conv2d(512, 256, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(256)
        
        self.conv2 = nn.Conv2d(256, 128, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(128)
        
        self.objectness = nn.Conv2d(128, 1, kernel_size=1)
        self.bbox_regressor = nn.Conv2d(128, 4, kernel_size=1)
        self.class_predictor = nn.Conv2d(128, num_classes, kernel_size=1)
        
        # Segmentation head
        self.enable_segmentation = enable_segmentation
        if enable_segmentation:
            self.segmentation_head = SegmentationHead(512, num_classes)
        
        self.grid_size = 13
        self.num_classes = num_classes
    
    def forward(self, x):
        # Extract features
        x1 = self.layer1(x)
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        
        # Detection head
        det = F.relu(self.bn1(self.conv1(x4)))
        det = F.relu(self.bn2(self.conv2(det)))
        
        objectness = torch.sigmoid(self.objectness(det))
        bbox_pred = self.bbox_regressor(det)
        class_pred = self.class_predictor(det)
        
        self.grid_size = objectness.size(2)
        
        objectness = objectness.permute(0, 2, 3, 1).contiguous()
        bbox_pred = bbox_pred.permute(0, 2, 3, 1).contiguous()
        class_pred = class_pred.permute(0, 2, 3, 1).contiguous()
        
        # Segmentation head
        seg_pred = None
        if self.enable_segmentation:
            seg_pred = self.segmentation_head(x4)
        
        return objectness, bbox_pred, class_pred, seg_pred
    
    def predict_boxes(self, objectness, bbox_pred, class_pred, image_size=416, conf_threshold=0.5):
        """Convert network predictions to bounding boxes WITH classes"""
        batch_size = objectness.size(0)
        grid_size = self.grid_size
        stride = image_size / grid_size
        
        all_boxes = []
        all_scores = []
        all_classes = []
        
        for b in range(batch_size):
            boxes = []
            scores = []
            classes = []
            
            for i in range(grid_size):
                for j in range(grid_size):
                    confidence = objectness[b, i, j, 0].item()
                    
                    if confidence >= conf_threshold:
                        # Get predicted class
                        class_scores = torch.softmax(class_pred[b, i, j, :], dim=0)
                        class_id = torch.argmax(class_scores).item()
                        class_conf = class_scores[class_id].item()
                        
                        final_conf = confidence * class_conf
                        
                        if final_conf < conf_threshold:
                            continue
                        
                        dx, dy, dw, dh = bbox_pred[b, i, j, :].cpu().numpy()
                        
                        cx = (j + 0.5 + dx) * stride
                        cy = (i + 0.5 + dy) * stride
                        w = torch.exp(torch.tensor(dw)).item() * stride * 2
                        h = torch.exp(torch.tensor(dh)).item() * stride * 2
                        
                        x1 = max(0, cx - w / 2)
                        y1 = max(0, cy - h / 2)
                        x2 = min(image_size, cx + w / 2)
                        y2 = min(image_size, cy + h / 2)
                        
                        boxes.append([x1, y1, x2, y2])
                        scores.append(final_conf)
                        classes.append(class_id)
            
            all_boxes.append(boxes)
            all_scores.append(scores)
            all_classes.append(classes)
        
        return all_boxes, all_scores, all_classes


# Continue in next message due to length...


class MLPredictor(Core):
    """
    GPU-Accelerated ML Auto-Prediction Tool with Segmentation Support
    NOW SUPPORTS: Bounding boxes AND paintbrush pixel-level predictions
    """
    
    def __init__(self):
        super().__init__()
        
        # Device configuration
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        # ML model components
        self.model = None
        self.trained = False
        
        # Detection parameters
        self.image_size = 416
        self.confidence_threshold = 0.7
        self.nms_threshold = 0.4
        
        # Segmentation parameters (NEW)
        self.enable_segmentation = True
        self.segmentation_threshold = 0.5
        
        # Training parameters
        self.training_mode = None         
        self.enable_detection = False
        self.enable_segmentation = False
        self.batch_size = 8
        self.num_epochs = 50
        self.learning_rate = 0.001
        
        # Prediction storage
        self.ml_predictions_current = []
        self.ml_prediction_items = []
        self.ml_pending_predictions = {}
        self.ml_segmentation_pixmap = None  # NEW
        
        # Label mapping
        self.label_to_id = {}
        self.id_to_label = {}
        
        # Statistics
        self.ml_annotation_counter = 0
    
    @staticmethod
    def detection_collate_fn(batch):
        images = []
        targets = []

        for img, boxes, labels in batch:
            if isinstance(img, np.ndarray):
                img = torch.from_numpy(img)
            img = img.float()
            images.append(img)

            boxes = boxes if isinstance(boxes, torch.Tensor) else torch.tensor(boxes, dtype=torch.float32)
            labels = labels if isinstance(labels, torch.Tensor) else torch.tensor(labels, dtype=torch.long)

            targets.append({
                "boxes": boxes,
                "labels": labels
            })

        images = torch.stack(images, dim=0)
        return images, targets
    
    def collect_training_data(self):
        """Collect bounding box annotations"""
        training_data = []
        
        for file_path in self.file_paths:
            image_item = self.image_items.get(file_path)
            
            if image_item is None:
                continue
            
            annotations = []
            
            # Collect rectangles, ellipses, polygons as before
            for rect_data in image_item.image_rectangles:
                x = rect_data.get('x', 0)
                y = rect_data.get('y', 0)
                width = rect_data.get('width', 0)
                height = rect_data.get('height', 0)
                label_id = rect_data.get('label_id', 0)
                
                label_name = self._get_label_name(label_id)
                annotations.append((x, y, width, height, label_name))
            
            for ellipse_data in image_item.image_ellipses:
                x = ellipse_data.get('x', 0)
                y = ellipse_data.get('y', 0)
                width = ellipse_data.get('width', 0)
                height = ellipse_data.get('height', 0)
                label_id = ellipse_data.get('label', 0)
                
                label_name = self._get_label_name(label_id)
                annotations.append((x, y, width, height, label_name))
            
            for polygon_data in image_item.image_polygons:
                points = polygon_data.get('points', [])
                label_id = polygon_data.get('label_id', 0)
                
                if points:
                    x_coords = [p['x'] for p in points]
                    y_coords = [p['y'] for p in points]
                    
                    x = min(x_coords)
                    y = min(y_coords)
                    width = max(x_coords) - x
                    height = max(y_coords) - y
                    
                    label_name = self._get_label_name(label_id)
                    annotations.append((x, y, width, height, label_name))
            
            if annotations:
                training_data.append((file_path, annotations))
        
        return training_data
    
    def collect_segmentation_data(self):
        """
        Collect pixel-level annotations from paintbrush overlays
        DEBUG VERSION with extensive logging
        """
        segmentation_data = []
        
        print("\n" + "="*50)
        print("COLLECTING SEGMENTATION DATA")
        print("="*50)
        
        images_checked = 0
        images_with_overlay = 0
        images_with_pixmap = 0
        images_with_painted_pixels = 0
        
        for file_path in self.file_paths:
            images_checked += 1
            basename = os.path.basename(file_path)
            
            image_item = self.image_items.get(file_path)
            
            if image_item is None:
                print(f"✗ {basename}: image_item is None")
                continue
            
            # Check for get_labeling_overlay method
            if not hasattr(image_item, 'get_labeling_overlay'):
                print(f"✗ {basename}: no get_labeling_overlay() method")
                continue
            
            # Get the overlay
            try:
                labeling_overlay = image_item.get_labeling_overlay()
            except Exception as e:
                print(f"✗ {basename}: error calling get_labeling_overlay(): {e}")
                continue
            
            if labeling_overlay is None:
                print(f"✗ {basename}: get_labeling_overlay() returned None")
                continue
            
            images_with_overlay += 1
            
            # Check for pixmap
            if not hasattr(labeling_overlay, 'labeling_overlay_pixmap'):
                print(f"✗ {basename}: overlay has no labeling_overlay_pixmap attribute")
                continue
            
            overlay_pixmap = labeling_overlay.labeling_overlay_pixmap
            
            if overlay_pixmap is None:
                print(f"✗ {basename}: labeling_overlay_pixmap is None")
                continue
            
            if overlay_pixmap.isNull():
                print(f"✗ {basename}: labeling_overlay_pixmap.isNull() = True")
                continue
            
            images_with_pixmap += 1
            print(f"✓ {basename}: Found pixmap {overlay_pixmap.width()}x{overlay_pixmap.height()}")
            
            # Load the actual image
            img = cv2.imread(file_path)
            if img is None:
                print(f"✗ {basename}: Could not load image file")
                continue
            
            height, width = img.shape[:2]
            
            # Convert pixmap to numpy array
            try:
                qimg = overlay_pixmap.toImage()
                qimg = qimg.convertToFormat(QImage.Format.Format_ARGB32)
                
                ptr = qimg.bits()
                ptr.setsize(qimg.sizeInBytes())
                
                # Create numpy array [H, W, 4] (RGBA)
                arr = np.frombuffer(ptr, dtype=np.uint8).reshape((qimg.height(), qimg.width(), 4))
                
                # Check alpha channel for painted pixels
                alpha = arr[:, :, 3]
                painted_pixels = np.count_nonzero(alpha > 0)
                
                print(f"  → {painted_pixels} painted pixels found")
                
                if painted_pixels == 0:
                    print(f"✗ {basename}: No painted pixels (alpha channel all 0)")
                    continue
                
                images_with_painted_pixels += 1
                
                # Create mask
                # For now, use binary mask (1 = painted, 0 = background)
                mask = (alpha > 0).astype(np.uint8)
                
                # Resize if needed
                if mask.shape != (height, width):
                    mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
                
                segmentation_data.append((file_path, mask))
                print(f"✓ {basename}: Added to segmentation data")
                
            except Exception as e:
                print(f"✗ {basename}: Error processing pixmap: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print("\n" + "="*50)
        print(f"SUMMARY:")
        print(f"  Images checked: {images_checked}")
        print(f"  With overlay: {images_with_overlay}")
        print(f"  With pixmap: {images_with_pixmap}")
        print(f"  With painted pixels: {images_with_painted_pixels}")
        print(f"  FINAL SEGMENTATION DATA: {len(segmentation_data)} images")
        print("="*50 + "\n")
        
        return segmentation_data
    
    def _get_label_name(self, label_id):
        """Get label name from label_id"""
        if label_id in self.label_items:
            return self.label_items[label_id].get_name()
        return f"label_{label_id}"
    
    def train_model(self):  # ← REMOVED THE ARGUMENTS!
        """
        Train model on EITHER detection OR segmentation data
        Each image has only one type of annotation
        """
        # Collect both types of data INTERNALLY
        detection_data = self.collect_training_data()
        segmentation_data = self.collect_segmentation_data()
        
        if hasattr(self, "collect_segmentation_data"):
            segmentation_data = self.collect_segmentation_data()

        has_detection = len(detection_data) > 0
        has_segmentation = len(segmentation_data) > 0

        # -------------------------
        # Determine training mode
        # -------------------------
        if has_detection and not has_segmentation:
            self.training_mode = "detection"
            self.enable_detection = True
            self.enable_segmentation = False

        elif has_segmentation and not has_detection:
            self.training_mode = "segmentation"
            self.enable_detection = False
            self.enable_segmentation = True

        elif has_detection and has_segmentation:
            self.training_mode = "both"
            self.enable_detection = True
            self.enable_segmentation = True

        else:
            raise RuntimeError("No training data available.")

        print(f"Training mode set to: {self.training_mode}")
        
        # Build label mapping
        all_labels = set()
        for _, annotations in detection_data:
            for x, y, w, h, label_name in annotations:
                all_labels.add(label_name)
        
        # Add background class
        if not all_labels:
            all_labels = set(['default'])
        
        self.label_to_id = {label: idx + 1 for idx, label in enumerate(sorted(all_labels))}
        self.label_to_id['background'] = 0
        self.id_to_label = {idx: label for label, idx in self.label_to_id.items()}
        
        # Ensure we have enough classes for all label IDs
        max_label_id = max(self.label_items.keys()) if self.label_items else 0
        num_classes = max(len(self.label_to_id), max_label_id + 1)
        
        print(f"Training with {num_classes} classes: {list(self.label_to_id.keys())}")
        
        # Create detection dataset if we have detection data
        detection_loader = None
        if has_detection:
            image_paths = [path for path, _ in detection_data]
            annotations_list = [anns for _, anns in detection_data]
            
            train_dataset = ObjectDetectionDataset(
                image_paths,
                annotations_list,
                self.label_to_id,
                image_size=self.image_size,
                augment=True
            )
            
            detection_loader = DataLoader(
                train_dataset,
                batch_size=self.batch_size,
                shuffle=True,
                num_workers=0,
                collate_fn=MLPredictor.detection_collate_fn
            )
        
        # Create segmentation dataset if we have segmentation data
        segmentation_loader = None
        if has_segmentation:
            seg_image_paths = [path for path, _ in segmentation_data]
            seg_masks = [mask for _, mask in segmentation_data]
            
            seg_dataset = SegmentationDataset(
                seg_image_paths,
                seg_masks,
                image_size=self.image_size,
                augment=True
            )
            
            segmentation_loader = DataLoader(
                seg_dataset,
                batch_size=self.batch_size,
                shuffle=True,
                num_workers=0
            )
        
        # Initialize model
        self.model = FastObjectDetectorWithSegmentation(
            num_classes=num_classes,
            pretrained=True,
            enable_segmentation=has_segmentation  # Only enable seg head if we have seg data
        )
        self.model = self.model.to(self.device)
        
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.num_epochs)
        
        print("Training model...")
        if has_detection:
            print("  - Detection head: ENABLED")
        if has_segmentation:
            print("  - Segmentation head: ENABLED")
        print()
        
        self.model.train()
        
        for epoch in range(self.num_epochs):
            total_loss = 0
            total_det_loss = 0
            total_seg_loss = 0
            num_batches = 0
            
            # Train on detection data
            if detection_loader:
                for batch_idx, (images, targets) in enumerate(detection_loader):
                    images = images.to(self.device)
                    optimizer.zero_grad()
                    
                    objectness, bbox_pred, class_pred, seg_pred = self.model(images)
                    grid_size = self.model.grid_size
                    
                    # Detection losses
                    obj_target = torch.zeros_like(objectness)
                    bbox_target = torch.zeros_like(bbox_pred)
                    class_target = torch.zeros(
                        objectness.shape[0], grid_size, grid_size,
                        dtype=torch.long, device=self.device
                    )
                    
                    batch_size = images.size(0)
                    
                    for b in range(batch_size):
                        boxes = targets[b]["boxes"].to(self.device)
                        labels = targets[b]["labels"].to(self.device)
                        
                        for box_idx, box in enumerate(boxes):
                            if box.sum() <= 0:
                                continue
                            
                            x1, y1, x2, y2 = box
                            cx = (x1 + x2) / 2
                            cy = (y1 + y2) / 2
                            w = x2 - x1
                            h = y2 - y1
                            
                            grid_x = int(cx / self.image_size * grid_size)
                            grid_y = int(cy / self.image_size * grid_size)
                            grid_x = max(0, min(grid_x, grid_size - 1))
                            grid_y = max(0, min(grid_y, grid_size - 1))
                            
                            obj_target[b, grid_y, grid_x, 0] = 1.0
                            
                            stride = self.image_size / grid_size
                            bbox_target[b, grid_y, grid_x, 0] = (cx - grid_x * stride) / stride
                            bbox_target[b, grid_y, grid_x, 1] = (cy - grid_y * stride) / stride
                            bbox_target[b, grid_y, grid_x, 2] = torch.log(torch.clamp(w / stride / 2, min=1e-6))
                            bbox_target[b, grid_y, grid_x, 3] = torch.log(torch.clamp(h / stride / 2, min=1e-6))
                            
                            class_target[b, grid_y, grid_x] = labels[box_idx]
                    
                    obj_loss = F.binary_cross_entropy(objectness, obj_target)
                    
                    obj_mask = obj_target > 0.5
                    if obj_mask.any():
                        bbox_loss = F.smooth_l1_loss(
                            bbox_pred[obj_mask.expand_as(bbox_pred)],
                            bbox_target[obj_mask.expand_as(bbox_target)]
                        )
                        
                        class_pred_masked = class_pred[obj_mask.squeeze(-1)]
                        class_target_masked = class_target[obj_mask.squeeze(-1)]
                        cls_loss = F.cross_entropy(class_pred_masked, class_target_masked)
                    else:
                        bbox_loss = torch.tensor(0.0, device=self.device)
                        cls_loss = torch.tensor(0.0, device=self.device)
                    
                    det_loss = obj_loss + 5.0 * bbox_loss + 2.0 * cls_loss
                    
                    det_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
                    optimizer.step()
                    
                    total_loss += det_loss.item()
                    total_det_loss += det_loss.item()
                    num_batches += 1
            
            # Train on segmentation data
            if segmentation_loader:
                for batch_idx, (images, masks) in enumerate(segmentation_loader):
                    images = images.to(self.device)
                    masks = masks.to(self.device)
                    
                    optimizer.zero_grad()
                    
                    _, _, _, seg_pred = self.model(images)
                    
                    if seg_pred is not None:
                        # Segmentation loss (cross-entropy)
                        seg_loss = F.cross_entropy(seg_pred, masks)
                        
                        seg_loss.backward()
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=10.0)
                        optimizer.step()
                        
                        total_loss += seg_loss.item()
                        total_seg_loss += seg_loss.item()
                        num_batches += 1
            
            scheduler.step()
            
            avg_loss = total_loss / num_batches if num_batches > 0 else 0
            if (epoch + 1) % 10 == 0 or epoch == 0:
                det_avg = total_det_loss / len(detection_loader) if detection_loader else 0
                seg_avg = total_seg_loss / len(segmentation_loader) if segmentation_loader else 0
                print(f"Epoch [{epoch+1}/{self.num_epochs}], "
                    f"Total: {avg_loss:.4f}, "
                    f"Det: {det_avg:.4f}, "
                    f"Seg: {seg_avg:.4f}")
        
        self.trained = True
        print("\nTraining complete!")
        print(f"Model trained on:")
        print(f"  - {len(detection_data)} images with geometric shapes")
        print(f"  - {len(segmentation_data)} images with painted pixels")
    
    @torch.no_grad()
    def predict_image(self, image_path, confidence_threshold=None):
        """
        Predict bounding boxes.
        Only runs if training_mode allows detection.
        """

        if not self.trained or self.model is None:
            return []

        if not self.enable_detection:
            return []  # ← IMPORTANT FIX

        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold

        image = cv2.imread(image_path)
        if image is None:
            return []

        original_h, original_w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        image_resized = cv2.resize(image_rgb, (self.image_size, self.image_size))
        image_normalized = image_resized.astype(np.float32) / 255.0
        image_normalized = (image_normalized - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        image_tensor = torch.from_numpy(image_normalized).permute(2, 0, 1).float().unsqueeze(0).to(self.device)

        self.model.eval()

        objectness, bbox_pred, class_pred, _ = self.model(image_tensor)

        boxes_list, scores_list, classes_list = self.model.predict_boxes(
            objectness,
            bbox_pred,
            class_pred,
            image_size=self.image_size,
            conf_threshold=confidence_threshold
        )

        boxes = boxes_list[0]
        scores = scores_list[0]
        classes = classes_list[0]

        if len(boxes) == 0:
            return []

        scale_x = original_w / self.image_size
        scale_y = original_h / self.image_size

        predictions = []

        for box, score, cls in zip(boxes, scores, classes):
            x1, y1, x2, y2 = box

            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)

            w = x2 - x1
            h = y2 - y1

            label_name = self.id_to_label.get(int(cls), f"class_{cls}")

            predictions.append((x1, y1, w, h, float(score), label_name))

        return predictions
    
    @torch.no_grad()
    def predict_segmentation(self, image_path, confidence_threshold=None):
        """
        Predict pixel-level segmentation mask
        RESPECTS CONFIDENCE THRESHOLD - only returns pixels above threshold
        """
        if not self.trained or self.model is None:
            return None

        if not self.enable_segmentation:
            return None

        if confidence_threshold is None:
            confidence_threshold = self.segmentation_threshold

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return None

        original_h, original_w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Preprocess
        image_resized = cv2.resize(image_rgb, (self.image_size, self.image_size))
        image_normalized = image_resized.astype(np.float32) / 255.0
        image_normalized = (image_normalized - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        image_tensor = torch.from_numpy(image_normalized).permute(2, 0, 1).float().unsqueeze(0).to(self.device)

        # Set model to eval mode
        self.model.eval()

        # Inference
        _, _, _, seg_pred = self.model(image_tensor)

        if seg_pred is None:
            return None

        # Convert to probabilities
        seg_probs = torch.softmax(seg_pred, dim=1)  # [1, num_classes, H, W]
        seg_classes = torch.argmax(seg_probs, dim=1).squeeze(0).cpu().numpy()  # [H, W]
        seg_confidence = torch.max(seg_probs, dim=1)[0].squeeze(0).cpu().numpy()  # [H, W]

        # Resize to original size
        seg_classes = cv2.resize(seg_classes.astype(np.uint8), (original_w, original_h),
                                interpolation=cv2.INTER_NEAREST)
        seg_confidence = cv2.resize(seg_confidence, (original_w, original_h),
                                interpolation=cv2.INTER_LINEAR)

        # CRITICAL: Create mask that respects confidence threshold
        # Only include pixels where:
        # 1. class_id > 0 (not background)
        # 2. confidence >= threshold
        segmentation_mask = np.zeros((original_h, original_w), dtype=np.uint8)
        
        # Apply confidence threshold
        high_confidence = seg_confidence >= confidence_threshold
        foreground = seg_classes > 0
        
        # Combine both conditions
        valid_pixels = high_confidence & foreground
        segmentation_mask[valid_pixels] = 255
        
        pixel_count = np.count_nonzero(segmentation_mask)
        print(f"Predicted {pixel_count} pixels above confidence {confidence_threshold:.2f}")
        
        return segmentation_mask
    
    def ml_visualize_predictions(self, predictions):
        """Draw bounding box predictions on canvas"""
        self.ml_clear_predictions_visual()
        
        if not predictions:
            return
        
        for prediction in predictions:
            # Handle both old (5) and new (6) format
            if len(prediction) == 6:
                x, y, w, h, confidence, label_name = prediction
            elif len(prediction) == 5:
                x, y, w, h, confidence = prediction
                label_name = None
            else:
                continue
            
            # Create dashed blue rectangle
            rect_item = QGraphicsRectItem(x, y, w, h)
            
            pen = QPen(QColor(0, 100, 255, 180))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            rect_item.setPen(pen)
            rect_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            rect_item.setZValue(10)
            
            self.zoomable_graphics_view.scene.addItem(rect_item)
            self.ml_prediction_items.append(rect_item)
            
            # Add label
            if label_name:
                label_text = f"{label_name}: {confidence:.2f}"
            else:
                label_text = f"{confidence:.2f}"
            
            text_item = QGraphicsTextItem(label_text)
            text_item.setPos(x + 5, y - 20)
            text_item.setDefaultTextColor(QColor(0, 100, 255))
            text_item.setZValue(10)
            
            self.zoomable_graphics_view.scene.addItem(text_item)
            self.ml_prediction_items.append(text_item)
    
    def ml_visualize_segmentation(self, segmentation_mask):
        """
        Display segmentation prediction as semi-transparent overlay
        PROPERLY CLEARS OLD PREDICTIONS FIRST
        """
        if segmentation_mask is None:
            print("✗ No segmentation mask to visualize")
            return

        if not isinstance(segmentation_mask, np.ndarray):
            print("✗ Segmentation mask is not a numpy array")
            return

        h, w = segmentation_mask.shape
        
        # Create RGBA array
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        
        # Get current label color with semi-transparency for preview
        if self.current_label_item is None:
            print("Warning: No label selected, using red")
            color = np.array([255, 0, 0, 120], dtype=np.uint8)
        else:
            base_color = self.current_label_item.get_color()
            color = np.array([base_color.red(), base_color.green(), base_color.blue(), 120], dtype=np.uint8)
        
        # Set color where mask > 0
        mask_bool = segmentation_mask > 0
        rgba[mask_bool] = color
        
        pixel_count = np.count_nonzero(mask_bool)
        print(f"✓ Displaying {pixel_count} predicted pixels (semi-transparent preview)")
        
        # Convert to QImage
        qimg = QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        
        # Store pixmap
        self.ml_segmentation_pixmap = QPixmap.fromImage(qimg)
        
        segmentation_preview_item = QGraphicsPixmapItem(self.ml_segmentation_pixmap)
        segmentation_preview_item.setZValue(9)
        
        self.zoomable_graphics_view.scene.addItem(segmentation_preview_item)
        
        # Store reference for clearing
        self.ml_prediction_items.append(segmentation_preview_item)
    
    def ml_clear_predictions_visual(self):
        """Remove prediction graphics from scene"""
        for item in self.ml_prediction_items:
            self.zoomable_graphics_view.scene.removeItem(item)
        self.ml_prediction_items = []
    
    def ml_accept_predictions(self, ml_predictions_current):
        """Convert current bounding box predictions to rectangle annotations"""
        if not ml_predictions_current:
            return 0

        if self.current_label_item is None:
            return 0

        current_image = self.current_image_item
        if current_image is None:
            return 0

        label_id = self.current_label_item.label_id
        color = self.current_label_item.get_color()

        count = 0

        for prediction in ml_predictions_current:
            if len(prediction) == 6:
                x, y, w, h, confidence, label_name = prediction
            elif len(prediction) == 5:
                x, y, w, h, confidence = prediction
            else:
                continue

            rect_data = {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "label_id": label_id
            }

            current_image.image_rectangles.append(rect_data)

            rect_item = RectangleItem(
                rect_data["x"],
                rect_data["y"],
                rect_data["width"],
                rect_data["height"],
                color
            )
            rect_item.setZValue(2)
            rect_item.model_ref = rect_data
            rect_item.label_id = label_id

            self.zoomable_graphics_view.scene.addItem(rect_item)

            count += 1

        current_image.update_labeling_overlay()
        self.controller.ml_update_stats()

        self.ml_predictions_current = []
        self.ml_clear_predictions_visual()

        path = current_image.path_image
        if path in self.ml_pending_predictions:
            del self.ml_pending_predictions[path]

        return count
    
    def ml_accept_segmentation(self):
        """
        Accept segmentation: Paint PERMANENTLY to labeling overlay
        ENSURES pixels are saved and visible after acceptance
        """
        if self.ml_segmentation_pixmap is None:
            print("✗ No segmentation to accept")
            return False

        current_image = self.current_image_item
        if current_image is None:
            print("✗ No current image")
            return False

        labeling_overlay = current_image.get_labeling_overlay()
        if labeling_overlay is None:
            print("✗ No labeling overlay")
            return False

        # Get dimensions
        h = self.ml_segmentation_pixmap.height()
        w = self.ml_segmentation_pixmap.width()
        
        # Get current label OPAQUE color
        if self.current_label_item is None:
            opaque_color = QColor(255, 0, 0, 255)
        else:
            base_color = self.current_label_item.get_color()
            opaque_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 255)
        
        # Convert preview to numpy
        preview_img = self.ml_segmentation_pixmap.toImage()
        preview_img = preview_img.convertToFormat(QImage.Format.Format_ARGB32)
        
        ptr = preview_img.bits()
        ptr.setsize(preview_img.sizeInBytes())
        preview_arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4))
        
        # Find painted pixels
        painted_mask = preview_arr[:, :, 3] > 0
        pixel_count = np.count_nonzero(painted_mask)
        
        print(f"Accepting {pixel_count} pixels to permanent overlay...")
        
        # Create OPAQUE version for permanent storage
        opaque_arr = np.zeros((h, w, 4), dtype=np.uint8)
        opaque_arr[painted_mask] = [opaque_color.red(), opaque_color.green(), opaque_color.blue(), 255]
        
        # Convert to QPixmap
        opaque_img = QImage(opaque_arr.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
        opaque_pixmap = QPixmap.fromImage(opaque_img)
        
        painter = labeling_overlay.get_painter()
        painter.drawPixmap(0, 0, opaque_pixmap)
        # Don't end the painter - overlay manages it
        
        # Update overlay
        current_image.update_labeling_overlay()
        
        return True
    
    def save_model_file(self, directory):
        """Save ML model to file"""
        if not self.trained or self.model is None:
            return
        
        model_path = os.path.join(directory, "ml_model.pth")
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'label_to_id': self.label_to_id,
            'id_to_label': self.id_to_label,
            'num_classes': len(self.label_to_id),
            'image_size': self.image_size,
            'confidence_threshold': self.confidence_threshold,
            'nms_threshold': self.nms_threshold,
            'enable_segmentation': self.enable_segmentation,
            'segmentation_threshold': self.segmentation_threshold,
        }, model_path)
        
        print(f"ML model saved to {model_path}")
    
    def load_model_file(self, directory):
        """Load ML model from file"""
        model_path = os.path.join(directory, "ml_model.pth")
        
        if not os.path.exists(model_path):
            return False
        
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            
            self.label_to_id = checkpoint.get('label_to_id', {})
            self.id_to_label = checkpoint.get('id_to_label', {})
            num_classes = checkpoint.get('num_classes', 2)
            
            self.model = FastObjectDetectorWithSegmentation(
                num_classes=num_classes,
                pretrained=False,
                enable_segmentation=checkpoint.get('enable_segmentation', True)
            )
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model = self.model.to(self.device)
            self.model.eval()
            
            self.image_size = checkpoint.get('image_size', 416)
            self.confidence_threshold = checkpoint.get('confidence_threshold', 0.7)
            self.nms_threshold = checkpoint.get('nms_threshold', 0.4)
            self.enable_segmentation = checkpoint.get('enable_segmentation', True)
            self.segmentation_threshold = checkpoint.get('segmentation_threshold', 0.5)
            
            self.trained = True
            
            print(f"ML model loaded successfully with {num_classes} classes")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def is_trained(self):
        """Check if model is trained"""
        return self.trained
    
    # Legacy compatibility methods
    def calculate_iou(self, box1, box2):
        """Calculate Intersection over Union"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0
