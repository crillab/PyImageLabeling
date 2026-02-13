from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt
import sys
import os
import numpy as np
import torch
import cv2
from PyQt6.QtGui import QImage
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'

from PyImageLabeling.controller.Events import Events
from PyImageLabeling.model.ML.MLPredictor import MLPredictor

class MLEvents(Events):
    def __init__(self):
        super().__init__()
        self.ml_predictions_current = []  # Current predictions for active image
        self.ml_annotation_counter = 0 

    def ml_collect_training_data(self):
        return self.model.start_data_collection()

    def save_project(self, project_file):
        return self.model.start_project_load(project_file)
    
    def ml_predictor_start(self, image_path, confidence_threshold=0.7):
        return self.model.predict_image(image_path, confidence_threshold)

    def ml_train_model(self):
        """Train the ML model on current annotations (detection + segmentation)"""
        print("STARTING ML TRAINING")
        # Collect both types of data

        self.ml_predictions_current = []
        if hasattr(self.model, 'ml_segmentation_pixmap'):
            self.model.ml_segmentation_pixmap = None
        if hasattr(self.model, 'ml_clear_predictions_visual'):
            self.model.ml_clear_predictions_visual()
            
        if hasattr(self.model, 'predictor'):
            self.model.predictor.trained = False
            self.model.predictor.label_id_to_class = {}
            self.model.predictor.class_to_label_id = {}
            self.model.predictor.model = None 
        
        detection_data = self.ml_collect_training_data()

        segmentation_data = []
        if hasattr(self.model, 'collect_segmentation_data'):
            print("Collecting segmentation data...")
            segmentation_data = self.model.collect_segmentation_data()
        else:
            print("WARNING: model does not have collect_segmentation_data() method")
        
        total_data = len(detection_data) + len(segmentation_data)
        
        print(f"Collected data:")
        print(f"Detection: {len(detection_data)} images")
        print(f"Segmentation: {len(segmentation_data)} images")
        print(f"Total: {total_data} images")
        
        if total_data < 1:
            QMessageBox.warning(
                self.view,
                "Insufficient Data",
                f"Please annotate at least 1 image before training.\n\n"
                f"Found:\n"
                f"  - {len(detection_data)} images with geometric shapes\n"
                f"  - {len(segmentation_data)} images with painted pixels"
            )
            return
        
        # Show progress dialog
        progress = QProgressDialog("Training ML model...", None, 0, 100, self.view)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(10)
        
        try:
            self.model.train_model()
            
            progress.setValue(100)
            
            # Update UI
            self.ml_update_status()
            
            QMessageBox.information(
                self.view,
                "Training Complete",
                f"Detection data: {len(detection_data)} images\n"
                f"Segmentation data: {len(segmentation_data)} images\n"
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self.view,
                "Training Failed",
                f"Failed to train model:\n{str(e)}\n\nCheck console for details."
            )
        finally:
            progress.close()
    
    def ml_predict_current(self):
        """
        Generate predictions for current image
        """
        if not self.model.is_trained():
            QMessageBox.information(
                self.view, "Model Not Trained",
                "Please train the model first by clicking 'Train Model'."
            )
            return
        
        current_image_item = self.model.get_current_image_item()
        if current_image_item is None:
            return
        
        current_image_path = current_image_item.path_image
        if not current_image_path:
            return
        
        # clear old predictions FIRST
        self.model.ml_clear_predictions_visual()
        self.ml_predictions_current = []
        if hasattr(self.model, 'ml_segmentation_pixmap'):
            self.model.ml_segmentation_pixmap = None
        
        confidence = self.view.ml_confidence_slider.value() / 100.0
        self.view.statusBar().showMessage(f"Generating predictions (confidence: {confidence:.2f})...")
        
        # Check capabilities
        has_segmentation = (hasattr(self.model.model, 'enable_segmentation') and 
                        self.model.model.enable_segmentation)
        
        predictions = []
        segmentation = None
        
        # Try detection prediction
        if hasattr(self.model, 'enable_detection') and self.model.enable_detection:
            try:
                predictions = self.ml_predictor_start(current_image_path, confidence)
                if predictions:
                    self.ml_predictions_current = predictions
                    self.model.ml_visualize_predictions(predictions)
                    print(f"✓ Detection: {len(predictions)} boxes")
                else : 
                    print("No predictions after thresholding")
            except Exception as e:
                print(f"Detection prediction failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Try segmentation prediction
        if has_segmentation:
            try:
                segmentation = self.model.predict_segmentation(current_image_path, confidence)
                if segmentation is not None and np.any(segmentation > 0):
                    self.model.ml_visualize_segmentation(segmentation)
                    print(f"✓ Segmentation: displayed on screen")
            except Exception as e:
                print(f"Segmentation prediction failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Update status bar
        parts = []
        if predictions:
            parts.append(f"{len(predictions)} boxes")
        if segmentation is not None and np.any(segmentation > 0):
            parts.append("segmentation")
        
        if parts:
            self.view.statusBar().showMessage(f"Generated {' + '.join(parts)} (confidence: {confidence:.2f})")
        else:
            self.view.statusBar().showMessage(f"No predictions found (confidence: {confidence:.2f})")
    
    def ml_accept_predictions(self):
        """
        Accept both box predictions AND segmentation
        CLEARS predictions after acceptance
        """
        accepted_boxes = 0
        accepted_segmentation = False
        
        # Accept bounding boxes
        if self.ml_predictions_current:
            accepted_boxes = self.model.ml_accept_predictions(self.ml_predictions_current)
            self.ml_predictions_current = []
        
        # Accept segmentation
        if hasattr(self.model, 'ml_segmentation_pixmap') and self.model.ml_segmentation_pixmap is not None:
            accepted_segmentation = self.model.ml_accept_segmentation()
        
        # Clear ALL predictions from scene
        self.model.ml_clear_predictions_visual()
        
        if accepted_boxes == 0 and not accepted_segmentation:
            QMessageBox.information(
                self.view,
                "No Predictions",
                "No predictions to accept. Generate predictions first."
            )
            return
        
        # Update stats
        self.ml_update_stats()
        
        # Build message
        message_parts = []
        if accepted_boxes > 0:
            message_parts.append(f"{accepted_boxes} boxes")
        if accepted_segmentation:
            message_parts.append("segmentation")
        
        self.view.statusBar().showMessage(
            f"✓ Accepted {' and '.join(message_parts)} as permanent annotations"
        )
    
    def ml_clear_predictions(self):
        """
        Clear all predictions from current image
        """
        # Clear boxes
        self.ml_predictions_current = []
        
        # Clear segmentation
        if hasattr(self.model, 'ml_segmentation_pixmap'):
            self.model.ml_segmentation_pixmap = None
        
        # Clear visual items from scene
        self.model.ml_clear_predictions_visual()
        
        self.view.statusBar().showMessage("Predictions cleared")
    
    def ml_toggle_predictions(self, state):
        """Toggle visibility of predictions"""
        show = (state == Qt.CheckState.Checked.value)
        # Update visualization
        if show:
            self.model.ml_visualize_predictions(self.ml_predictions_current)
        else:
            self.model.ml_clear_predictions_visual()
    
    def ml_update_confidence(self, value):
        """
        Update confidence threshold and REFRESH predictions if they exist
        """
        confidence = value / 100.0
        self.view.ml_confidence_label.setText(f"{confidence:.2f}")
        
        # If we have an active image and predictions are shown, refresh them
        if self.model.get_current_image_item() is not None:
            # Check if we should refresh predictions
            should_refresh = False
            
            # Check for box predictions
            if self.ml_predictions_current:
                should_refresh = True
            
            # Check for segmentation predictions
            if hasattr(self.model, 'ml_segmentation_pixmap') and self.model.ml_segmentation_pixmap is not None:
                should_refresh = True
            
            # Refresh if needed
            if should_refresh:
                print(f"Refreshing predictions with new confidence: {confidence:.2f}")
                self.ml_predict_current()
    
    def ml_update_status(self):
        """Update ML status in status bar"""
        if self.model.is_trained():
            self.view.ml_status_label.setText("ML: Trained ✓")
            self.view.ml_status_label.setStyleSheet("color: green;")
        else:
            self.view.ml_status_label.setText("ML: Not trained")
            self.view.ml_status_label.setStyleSheet("color: gray;")

    def ml_update_stats(self):
        """Update the ML stats label with current annotation counts"""
        annotated_images = 0
        total_annotations = 0

        for file_path in self.model.file_paths:
            image_item = self.model.image_items.get(file_path)
            if not image_item:
                continue

            rect_count = len(image_item.image_rectangles)
            ellipse_count = len(image_item.image_ellipses)
            polygon_count = len(image_item.image_polygons)

            paint_instances = 0

            if hasattr(image_item, "labeling_overlays"):
                for overlay in image_item.labeling_overlays.values():
                    pixmap = overlay.labeling_overlay_pixmap
                    if pixmap is None or pixmap.isNull():
                        continue

                    qimg = pixmap.toImage().convertToFormat(
                        QImage.Format.Format_Grayscale8
                    )

                    h = qimg.height()
                    w = qimg.width()
                    bpl = qimg.bytesPerLine()

                    ptr = qimg.bits()
                    ptr.setsize(h * bpl)

                    arr = np.frombuffer(ptr, np.uint8).reshape((h, bpl))
                    mask = arr[:, :w]

                    if np.count_nonzero(mask) == 0:
                        continue

                    binary = (mask > 0).astype(np.uint8)
                    num_labels, _ = cv2.connectedComponents(binary)

                    paint_instances += max(0, num_labels - 1)

            image_total = (
                rect_count +
                ellipse_count +
                polygon_count +
                paint_instances
            )

            if image_total > 0:
                annotated_images += 1
                total_annotations += image_total

        model_status = "Trained ✓" if self.model.is_trained() else "Not trained"
        color = "green" if self.model.is_trained() else "gray"

        self.view.ml_stats_label.setText(
            f"Annotated Images: {annotated_images}\n"
            f"Total Annotations: {total_annotations}\n"
            f"Model Status: {model_status}"
        )

        self.view.ml_status_label.setText(f"ML: {model_status}")
        self.view.ml_status_label.setStyleSheet(f"color: {color};")




