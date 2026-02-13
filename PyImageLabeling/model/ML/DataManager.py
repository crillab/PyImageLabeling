import json
from pathlib import Path
from collections import defaultdict
from PyImageLabeling.model.Core import Core
import cv2
import numpy as np

class DataManager(Core):
    """
    Data Manager Tool - inherits from Core
    Handles export to YOLO/COCO formats using existing annotations
    """
    
    def __init__(self):
        super().__init__()
        self.project_metadata = {}
    
    def ml_get_unlabeled_images(self):
        """
        Get list of images without any annotations
        Returns list of file paths
        """
        unlabeled = []
        
        for file_path in self.file_paths:
            image_item = self.image_items.get(file_path)
            
            # If image not loaded yet, consider it unlabeled
            if image_item is None:
                unlabeled.append(file_path)
                continue

            has_paint = bool(image_item.labeling_overlays)

            # Check if it has any annotations
            has_annotations = (
                image_item.image_rectangles or
                image_item.image_ellipses or
                image_item.image_polygons > 0 or
                has_paint
            )
            
            if not has_annotations:
                unlabeled.append(file_path)
        
        return unlabeled
    
    def get_annotation_count(self, file_path):
        """Get number of annotations for a specific image"""
        image_item = self.image_items.get(file_path)
        if image_item is None:
            return 0
        
        return (
            len(image_item.image_rectangles) +
            len(image_item.image_ellipses) +
            len(image_item.image_polygons)
        )
    
    def collect_all_annotations(self):
        all_annotations = {}
        
        for file_path in self.file_paths:
            image_item = self.image_items.get(file_path)
            
            if image_item is None:
                continue
            
            annotations = []
            
            # Collect rectangles
            for rect in image_item.image_rectangles:
                x = rect.get('x', 0)
                y = rect.get('y', 0)
                w = rect.get('width', 0)
                h = rect.get('height', 0)
                label_id = rect.get('label_id', 0)
                
                label_name = self._get_label_name(label_id)
                annotations.append((x, y, w, h, label_name))
            
            # Collect ellipses (as bounding boxes)
            for ellipse in image_item.image_ellipses:
                x = ellipse.get('x', 0)
                y = ellipse.get('y', 0)
                w = ellipse.get('width', 0)
                h = ellipse.get('height', 0)
                label_id = ellipse.get('label', 0)
                
                label_name = self._get_label_name(label_id)
                annotations.append((x, y, w, h, label_name))
            
            # Collect polygons (as bounding boxes)
            for polygon in image_item.image_polygons:
                points = polygon.get('points', [])
                label_id = polygon.get('label_id', 0)
                
                if points:
                    x_coords = [p['x'] for p in points]
                    y_coords = [p['y'] for p in points]
                    
                    x = min(x_coords)
                    y = min(y_coords)
                    w = max(x_coords) - x
                    h = max(y_coords) - y
                    
                    label_name = self._get_label_name(label_id)
                    annotations.append((x, y, w, h, label_name))
            
            if annotations:
                all_annotations[file_path] = annotations
        
        return all_annotations

    def _get_label_name(self, label_id):
        """Get label name from label_id"""
        if label_id in self.label_items:
            return self.label_items[label_id].get_name()
        return f"label_{label_id}"
    
    def ml_store_predictions(self, image_path, predictions):
        current_image_item = self.get_current_image_item()
        current_image_item_path  = current_image_item.path_image
        image_item = self.image_items.get(image_path)

        if image_item is None:
            image_item = self.image_items.get(current_image_item_path )
            if image_item is None:
                return False

        if not hasattr(image_item, "ml_predictions"):
            image_item.ml_predictions = []

        stored = []

        for pred in predictions:
            if len(pred) == 5:
                x, y, w, h, conf = pred
                label_id = self.current_label_id if hasattr(self, "current_label_id") else 0
            elif len(pred) == 6:
                x, y, w, h, conf, label_id = pred
            else:
                continue  # invalid prediction format

            stored.append({
                "x": float(x),
                "y": float(y),
                "width": float(w),
                "height": float(h),
                "confidence": float(conf),
                "label_id": int(label_id),
            })

        image_item.ml_predictions.extend(stored)
        return True
    
    def start_data_collection(self):
        """Collect all annotations for ML training"""
        all_annotations = self.collect_all_annotations()
        return [(path, anns) for path, anns in all_annotations.items()]