from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem, QProgressDialog, QMessageBox
from PyQt6.QtGui import QPen, QColor, QBrush, QPixmap, QImage
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyImageLabeling.model.Labeling.RectangleItem import RectangleItem
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision.models import (
    resnet18,           ResNet18_Weights,
    resnet34,           ResNet34_Weights,
    resnet50,           ResNet50_Weights,
    resnet101,           ResNet101_Weights,
    resnet152,           ResNet152_Weights,
    mobilenet_v3_small, MobileNet_V3_Small_Weights,
    efficientnet_b0,    EfficientNet_B0_Weights,
)

# ---------------------------------------------------------------------------
# Backbone registry  {name: (constructor, pretrained_weights)}
# Output channels are probed at build time — never hardcoded.
# ---------------------------------------------------------------------------
BACKBONE_REGISTRY = {
    "ResNet18":        (resnet18,           ResNet18_Weights.DEFAULT),
    "ResNet34":        (resnet34,           ResNet34_Weights.DEFAULT),
    "ResNet50":        (resnet50,           ResNet50_Weights.DEFAULT),
    "ResNet101": (resnet101, ResNet101_Weights.DEFAULT),
    "ResNet152": (resnet152, ResNet152_Weights.DEFAULT),
    "MobileNetV3-S":   (mobilenet_v3_small, MobileNet_V3_Small_Weights.DEFAULT),
    "EfficientNet-B0": (efficientnet_b0,    EfficientNet_B0_Weights.DEFAULT),
}
BACKBONE_NAMES   = list(BACKBONE_REGISTRY.keys())
DEFAULT_BACKBONE = "ResNet18"


