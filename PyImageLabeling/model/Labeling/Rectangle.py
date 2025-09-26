from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtGui import QPen, QCursor, QBrush, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

from PyImageLabeling.model.Labeling.RectangleItem import RectangleItem

class Rectangle(Core):
    def __init__(self):
        super().__init__()
        self.first_click_pos = None
        self.current_rectangle = None
        self.is_drawing = False
        self.selected_rectangle = None

    def rectangle(self):
        self.checked_button = self.rectangle.__name__
        self.zoomable_graphics_view.scene.selectionChanged.connect(self.update_selected_rectangle)

    def cleanup_temporary_rectangles(self):
        if self.current_rectangle and self.current_rectangle in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.current_rectangle)
        self.current_rectangle = None

    def start_rectangle_tool(self, current_position):
        self.zoomable_graphics_view.change_cursor("rectangle")
        self.cleanup_temporary_rectangles()

        self.first_click_pos = QPointF(current_position)
        self.color = self.get_current_label_item().get_color()
        self.is_drawing = True

        self.current_rectangle = QGraphicsRectItem(self.first_click_pos.x(), self.first_click_pos.y(), 1, 1)
        self.current_rectangle.setPen(QPen(self.color, 2, Qt.PenStyle.DashLine))
        self.current_rectangle.setZValue(2)
        self.zoomable_graphics_view.scene.addItem(self.current_rectangle)

    def move_rectangle_tool(self, current_position):
        if not (self.is_drawing and self.current_rectangle):
            return
        current_pos = QPointF(current_position)
        x, y = min(self.first_click_pos.x(), current_pos.x()), min(self.first_click_pos.y(), current_pos.y())
        w, h = abs(current_pos.x() - self.first_click_pos.x()), abs(current_pos.y() - self.first_click_pos.y())
        self.current_rectangle.setRect(x, y, w, h)

    def restore_rectangles_for_image(self, image_path):
        """Restore rectangles for a specific image."""
        if self.current_image_item.image_rectangles is not None:
            for rect_data in self.current_image_item.image_rectangles:
                x = rect_data["x"]
                y = rect_data["y"]
                width = rect_data["width"]
                height = rect_data["height"]
                label_id = rect_data["label"]
                # Create a new RectangleItem with the same geometry and color
                item = RectangleItem(x, y, width, height, self.label_items[label_id].get_color())
                item.setZValue(2)
                # Add to scene
                self.zoomable_graphics_view.scene.addItem(item)
                item.model_ref = rect_data
                item.label_id = label_id 

    def end_rectangle_tool(self):
        if not (self.is_drawing and self.current_rectangle):
            return

        rect = self.current_rectangle.rect()
        self.cleanup_temporary_rectangles()

        if rect.width() > 5 and rect.height() > 5:
            final_rectangle = RectangleItem(rect.x(), rect.y(), rect.width(), rect.height(), self.color)
            final_rectangle.setZValue(2)
            self.selected_rectangle = final_rectangle
            if self.current_image_item:
                #rect_data = (final_rectangle.rect())
                rect_data = {
                    "x":  final_rectangle.rect().x(),
                    "y":  final_rectangle.rect().y(),
                    "width":  final_rectangle.rect().width(),
                    "height":  final_rectangle.rect().height(),
                    "label": self.get_current_label_item().label_id
                }
                self.zoomable_graphics_view.scene.addItem(final_rectangle)
                self.current_image_item.image_rectangles.append(rect_data)
                final_rectangle.model_ref = rect_data
                final_rectangle.label_id = self.get_current_label_item().label_id
                

        self.first_click_pos = None
        self.is_drawing = False
        self.get_current_image_item().update_labeling_overlay()
        
    def update_selected_rectangle(self):
        items = self.zoomable_graphics_view.scene.selectedItems()
        self.selected_rectangle = next((i for i in reversed(items) if isinstance(i, RectangleItem)), None)

    def clear_rectangle(self):
        selected_rectangles = [item for item in self.zoomable_graphics_view.scene.items() 
                            if isinstance(item, RectangleItem) and item.isSelected()]
        print("selected_rectangles:",selected_rectangles)

        for rectangle in selected_rectangles:
            # Remove the visual item from the scene
            self.zoomable_graphics_view.scene.removeItem(rectangle)

            for i, rect_data in enumerate(self.current_image_item.image_rectangles):
                if (rect_data.get("x") == rectangle.model_ref.get("x") and
                    rect_data.get("y") == rectangle.model_ref.get("y") and
                    rect_data.get("width") == rectangle.model_ref.get("width") and
                    rect_data.get("height") == rectangle.model_ref.get("height") and
                    rect_data.get("label") == rectangle.model_ref.get("label")):
                    self.current_image_item.image_rectangles.pop(i)
                    break

        self.selected_rectangle = None
        self.current_image_item.update_labeling_overlay()

    def clear_all_rectangles(self, label_id):
        if not self.current_image_item:
            return

        # Iterate over a copy of the scene items because we will modify the scene
        for item in list(self.zoomable_graphics_view.scene.items()):
            if isinstance(item, RectangleItem) and getattr(item, "label_id", None) == label_id:
                self.zoomable_graphics_view.scene.removeItem(item)

        # Remove matching rectangles from the image model
        self.current_image_item.image_rectangles = [
            rect for rect in self.current_image_item.image_rectangles
            if rect.get("label") != label_id
        ]

        self.selected_rectangle = None
        self.current_image_item.update_labeling_overlay()

