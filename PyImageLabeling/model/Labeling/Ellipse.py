from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QCursor, QBrush, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math
from PyImageLabeling.model.Labeling.EllipseItem import EllipseItem

class Ellipse(Core):
    def __init__(self):
        super().__init__()
        self.first_click_pos = None
        self.current_ellipse = None
        self.is_drawing = False
        self.selected_ellipse = None

    def ellipse(self):
        self.checked_button = self.ellipse.__name__
        self.zoomable_graphics_view.scene.selectionChanged.connect(self.update_selected_ellipse)

    def cleanup_temporary_ellipses(self):
        """Remove preview ellipses"""
        if self.current_ellipse and self.current_ellipse in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.current_ellipse)
        self.current_ellipse = None

    def start_ellipse_tool(self, current_position):
        """Mouse press → start drawing"""
        self.zoomable_graphics_view.change_cursor("ellipse")
        self.cleanup_temporary_ellipses()
        self.first_click_pos = QPointF(current_position)
        self.color = self.get_current_label_item().get_color()
        self.is_drawing = True
        # Preview ellipse
        self.current_ellipse = QGraphicsEllipseItem(
            self.first_click_pos.x(),
            self.first_click_pos.y(),
            1, 1
        )
        pen = QPen(self.color, 2, Qt.PenStyle.DashLine)
        self.current_ellipse.setPen(pen)
        self.current_ellipse.setZValue(2)
        self.zoomable_graphics_view.scene.addItem(self.current_ellipse)

    def move_ellipse_tool(self, current_position):
        """Mouse move → resize preview ellipse"""
        if not (self.is_drawing and self.current_ellipse):
            return
        current_pos = QPointF(current_position)
        x, y = min(self.first_click_pos.x(), current_pos.x()), min(self.first_click_pos.y(), current_pos.y())
        w, h = abs(current_pos.x() - self.first_click_pos.x()), abs(current_pos.y() - self.first_click_pos.y())
        self.current_ellipse.setRect(x, y, w, h)

    def end_ellipse_tool(self):
        """Mouse release → finalize ellipse"""
        if not (self.is_drawing and self.current_ellipse):
            return
        ellipse = self.current_ellipse.rect()
        self.cleanup_temporary_ellipses()
        if ellipse.width() > 5 and ellipse.height() > 5:
            # Fixed: Pass rotation=0 and color in correct order
            final_ellipse = EllipseItem(
                ellipse.x(), ellipse.y(),
                ellipse.width(), ellipse.height(),
                self.color,
                rotation=0  
            )
            final_ellipse.setZValue(2)
            final_ellipse.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.zoomable_graphics_view.scene.addItem(final_ellipse)
            self.selected_ellipse = final_ellipse
            if self.current_image_item:
                ellipse_data = {
                    "x": ellipse.x(),
                    "y": ellipse.y(),
                    "width": ellipse.width(),
                    "height": ellipse.height(),
                    "rotation": 0,
                    "label": self.get_current_label_item().label_id
                }
                self.current_image_item.image_ellipses.append(ellipse_data)
                final_ellipse.model_ref = ellipse_data
                final_ellipse.label_id = self.get_current_label_item().label_id
        self.first_click_pos = None
        self.is_drawing = False
        self.get_current_image_item().update_labeling_overlay()

    def update_selected_ellipse(self):
        """Update selected_ellipse when user clicks on an ellipse"""
        items = self.zoomable_graphics_view.scene.selectedItems()
        self.selected_ellipse = next((i for i in reversed(items) if isinstance(i, EllipseItem)), None)

    def restore_ellipses_for_image(self, image_path):
        """Restore ellipses for a specific image."""
        if self.current_image_item.image_ellipses is not None:
            for ellipse_data in self.current_image_item.image_ellipses:
                x = ellipse_data["x"]
                y = ellipse_data["y"]
                width = ellipse_data["width"]
                height = ellipse_data["height"]
                rotation = ellipse_data["rotation"]
                label_id = ellipse_data["label"]
                # Fixed: Pass color and rotation in correct order
                item = EllipseItem(x, y, width, height, 
                                 self.label_items[label_id].get_color(),
                                 rotation=rotation)
                item.setZValue(2)
                # Add to scene
                self.zoomable_graphics_view.scene.addItem(item)
                item.model_ref = ellipse_data
                item.label_id = label_id

    def clear_ellipse(self):
        """Remove the currently selected ellipse from the scene and model"""
        selected_ellipses = [item for item in self.zoomable_graphics_view.scene.items()
                            if isinstance(item, EllipseItem) and item.isSelected()]
        for ellipse in selected_ellipses:
            # Remove the visual item from the scene
            self.zoomable_graphics_view.scene.removeItem(ellipse)
            for i, ellipse_data in enumerate(self.current_image_item.image_ellipses):
                if (ellipse_data.get("x") == ellipse.model_ref.get("x") and
                    ellipse_data.get("y") == ellipse.model_ref.get("y") and
                    ellipse_data.get("width") == ellipse.model_ref.get("width") and
                    ellipse_data.get("height") == ellipse.model_ref.get("height") and
                    ellipse_data.get("rotation") == ellipse.model_ref.get("rotation") and
                    ellipse_data.get("label") == ellipse.model_ref.get("label")):
                    self.current_image_item.image_ellipses.pop(i)
                    break
        self.selected_ellipse = None
        self.current_image_item.update_labeling_overlay()

    def clear_all_ellipses(self, label_id):
        """Remove all ellipses of a specific label from the scene and model"""
        if not self.current_image_item:
            return
        # Iterate over a copy of the scene items because we will modify the scene
        for item in list(self.zoomable_graphics_view.scene.items()):
            if isinstance(item, EllipseItem) and getattr(item, "label_id", None) == label_id:
                self.zoomable_graphics_view.scene.removeItem(item)
        # Remove matching ellipses from the image model
        self.current_image_item.image_ellipses = [
            ellipse for ellipse in self.current_image_item.image_ellipses
            if ellipse.get("label") != label_id
        ]
        self.selected_ellipse = None
        self.current_image_item.update_labeling_overlay()