def _build_backbone(backbone_name: str, pretrained: bool):
    """
    Instantiate the requested backbone and return (extractor_module, feat_channels).
    feat_channels is measured with a dummy forward pass — no hardcoding.
    """
    if backbone_name not in BACKBONE_REGISTRY:
        print(f"[backbone] Unknown '{backbone_name}', falling back to {DEFAULT_BACKBONE}")
        backbone_name = DEFAULT_BACKBONE

    constructor, weights_cls = BACKBONE_REGISTRY[backbone_name]
    weights = weights_cls if pretrained else None
    bb      = constructor(weights=weights)

    # ── ResNet family ────────────────────────────────────────────────────────
    if backbone_name in ("ResNet18", "ResNet34", "ResNet50", "ResNet101", "ResNet152"):
        children = list(bb.children())
        # stem(conv1+bn+relu+maxpool) = children[:4], then layer1..4
        layer1 = nn.Sequential(*children[:5])   # stem + layer1
        layer2 = children[5]
        layer3 = children[6]
        layer4 = children[7]

        class _ResNetExtractor(nn.Module):
            def __init__(self):
                super().__init__()
                self.layer1 = layer1
                self.layer2 = layer2
                self.layer3 = layer3
                self.layer4 = layer4
            def forward(self, x):
                x = self.layer1(x)
                x = self.layer2(x)
                x = self.layer3(x)
                return self.layer4(x)

        ext = _ResNetExtractor()

    # ── MobileNetV3-Small ────────────────────────────────────────────────────
    elif backbone_name == "MobileNetV3-S":
        features = bb.features   # Sequential of inverted-residual blocks

        class _MobileNetExtractor(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = features
            def forward(self, x):
                return self.features(x)

        ext = _MobileNetExtractor()

    # ── EfficientNet-B0 ──────────────────────────────────────────────────────
    elif backbone_name == "EfficientNet-B0":
        features = bb.features   # Sequential of MBConv blocks

        class _EfficientNetExtractor(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = features
            def forward(self, x):
                return self.features(x)

        ext = _EfficientNetExtractor()

    else:
        raise ValueError(f"Unhandled backbone: {backbone_name}")

    # Probe actual output channels with a dummy forward pass
    ext.eval()
    with torch.no_grad():
        dummy    = torch.zeros(1, 3, 224, 224)
        feat_ch  = ext(dummy).shape[1]
    print(f"[backbone] {backbone_name}: feat_channels={feat_ch}")
    return ext, feat_ch

try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    ALBUMENTATIONS_AVAILABLE = True
    print(f"Albumentations version: {A.__version__}")
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False
    print("Warning: Albumentations not installed. Using basic augmentation.")
    A = None
    ToTensorV2 = None


# ---------------------------------------------------------------------------
# Background training thread
# ---------------------------------------------------------------------------

class TrainingWorker(QThread):
    progress   = pyqtSignal(str)            # log messages  → console
    epoch_done = pyqtSignal(int, int, float) # current, total, loss → progress bar
    finished   = pyqtSignal()
    error      = pyqtSignal(str)

    def __init__(self, predictor, selected_paths=None):
        super().__init__()
        self.predictor      = predictor
        self.selected_paths = selected_paths

    def run(self):
        try:
            self.predictor.train_model_core(
                selected_paths  = self.selected_paths,
                epoch_callback  = self.epoch_done.emit,
                log_callback    = self.progress.emit,
            )
            self.finished.emit()
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

class ObjectDetectionDataset(Dataset):
    def __init__(self, image_paths, annotations_list, label_id_to_class,
                 image_size=416, augment=True):
        self.image_paths       = image_paths
        self.annotations_list  = annotations_list
        self.label_id_to_class = label_id_to_class
        self.image_size        = image_size
        self.augment           = augment
        self.use_albumentations = ALBUMENTATIONS_AVAILABLE

        if ALBUMENTATIONS_AVAILABLE:
            try:
                common = [
                    A.Resize(height=image_size, width=image_size),
                    A.Normalize(mean=[0.485, 0.456, 0.406],
                                std =[0.229, 0.224, 0.225]),
                    ToTensorV2(),
                ]
                aug = [A.HorizontalFlip(p=0.5),
                       A.RandomBrightnessContrast(0.2, 0.2, p=0.5)] if augment else []
                self.transform = A.Compose(
                    aug + common,
                    bbox_params=A.BboxParams(format='pascal_voc',
                                            label_fields=['labels']),
                )
            except Exception:
                self.use_albumentations = False

    def _basic_transform(self, image, boxes):
        h, w = image.shape[:2]
        image = cv2.resize(image, (self.image_size, self.image_size))
        if self.augment and np.random.random() > 0.5:
            image = cv2.flip(image, 1)
            boxes = [[self.image_size - b[2], b[1],
                      self.image_size - b[0], b[3]] for b in boxes]
        image = image.astype(np.float32) / 255.0
        image = (image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        image = torch.from_numpy(image).permute(2, 0, 1).float()
        sx, sy = self.image_size / w, self.image_size / h
        boxes  = [[b[0]*sx, b[1]*sy, b[2]*sx, b[3]*sy] for b in boxes]
        return image, boxes

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image = cv2.imread(self.image_paths[idx])
        if image is None:
            return (torch.zeros(3, self.image_size, self.image_size),
                    torch.zeros(1, 4),
                    torch.zeros(1, dtype=torch.int64))

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w  = image.shape[:2]

        boxes, labels = [], []
        for x, y, bw, bh, label_id in self.annotations_list[idx]:
            x1 = max(0, min(x,    w - 1))
            y1 = max(0, min(y,    h - 1))
            x2 = max(0, min(x+bw, w))
            y2 = max(0, min(y+bh, h))
            if (x2 - x1) >= 2 and (y2 - y1) >= 2:
                boxes.append([float(x1), float(y1), float(x2), float(y2)])
                labels.append(self.label_id_to_class.get(label_id, 0))

        if not boxes:
            boxes  = [[0.0, 0.0, 2.0, 2.0]]
            labels = [0]

        if not self.use_albumentations:
            image, boxes = self._basic_transform(image, boxes)
        else:
            try:
                t      = self.transform(image=image, bboxes=boxes, labels=labels)
                image  = t['image']
                boxes  = list(t.get('bboxes', [])) or [[0.0, 0.0, 2.0, 2.0]]
                labels = list(t.get('labels', [])) or [0]
            except Exception:
                self.use_albumentations = False
                image, boxes = self._basic_transform(image, boxes)

        return (image,
                torch.tensor(boxes,  dtype=torch.float32),
                torch.tensor(labels, dtype=torch.int64))


class SegmentationDataset(Dataset):
    def __init__(self, image_paths, masks, label_id_to_class,
                 image_size=416, augment=True):
        self.image_paths       = image_paths
        self.masks             = masks
        self.label_id_to_class = label_id_to_class
        self.image_size        = image_size
        self.augment           = augment

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image = cv2.imread(self.image_paths[idx])
        if image is None:
            return (torch.zeros(3, self.image_size, self.image_size),
                    torch.zeros(self.image_size, self.image_size, dtype=torch.long))

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mask  = self.masks[idx]

        image = cv2.resize(image, (self.image_size, self.image_size))
        mask  = cv2.resize(mask,  (self.image_size, self.image_size),
                           interpolation=cv2.INTER_NEAREST)

        if self.augment and np.random.random() > 0.5:
            image = cv2.flip(image, 1)
            mask  = cv2.flip(mask,  1)
        if self.augment and np.random.random() > 0.5:
            alpha = np.random.uniform(0.8, 1.2)
            beta  = np.random.randint(-20, 20)
            image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

        image = image.astype(np.float32) / 255.0
        image = (image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        image = torch.from_numpy(image).permute(2, 0, 1).float()

        mask_mapped = np.zeros_like(mask, dtype=np.uint8)
        for orig_id, class_id in self.label_id_to_class.items():
            mask_mapped[mask == orig_id] = class_id

        return image, torch.from_numpy(mask_mapped).long()


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class SegmentationHead(nn.Module):
    def __init__(self, in_channels=512, num_classes=2):
        super().__init__()
        self.up1  = nn.ConvTranspose2d(in_channels, 256, 4, 2, 1)
        self.bn1  = nn.BatchNorm2d(256)
        self.up2  = nn.ConvTranspose2d(256, 128, 4, 2, 1)
        self.bn2  = nn.BatchNorm2d(128)
        self.up3  = nn.ConvTranspose2d(128,  64, 4, 2, 1)
        self.bn3  = nn.BatchNorm2d(64)
        self.up4  = nn.ConvTranspose2d( 64,  32, 4, 2, 1)
        self.bn4  = nn.BatchNorm2d(32)
        self.final = nn.Conv2d(32, num_classes, 1)

    def forward(self, x):
        x = F.relu(self.bn1(self.up1(x)))
        x = F.relu(self.bn2(self.up2(x)))
        x = F.relu(self.bn3(self.up3(x)))
        x = F.relu(self.bn4(self.up4(x)))
        x = self.final(x)
        return F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)


class FastObjectDetectorWithSegmentation(nn.Module):
    def __init__(self, num_classes=2, pretrained=True, enable_segmentation=True,
                 backbone_name=DEFAULT_BACKBONE):
        super().__init__()
        self.backbone_name = backbone_name

        # Build backbone and measure its output channels automatically
        self.backbone, feat_ch = _build_backbone(backbone_name, pretrained)

        # Detection neck: always projects feat_ch → 256 → 128
        self.conv1 = nn.Conv2d(feat_ch, 256, 3, padding=1)
        self.bn1   = nn.BatchNorm2d(256)
        self.conv2 = nn.Conv2d(256, 128, 3, padding=1)
        self.bn2   = nn.BatchNorm2d(128)

        self.objectness      = nn.Conv2d(128, 1,           1)
        self.bbox_regressor  = nn.Conv2d(128, 4,           1)
        self.class_predictor = nn.Conv2d(128, num_classes, 1)

        self.enable_segmentation = enable_segmentation
        if enable_segmentation:
            self.segmentation_head = SegmentationHead(feat_ch, num_classes)

        self.grid_size   = 13
        self.num_classes = num_classes

    def forward(self, x):
        x4 = self.backbone(x)

        det = F.relu(self.bn1(self.conv1(x4)))
        det = F.relu(self.bn2(self.conv2(det)))

        obj  = torch.sigmoid(self.objectness(det))
        bbox = self.bbox_regressor(det)
        cls  = self.class_predictor(det)

        self.grid_size = obj.size(2)

        obj  = obj.permute(0, 2, 3, 1).contiguous()
        bbox = bbox.permute(0, 2, 3, 1).contiguous()
        cls  = cls.permute(0, 2, 3, 1).contiguous()

        seg = self.segmentation_head(x4) if self.enable_segmentation else None
        return obj, bbox, cls, seg

    def predict_boxes(self, objectness, bbox_pred, class_pred,
                      image_size=416, conf_threshold=0.5):
        batch_size = objectness.size(0)
        grid_size  = self.grid_size
        stride     = image_size / grid_size

        all_boxes, all_scores, all_classes = [], [], []

        for b in range(batch_size):
            boxes, scores, classes = [], [], []
            for i in range(grid_size):
                for j in range(grid_size):
                    confidence = objectness[b, i, j, 0].item()
                    if confidence < conf_threshold:
                        continue

                    class_scores = torch.softmax(class_pred[b, i, j, :], dim=0)
                    class_id     = torch.argmax(class_scores).item()
                    final_conf   = confidence * class_scores[class_id].item()
                    if final_conf < conf_threshold:
                        continue

                    dx, dy, dw, dh = bbox_pred[b, i, j, :].cpu().numpy()
                    cx = (j + 0.5 + dx) * stride
                    cy = (i + 0.5 + dy) * stride
                    w  = torch.exp(torch.tensor(dw)).item() * stride * 2
                    h  = torch.exp(torch.tensor(dh)).item() * stride * 2

                    x1 = max(0,          cx - w / 2)
                    y1 = max(0,          cy - h / 2)
                    x2 = min(image_size, cx + w / 2)
                    y2 = min(image_size, cy + h / 2)

                    boxes.append([x1, y1, x2, y2])
                    scores.append(final_conf)
                    classes.append(class_id)

            all_boxes.append(boxes)
            all_scores.append(scores)
            all_classes.append(classes)

        return all_boxes, all_scores, all_classes


# ---------------------------------------------------------------------------
# Main predictor
# ---------------------------------------------------------------------------

class MLPredictor(Core):
    def __init__(self):
        super().__init__()

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")

        self.model   = None
        self.trained = False

        self.image_size            = 416
        self.confidence_threshold  = 0.3
        self.nms_threshold         = 0.4
        self.segmentation_threshold = 0.5

        # FIX: training_mode must survive save/load
        self.training_mode       = None
        self.enable_segmentation = False
        self.batch_size          = 8
        self.num_epochs          = 50
        self.learning_rate       = 0.001
        self.backbone_name       = DEFAULT_BACKBONE
        self.use_pretrained      = True

        self.ml_predictions_current    = []
        self.ml_prediction_items       = []
        self.ml_segmentation_predictions = None

        self.label_id_to_class = {}
        self.class_to_label_id = {}

    # ------------------------------------------------------------------
    # Collate
    # ------------------------------------------------------------------

    @staticmethod
    def detection_collate_fn(batch):
        images, targets = [], []
        for img, boxes, labels in batch:
            img = img.float() if isinstance(img, torch.Tensor) \
                  else torch.from_numpy(img).float()
            images.append(img)
            targets.append({
                "boxes":  boxes  if isinstance(boxes,  torch.Tensor) else torch.tensor(boxes,  dtype=torch.float32),
                "labels": labels if isinstance(labels, torch.Tensor) else torch.tensor(labels, dtype=torch.long),
            })
        return torch.stack(images, 0), targets

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def collect_training_data(self, selected_paths=None):
        training_data = []
        paths = selected_paths if selected_paths is not None else self.file_paths

        for file_path in paths:
            image_item = self.image_items.get(file_path)
            if image_item is None:
                continue
            annotations = []
            for r in image_item.image_rectangles:
                annotations.append((r.get('x',0), r.get('y',0),
                                     r.get('width',0), r.get('height',0),
                                     r.get('label_id',0)))
            for e in image_item.image_ellipses:
                annotations.append((e.get('x',0), e.get('y',0),
                                     e.get('width',0), e.get('height',0),
                                     e.get('label',0)))
            for p in image_item.image_polygons:
                pts = p.get('points', [])
                lid = p.get('label_id', 0)
                if pts:
                    xs = [pt['x'] for pt in pts]
                    ys = [pt['y'] for pt in pts]
                    annotations.append((min(xs), min(ys),
                                         max(xs)-min(xs), max(ys)-min(ys), lid))
            if annotations:
                training_data.append((file_path, annotations))

        return training_data

    def collect_segmentation_data(self, selected_paths=None):
        segmentation_data = []
        paths = selected_paths if selected_paths is not None else self.file_paths
        print("COLLECTING SEGMENTATION DATA")

        for file_path in paths:
            image_item = self.image_items.get(file_path)
            if image_item is None or not hasattr(image_item, 'labeling_overlays'):
                continue
            img = cv2.imread(file_path)
            if img is None:
                continue
            height, width   = img.shape[:2]
            combined_mask   = np.full((height, width), 255, dtype=np.uint8)
            colors_found    = {}

            for label_id, overlay in image_item.labeling_overlays.items():
                pix = overlay.labeling_overlay_pixmap
                if pix is None or pix.isNull():
                    continue
                qimg = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                ptr  = qimg.bits()
                ptr.setsize(qimg.sizeInBytes())
                arr  = np.frombuffer(ptr, dtype=np.uint8).reshape(
                           (qimg.height(), qimg.width(), 4))
                painted = arr[:, :, 3] > 30
                if painted.shape != (height, width):
                    painted = cv2.resize(
                        painted.astype(np.uint8) * 255,
                        (width, height), interpolation=cv2.INTER_NEAREST) > 0
                cnt = np.count_nonzero(painted)
                if cnt > 0:
                    combined_mask[painted] = label_id
                    colors_found[label_id] = cnt
                    print(f"  Label {label_id}: {cnt} painted pixels")

            if colors_found:
                segmentation_data.append((file_path, combined_mask))

        print(f"FINAL SEGMENTATION DATA: {len(segmentation_data)} images")
        return segmentation_data

    # ------------------------------------------------------------------
    # Label helpers
    # ------------------------------------------------------------------

    def _get_label_name(self, label_id):
        if label_id in self.label_items:
            return self.label_items[label_id].get_name()
        return f"label_{label_id}"

    def _get_label_by_name(self, label_name):
        if label_name is None:
            return None, None
        for lid, item in self.label_items.items():
            if item.get_name() == label_name:
                return lid, item.get_color()
        return None, None

    # ------------------------------------------------------------------
    # Training — core (runs in worker thread)
    # ------------------------------------------------------------------

    def train_model_core(self, selected_paths=None,
                         epoch_callback=None, log_callback=None):

        def log(msg):
            print(msg)
            if log_callback:
                log_callback(msg)

        # FIX: collect once, with the same selected_paths throughout
        detection_data    = self.collect_training_data(selected_paths)
        segmentation_data = self.collect_segmentation_data(selected_paths)

        has_detection    = len(detection_data)    > 0
        has_segmentation = len(segmentation_data) > 0

        log(f"Detection annotations:    {len(detection_data)} images")
        log(f"Segmentation annotations: {len(segmentation_data)} images")

        if has_detection and has_segmentation:
            self.training_mode = "both"
        elif has_detection:
            self.training_mode = "detection"
        elif has_segmentation:
            self.training_mode = "segmentation"
        else:
            raise RuntimeError(
                "No training data available. Please annotate at least 1 image.")

        log(f"Training mode: {self.training_mode.upper()}")

        # ---- build label mapping ----------------------------------------
        all_label_ids = set()
        for _, anns in detection_data:
            for *_, label_id in anns:
                all_label_ids.add(label_id)
        for _, mask in segmentation_data:
            for lid in np.unique(mask).tolist():
                all_label_ids.add(int(lid))

        if not all_label_ids:
            raise RuntimeError(
                "No labels found in annotations. Please annotate with at least one label.")

        sorted_ids = sorted(all_label_ids)
        self.label_id_to_class = {}
        self.class_to_label_id = {}
        # Reserve class-0 for background (label_id=255)
        self.label_id_to_class[255] = 0
        self.class_to_label_id[0]   = 255
        for idx, orig_id in enumerate(sorted_ids):
            self.label_id_to_class[orig_id] = idx
            self.class_to_label_id[idx]     = orig_id

        num_classes = len(sorted_ids)
        log(f"Training with {num_classes} classes")
        for orig, cls in sorted(self.label_id_to_class.items()):
            name = self.label_items[orig].get_name() \
                   if orig in self.label_items else "background"
            log(f"  {orig} ('{name}') → class {cls}")

        max_cls = max(self.label_id_to_class.values())
        if max_cls >= num_classes:
            raise ValueError(
                f"Class ID {max_cls} exceeds num_classes {num_classes}")

        # ---- dataloaders ------------------------------------------------
        detection_loader = None
        if has_detection:
            ds = ObjectDetectionDataset(
                [p for p, _ in detection_data],
                [a for _, a in detection_data],
                self.label_id_to_class,
                self.image_size, augment=True)
            detection_loader = DataLoader(
                ds, batch_size=self.batch_size, shuffle=True,
                num_workers=0, collate_fn=MLPredictor.detection_collate_fn)
            log(f"Detection dataloader: {len(detection_loader)} batches")

        segmentation_loader = None
        if has_segmentation:
            ds = SegmentationDataset(
                [p for p, _ in segmentation_data],
                [m for _, m in segmentation_data],
                self.label_id_to_class,
                self.image_size, augment=True)
            segmentation_loader = DataLoader(
                ds, batch_size=self.batch_size, shuffle=True, num_workers=0)
            log(f"Segmentation dataloader: {len(segmentation_loader)} batches")

        # ---- model ------------------------------------------------------
        backbone   = getattr(self, 'backbone_name',  DEFAULT_BACKBONE)
        pretrained = getattr(self, 'use_pretrained', True)
        log(f"Backbone: {backbone} | Pretrained: {pretrained}")
        self.model = FastObjectDetectorWithSegmentation(
            num_classes=num_classes,
            pretrained=pretrained,
            enable_segmentation=has_segmentation,
            backbone_name=backbone)
        self.model = self.model.to(self.device)

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=getattr(self, 'learning_rate', 0.001))
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=self.num_epochs)

        log(f"Device: {self.device} | Epochs: {self.num_epochs} | "
            f"Batch: {self.batch_size} | LR: {optimizer.param_groups[0]['lr']}")

        self.model.train()
        best_loss = float('inf')

        for epoch in range(self.num_epochs):
            total_loss = num_batches = 0
            avg_obj = avg_bbox = avg_cls = 0.0

            # -- detection batches --
            if detection_loader:
                total_obj = total_bbox = total_cls = 0.0
                for images, targets in detection_loader:
                    images = images.to(self.device)
                    optimizer.zero_grad()

                    objectness, bbox_pred, class_pred, _ = self.model(images)
                    gs = self.model.grid_size

                    obj_t   = torch.zeros_like(objectness)
                    bbox_t  = torch.zeros_like(bbox_pred)
                    cls_t   = torch.zeros(images.size(0), gs, gs,
                                          dtype=torch.long, device=self.device)

                    for b in range(images.size(0)):
                        boxes  = targets[b]["boxes"].to(self.device)
                        labels = targets[b]["labels"].to(self.device)
                        for bi, box in enumerate(boxes):
                            if box.sum() <= 0:
                                continue
                            x1, y1, x2, y2 = box
                            cx = (x1 + x2) / 2;  cy = (y1 + y2) / 2
                            w  =  x2 - x1;        h  =  y2 - y1
                            gx = max(0, min(int(cx/self.image_size*gs), gs-1))
                            gy = max(0, min(int(cy/self.image_size*gs), gs-1))
                            stride = self.image_size / gs
                            obj_t[b, gy, gx, 0] = 1.0
                            bbox_t[b, gy, gx, 0] = (cx - gx*stride) / stride
                            bbox_t[b, gy, gx, 1] = (cy - gy*stride) / stride
                            bbox_t[b, gy, gx, 2] = torch.log(torch.clamp(w/stride/2, min=1e-6))
                            bbox_t[b, gy, gx, 3] = torch.log(torch.clamp(h/stride/2, min=1e-6))
                            lv = min(labels[bi].item(), num_classes - 1)
                            cls_t[b, gy, gx] = lv

                    pos = obj_t == 1;  neg = obj_t == 0
                    pos_loss = F.binary_cross_entropy(objectness[pos], obj_t[pos]) \
                               if pos.any() else torch.tensor(0., device=self.device)
                    neg_loss = F.binary_cross_entropy(objectness[neg], obj_t[neg])
                    obj_loss = 5.0 * pos_loss + 0.5 * neg_loss

                    obj_mask = obj_t > 0.5
                    if obj_mask.any():
                        bbox_loss = F.smooth_l1_loss(
                            bbox_pred[obj_mask.expand_as(bbox_pred)],
                            bbox_t   [obj_mask.expand_as(bbox_t)])
                        sq = obj_mask.squeeze(-1)
                        ct = torch.clamp(cls_t[sq], 0, num_classes - 1)
                        cls_loss = F.cross_entropy(class_pred[sq], ct)
                    else:
                        bbox_loss = cls_loss = torch.tensor(0., device=self.device)

                    loss = 2.0*obj_loss + 5.0*bbox_loss + 2.0*cls_loss
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 10.0)
                    optimizer.step()

                    total_loss += loss.item()
                    total_obj  += obj_loss.item()
                    total_bbox += bbox_loss.item()
                    total_cls  += cls_loss.item()
                    num_batches += 1

                n = len(detection_loader)
                avg_obj  = total_obj  / n
                avg_bbox = total_bbox / n
                avg_cls  = total_cls  / n

            # -- segmentation batches --
            if segmentation_loader:
                for images, masks in segmentation_loader:
                    images = images.to(self.device)
                    masks  = masks.to(self.device)
                    optimizer.zero_grad()
                    _, _, _, seg_pred = self.model(images)
                    if seg_pred is not None:
                        loss = F.cross_entropy(seg_pred, masks)
                        loss.backward()
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 10.0)
                        optimizer.step()
                        total_loss  += loss.item()
                        num_batches += 1

            scheduler.step()

            avg_loss = total_loss / num_batches if num_batches else 0.0
            if avg_loss < best_loss:
                best_loss = avg_loss

            if epoch_callback:
                epoch_callback(epoch + 1, self.num_epochs, avg_loss)

            if (epoch + 1) % 10 == 0 or epoch == 0:
                log(f"Epoch [{epoch+1}/{self.num_epochs}] "
                    f"Loss: {avg_loss:.4f} | Obj: {avg_obj:.4f} | "
                    f"BBox: {avg_bbox:.4f} | Cls: {avg_cls:.4f}")

        self.trained = True
        log(f"TRAINING COMPLETE! Best loss: {best_loss:.4f}")

    # ------------------------------------------------------------------
    # Training — public entry point (shows modal progress dialog)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Apply persisted ML settings → instance attributes
    # ------------------------------------------------------------------

    def _apply_ml_params(self):
        """Sync instance attributes from Utils.load_parameters() before training."""
        from PyImageLabeling.model.Utils import Utils
        params    = Utils.load_parameters()
        ml        = params.get("ml", {})

        self.num_epochs          = ml.get("num_epochs",           self.num_epochs)
        self.batch_size          = ml.get("batch_size",           self.batch_size)
        self.learning_rate       = ml.get("learning_rate",        self.learning_rate)
        self.image_size          = ml.get("image_size",           self.image_size)
        self.enable_segmentation = ml.get("enable_segmentation",  self.enable_segmentation)
        self.confidence_threshold = ml.get("confidence_threshold", self.confidence_threshold)
        self.nms_threshold        = ml.get("nms_threshold",        self.nms_threshold)
        self.use_pretrained       = ml.get("pretrained",           True)
        backbone = ml.get("backbone_name", DEFAULT_BACKBONE)
        if backbone not in BACKBONE_NAMES:
            print(f"[MLPredictor] Unknown backbone '{backbone}', using {DEFAULT_BACKBONE}")
            backbone = DEFAULT_BACKBONE
        self.backbone_name = backbone
        print(f"[MLPredictor] Params applied — backbone={self.backbone_name}, "
              f"epochs={self.num_epochs}, lr={self.learning_rate}, "
              f"img_size={self.image_size}, pretrained={self.use_pretrained}")

    def train_model(self, selected_paths=None):
        self._apply_ml_params()
        n_images = len(selected_paths) if selected_paths else len(self.file_paths)
        self._progress_dialog = QProgressDialog(
            f"Initializing training…\n{n_images} image(s) selected",
            None, 0, self.num_epochs)
        self._progress_dialog.setWindowTitle("Training Model")
        self._progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.setAutoReset(False)
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.resize(420, 120)
        self._progress_dialog.show()

        self._training_worker = TrainingWorker(self, selected_paths)
        self._training_worker.epoch_done.connect(self._on_epoch_done)
        self._training_worker.progress.connect(self._on_training_log)
        self._training_worker.finished.connect(self._on_training_finished)
        self._training_worker.error.connect(self._on_training_error)
        self._training_worker.start()

    def _on_epoch_done(self, current, total, loss):
        self._progress_dialog.setValue(current)
        self._progress_dialog.setLabelText(
            f"Epoch {current}/{total}  —  Loss: {loss:.4f}")

    def _on_training_log(self, message):
        print(message)

    def _on_training_finished(self):
        self._progress_dialog.close()
        QMessageBox.information(
            None, "Training Complete",
            f"Model trained successfully!\n"
            f"Mode: {self.training_mode}\n"
            f"Classes: {self.model.num_classes}")

    def _on_training_error(self, error_msg):
        self._progress_dialog.close()
        QMessageBox.critical(
            None, "Training Failed",
            f"Error during training:\n{error_msg}")

    # ------------------------------------------------------------------
    # Prediction — detection
    # ------------------------------------------------------------------

    @torch.no_grad()
    def predict_image(self, image_path, confidence_threshold=None):
        if not self.trained or self.model is None:
            return []
        # Only run if model was trained on detection data
        if self.training_mode not in ("detection", "both"):
            return []

        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold

        image = cv2.imread(image_path)
        if image is None:
            return []

        original_h, original_w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        img_r = cv2.resize(image_rgb, (self.image_size, self.image_size))
        img_n = (img_r.astype(np.float32)/255.0
                 - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        tensor = (torch.from_numpy(img_n)
                  .permute(2,0,1).float().unsqueeze(0).to(self.device))

        self.model.eval()
        objectness, bbox_pred, class_pred, _ = self.model(tensor)

        boxes_l, scores_l, classes_l = self.model.predict_boxes(
            objectness, bbox_pred, class_pred,
            image_size=self.image_size, conf_threshold=confidence_threshold)

        sx = original_w / self.image_size
        sy = original_h / self.image_size
        predictions = []

        for box, score, class_id in zip(boxes_l[0], scores_l[0], classes_l[0]):
            x1, y1, x2, y2 = box
            x1, y1 = int(x1*sx), int(y1*sy)
            x2, y2 = int(x2*sx), int(y2*sy)
            orig_lid   = self.class_to_label_id.get(int(class_id), 0)
            label_name = (self.label_items[orig_lid].get_name()
                          if orig_lid in self.label_items
                          else f"label_{orig_lid}")
            predictions.append((x1, y1, x2-x1, y2-y1, float(score), label_name))

        return predictions

    # ------------------------------------------------------------------
    # Prediction — segmentation
    # ------------------------------------------------------------------

    @torch.no_grad()
    def predict_segmentation(self, image_path, confidence_threshold=None):
        if not self.trained or self.model is None:
            return None
        # Only run if model was trained on segmentation data
        if self.training_mode not in ("segmentation", "both"):
            return None

        if confidence_threshold is None:
            confidence_threshold = self.segmentation_threshold

        image = cv2.imread(image_path)
        if image is None:
            return None

        original_h, original_w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        img_r = cv2.resize(image_rgb, (self.image_size, self.image_size))
        img_n = (img_r.astype(np.float32)/255.0
                 - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        tensor = (torch.from_numpy(img_n)
                  .permute(2,0,1).float().unsqueeze(0).to(self.device))

        self.model.eval()
        _, _, _, seg_pred = self.model(tensor)
        if seg_pred is None:
            return None

        seg_probs  = torch.softmax(seg_pred, dim=1)
        seg_cls    = torch.argmax(seg_probs, dim=1).squeeze(0).cpu().numpy()
        seg_conf   = torch.max(seg_probs,    dim=1)[0].squeeze(0).cpu().numpy()

        seg_cls  = cv2.resize(seg_cls.astype(np.uint8),
                              (original_w, original_h),
                              interpolation=cv2.INTER_NEAREST)
        seg_conf = cv2.resize(seg_conf,
                              (original_w, original_h),
                              interpolation=cv2.INTER_LINEAR)

        high_conf = seg_conf >= confidence_threshold
        predictions_by_label = {}

        for class_id, orig_lid in self.class_to_label_id.items():
            class_mask  = (seg_cls == class_id) & high_conf
            pixel_count = np.count_nonzero(class_mask)
            if pixel_count > 0:
                binary = np.zeros((original_h, original_w), dtype=np.uint8)
                binary[class_mask] = 255
                predictions_by_label[orig_lid] = binary
                print(f"  Predicted label {orig_lid} "
                      f"('{self._get_label_name(orig_lid)}'): "
                      f"{pixel_count} pixels above {confidence_threshold:.2f}")

        return predictions_by_label

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    def ml_visualize_predictions(self, predictions):
        self.ml_clear_predictions_visual()
        if not predictions:
            return

        for pred in predictions:
            if len(pred) == 6:
                x, y, w, h, confidence, label_name = pred
            elif len(pred) == 5:
                x, y, w, h, confidence = pred
                label_name = None
            else:
                continue

            _, color = self._get_label_by_name(label_name)
            if color is None:
                color = QColor(0, 100, 255, 180)
            else:
                color = QColor(color.red(), color.green(), color.blue(), 180)

            rect_item = QGraphicsRectItem(x, y, w, h)
            pen = QPen(color)
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            rect_item.setPen(pen)
            rect_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            rect_item.setZValue(10)
            self.zoomable_graphics_view.scene.addItem(rect_item)
            self.ml_prediction_items.append(rect_item)

            label_text = f"{label_name}: {confidence:.2f}" if label_name \
                         else f"{confidence:.2f}"
            text_item = QGraphicsTextItem(label_text)
            text_item.setPos(x + 5, y - 20)
            text_item.setDefaultTextColor(color)
            text_item.setZValue(10)
            self.zoomable_graphics_view.scene.addItem(text_item)
            self.ml_prediction_items.append(text_item)

    def ml_visualize_segmentation(self, predictions_by_label):
        if not predictions_by_label:
            print("No segmentation predictions to visualize")
            return

        self.ml_segmentation_predictions = predictions_by_label

        for label_id, mask in predictions_by_label.items():
            if not isinstance(mask, np.ndarray) or label_id == 255:
                continue

            h, w = mask.shape
            rgba = np.zeros((h, w, 4), dtype=np.uint8)

            if label_id in self.label_items:
                c = self.label_items[label_id].get_color()
                color = np.array([c.red(), c.green(), c.blue(), 120], dtype=np.uint8)
                label_name = self.label_items[label_id].get_name()
            else:
                color = np.array([255, 0, 0, 120], dtype=np.uint8)
                label_name = f"label_{label_id}"

            rgba[mask > 0] = color
            print(f"  Label {label_id} ('{label_name}'): "
                  f"{np.count_nonzero(mask > 0)} pixels (preview)")

            qimg    = QImage(rgba.data, w, h, w*4,
                             QImage.Format.Format_RGBA8888).copy()
            pixmap  = QPixmap.fromImage(qimg)
            item    = QGraphicsPixmapItem(pixmap)
            item.setZValue(9)
            self.zoomable_graphics_view.scene.addItem(item)
            self.ml_prediction_items.append(item)

    def ml_clear_predictions_visual(self):
        for item in self.ml_prediction_items[:]:
            try:
                if item.scene() is not None:
                    self.zoomable_graphics_view.scene.removeItem(item)
            except (RuntimeError, AttributeError):
                pass
        self.ml_prediction_items.clear()

    # ------------------------------------------------------------------
    # Accept predictions
    # ------------------------------------------------------------------

    def ml_accept_predictions(self, ml_predictions_current):
        """Convert bbox predictions into rectangle annotations."""
        if not ml_predictions_current:
            return 0

        current_image = self.current_image_item
        if current_image is None:
            return 0

        count = skipped = 0

        for pred in ml_predictions_current:
            if len(pred) == 6:
                x, y, w, h, confidence, label_name = pred
            elif len(pred) == 5:
                x, y, w, h, confidence = pred
                label_name = None
            else:
                continue

            predicted_label_id, predicted_color = self._get_label_by_name(label_name)
            if predicted_label_id is None or predicted_color is None:
                print(f"Warning: label '{label_name}' not found, skipping")
                skipped += 1
                continue

            rect_data = {
                "x": int(x), "y": int(y),
                "width": int(w), "height": int(h),
                "label_id": predicted_label_id,
            }
            current_image.image_rectangles.append(rect_data)

            rect_item = RectangleItem(
                rect_data["x"], rect_data["y"],
                rect_data["width"], rect_data["height"],
                predicted_color)
            rect_item.setZValue(2)
            rect_item.model_ref = rect_data
            rect_item.label_id  = predicted_label_id
            self.zoomable_graphics_view.scene.addItem(rect_item)
            count += 1

        print(f"Accepted {count} predictions"
              + (f", skipped {skipped}" if skipped else ""))

        current_image.update_labeling_overlay()
        self.controller.ml_update_stats()
        # FIX: clear the visual only after successfully writing annotations
        self.ml_clear_predictions_visual()

        return count

    def ml_accept_segmentation(self):
        """Paint segmentation predictions into their respective overlays."""
        preds = getattr(self, 'ml_segmentation_predictions', None)
        if not preds:
            print("No segmentation predictions to accept")
            return False

        current_image = self.current_image_item
        if current_image is None:
            print("No current image")
            return False

        print(f"Accepting segmentation for {len(preds)} label(s)…")

        for label_id, mask in preds.items():
            if label_id not in current_image.labeling_overlays:
                print(f"ERROR: No overlay for label {label_id}")
                continue

            overlay = current_image.labeling_overlays[label_id]
            if overlay.labeling_overlay_pixmap is None:
                print(f"ERROR: No pixmap for label {label_id}")
                continue

            if label_id not in self.label_items:
                print(f"ERROR: Label {label_id} not in label_items")
                continue

            c     = self.label_items[label_id].get_color()
            color = QColor(c.red(), c.green(), c.blue(), 255)

            h, w      = mask.shape
            painted   = mask > 0
            pix_count = np.count_nonzero(painted)
            if pix_count == 0:
                continue

            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[painted] = [color.red(), color.green(), color.blue(), 255]

            qimg   = QImage(rgba.data, w, h, w*4,
                            QImage.Format.Format_RGBA8888).copy()
            pixmap = QPixmap.fromImage(qimg)

            painter = overlay.get_painter()
            painter.drawPixmap(0, 0, pixmap)
            print(f"  Painted {pix_count} pixels → label {label_id} "
                  f"('{self._get_label_name(label_id)}')")

        current_image.update_labeling_overlay()
        self.ml_segmentation_predictions = None
        self.ml_clear_predictions_visual()
        return True

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    def save_model_file(self, directory):
        if not self.trained or self.model is None:
            return

        path = os.path.join(directory, "ml_model.pth")

        torch.save({
            'model_state_dict': self.model.state_dict(),

            'num_classes': self.model.num_classes,
            'backbone_name': getattr(self.model, "backbone_name", "resnet18"),
            'enable_segmentation': self.model.enable_segmentation,
            'enable_detection': getattr(self.model, "enable_detection", True),

            'label_id_to_class': self.label_id_to_class,
            'class_to_label_id': self.class_to_label_id,

            'training_mode': self.training_mode,
            'image_size': self.image_size,
            'confidence_threshold': self.confidence_threshold,
            'nms_threshold': self.nms_threshold,
            'segmentation_threshold': self.segmentation_threshold,

        }, path)

        print(f"ML model saved to {path}")

    def load_model_file(self, directory):
        path = os.path.join(directory, "ml_model.pth")

        if not os.path.exists(path):
            return False

        try:
            ck = torch.load(path, map_location=self.device)

            num_classes = ck.get('num_classes', 2)
            backbone = ck.get('backbone_name', 'resnet18')
            enable_seg = ck.get('enable_segmentation', True)
            enable_det = ck.get('enable_detection', True)

            self.model = FastObjectDetectorWithSegmentation(
                num_classes=num_classes,
                pretrained=False,  # ⚠️ NEVER True when loading
                enable_segmentation=enable_seg
            )

            # optional if you added backbone support
            if hasattr(self.model, "backbone_name"):
                self.model.backbone_name = backbone

            self.model.load_state_dict(ck['model_state_dict'])
            self.model = self.model.to(self.device)
            self.model.eval()
            self.label_id_to_class = ck.get('label_id_to_class', {})
            self.class_to_label_id = ck.get('class_to_label_id', {})

            self.image_size = ck.get('image_size', 416)
            self.confidence_threshold = ck.get('confidence_threshold', 0.3)
            self.nms_threshold = ck.get('nms_threshold', 0.4)
            self.segmentation_threshold = ck.get('segmentation_threshold', 0.5)
            self.training_mode = ck.get('training_mode', None)

            self.trained = True

            print(f"Model loaded successfully (backbone={backbone}, mode={self.training_mode})")
            return True

        except Exception as e:
            print(f"Error loading model: {e}")
            import traceback; traceback.print_exc()
            return False

    def load_image_for_training(self, path_image):
        if self.image_items.get(path_image) is not None:
            return
        from PyImageLabeling.model.Core import ImageItem
        image_item = ImageItem(
            self.view, self.controller, path_image,
            self.icon_button_files.get(path_image),
            self.labeling_overview_was_loaded,
            self.labeling_overview_file_paths,
        )
        self.image_items[path_image] = image_item

        base = os.path.basename(path_image)
        if base in self.left_rectangles:
            image_item.image_rectangles = self.left_rectangles.pop(base)
        if base in self.left_ellipses:
            image_item.image_ellipses   = self.left_ellipses.pop(base)
        if base in self.left_polygons:
            image_item.image_polygons   = self.left_polygons.pop(base)

        if self.label_items and self.current_label_item is not None:
            image_item.update_labeling_overlays(
                self.label_items,
                self.current_label_item.get_label_id())

        print(f"[load_image_for_training] Loaded {base}")

    def is_trained(self):
        return self.trained