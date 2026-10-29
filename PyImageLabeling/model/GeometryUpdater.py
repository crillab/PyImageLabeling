import os
from PyQt6.QtGui import QBrush, QPen, QColor
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Labeling.RectangleItem import RectangleItem
from PyImageLabeling.model.Labeling.EllipseItem import EllipseItem
from PyImageLabeling.model.Labeling.PolygonItem import PolygonItem
from PyImageLabeling.logging_setup import get_logger

log = get_logger("core")


class GeometryUpdaterMixin:
        def update_thickness(self, new_thickness):
            # Update thickness in stored data for all images
            for file in self.file_paths:
                image_item = self.image_items.get(file)
                if image_item is not None:
                    # Update thickness in stored data
                    for rect_data in image_item.image_rectangles:
                        rect_data['thickness'] = new_thickness
                    for ellipse_data in image_item.image_ellipses:
                        ellipse_data['thickness'] = new_thickness
                    for polygon_data in image_item.image_polygons:
                        polygon_data['thickness'] = new_thickness
            
            # Restore shapes for current image to apply new thickness visually
            if self.current_image_item is not None:
                current_path = self.current_image_item.path_image
                
                # Remove existing geometric shapes from scene
                for item in list(self.zoomable_graphics_view.scene.items()):
                    if isinstance(item, (RectangleItem, EllipseItem, PolygonItem)):
                        self.zoomable_graphics_view.scene.removeItem(item)
                
                # Restore shapes with new thickness
                if self.current_image_item.image_rectangles:
                    self.restore_rectangles_for_image(current_path)
                if self.current_image_item.image_ellipses:
                    self.restore_ellipses_for_image(current_path)
                if self.current_image_item.image_polygons:
                    self.restore_polygons_for_image(current_path)
    
        def update_color(self, label_id):
            for file in self.file_paths:
                image_item = self.image_items.get(file) 
                if image_item is not None:
                    image_item.update_color(label_id)
                    self.update_geometric_colors_in_scene(label_id)
                    # We save the image in this case
                    image_item.save_overlays(self.save_directory)
                    image_item.update_icon_file()
                    self.save_labels(self.save_directory)
                else:
                    # deferred: never-opened images carry no overlay color in
                    # memory (the mask on disk stores only annotation alpha, so
                    # the currently-chosen label colour is applied on load). Their
                    # overlay and icon bar are refreshed when the image is next
                    # opened. Opening here would be an unwarranted LRU/screen churn.
                    log.debug("update_color skipped %s: not loaded (color "
                              "reapplied on load)", os.path.basename(file))
                
        def update_geometric_colors_in_scene(self, label_id):
            if self.current_image_item is None:
                return
            
            new_color = self.label_items[label_id].get_color()
            
            for item in self.zoomable_graphics_view.scene.items():
                if isinstance(item, RectangleItem) and getattr(item, "label_id", None) == label_id:
                    item.setPen(QPen(new_color, 2, Qt.PenStyle.SolidLine))
                    item.setBrush(QBrush(new_color, Qt.BrushStyle.NoBrush))
                if isinstance(item, EllipseItem) and getattr(item, "label_id", None) == label_id:
                    item.setPen(QPen(new_color, 2, Qt.PenStyle.SolidLine))
                    item.setBrush(QBrush(new_color, Qt.BrushStyle.NoBrush))
                if isinstance(item, PolygonItem) and getattr(item, "label_id", None) == label_id:
                    item.setPen(QPen(new_color, 2, Qt.PenStyle.SolidLine))
                    item.setBrush(QBrush(new_color, Qt.BrushStyle.NoBrush))
