from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF
import math
from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.Labeling.PolygonItem import PolygonItem

CLOSE_DISTANCE = 20


class Polygon(Core):
    def __init__(self):
        super().__init__()
        self.polygon_points = []
        self.is_drawing = False
        self.preview_lines = []
        self.first_point_indicator = None
        self.preview_line = None
        self.selected_polygon = None
        self.thickness = Utils.load_parameters()["geometric_shape"]["thickness"] 

    def polygon(self):
        """Activate the polygon drawing tool"""
        self.checked_button = self.polygon.__name__
        self.zoomable_graphics_view.scene.selectionChanged.connect(self.update_selected_polygon)

    def cleanup_preview(self):
        """Remove temporary preview lines and indicator"""
        for line in self.preview_lines:
            if line in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(line)
        self.preview_lines.clear()

        if self.first_point_indicator and self.first_point_indicator in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.first_point_indicator)
        self.first_point_indicator = None

        if self.preview_line and self.preview_line in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.preview_line)
        self.preview_line = None

    def start_polygon_tool(self, current_position):
        """Start or continue polygon drawing"""
        self.zoomable_graphics_view.change_cursor("polygon")
        pos = QPointF(current_position)

        if not self.is_drawing:
            # Start a new polygon
            self.cleanup_preview()
            self.polygon_points = [pos]
            self.is_drawing = True
            self.color = self.get_current_label_item().get_color()

            # Add a visual indicator for the first point
            self.first_point_indicator = QGraphicsEllipseItem(pos.x() - 5, pos.y() - 5, 10, 10)
            self.first_point_indicator.setPen(QPen(self.color, self.thickness))
            self.first_point_indicator.setBrush(QBrush(self.color))
            self.first_point_indicator.setZValue(3)
            self.zoomable_graphics_view.scene.addItem(self.first_point_indicator)
        else:
            # Check if the polygon should be closed
            first_point = self.polygon_points[0]
            if (
                math.hypot(pos.x() - first_point.x(), pos.y() - first_point.y()) <= CLOSE_DISTANCE
                and len(self.polygon_points) >= 3
            ):
                self.finalize_polygon()
                return

            # Otherwise add a new edge
            prev_point = self.polygon_points[-1]
            self.polygon_points.append(pos)
            line = QGraphicsLineItem(prev_point.x(), prev_point.y(), pos.x(), pos.y())
            pen = QPen(self.color, 2, Qt.PenStyle.DashLine)
            line.setPen(pen)
            line.setZValue(2)
            self.zoomable_graphics_view.scene.addItem(line)
            self.preview_lines.append(line)

    def move_polygon_tool(self, current_position):
        """Update the preview edge while moving mouse"""
        if not (self.is_drawing and self.polygon_points):
            return
        pos = QPointF(current_position)
        if self.preview_line and self.preview_line in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.preview_line)
        last_point = self.polygon_points[-1]
        self.preview_line = QGraphicsLineItem(last_point.x(), last_point.y(), pos.x(), pos.y())
        pen = QPen(self.color, 1, Qt.PenStyle.DotLine)
        self.preview_line.setPen(pen)
        self.preview_line.setZValue(1)
        self.zoomable_graphics_view.scene.addItem(self.preview_line)

    def finalize_polygon(self):
        """Finalize polygon creation"""
        if len(self.polygon_points) < 3:
            return

        self.cleanup_preview()
        polygon = QPolygonF(self.polygon_points)
        final_item = PolygonItem(polygon, self.color) 
        final_item.setZValue(2)
        final_item.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.zoomable_graphics_view.scene.addItem(final_item)

        if self.current_image_item:
            polygon_data = {
                "points": [(p.x(), p.y()) for p in polygon],
                "label": self.get_current_label_item().label_id
            }
            self.current_image_item.image_polygons.append(polygon_data)
            final_item.model_ref = polygon_data
            final_item.label_id = self.get_current_label_item().label_id

        self.selected_polygon = final_item
        self.polygon_points.clear()
        self.is_drawing = False
        self.get_current_image_item().update_labeling_overlay()

    def cancel_polygon(self):
        """Cancel current polygon drawing"""
        if self.is_drawing:
            self.cleanup_preview()
            self.polygon_points.clear()
            self.is_drawing = False

    def update_selected_polygon(self):
        """Update current selected polygon reference"""
        items = self.zoomable_graphics_view.scene.selectedItems()
        self.selected_polygon = next((i for i in reversed(items) if isinstance(i, PolygonItem)), None)

    def restore_polygons_for_image(self, image_path):
        """Restore all polygons for a specific image"""
        if self.current_image_item.image_polygons is not None:
            for poly_data in self.current_image_item.image_polygons:
                points = [QPointF(x, y) for x, y in poly_data["points"]]
                label_id = poly_data["label"]
                color = self.label_items[label_id].get_color()

                polygon_item = PolygonItem(QPolygonF(points), color) 
                polygon_item.setZValue(2)
                polygon_item.model_ref = poly_data
                polygon_item.label_id = label_id

                self.zoomable_graphics_view.scene.addItem(polygon_item)

    def clear_polygon(self):
        """Remove the currently selected polygon from the scene and model"""
        selected_polygons = [
            item for item in self.zoomable_graphics_view.scene.items()
            if isinstance(item, PolygonItem) and item.isSelected()
        ]
        for polygon in selected_polygons:
            if polygon in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(polygon)
            for i, poly_data in enumerate(self.current_image_item.image_polygons):
                if (poly_data.get("points") == [(p.x(), p.y()) for p in polygon.polygon()] and
                    poly_data.get("rotation") == polygon.rotation() and
                    poly_data.get("label") == polygon.model_ref.get("label")):
                    self.current_image_item.image_polygons.pop(i)
                    break
        self.selected_polygon = None
        self.current_image_item.update_labeling_overlay()

    def clear_all_polygons(self, label_id):
        """Remove all polygons with the given label"""
        if not self.current_image_item:
            return

        for item in list(self.zoomable_graphics_view.scene.items()):
            if isinstance(item, PolygonItem) and getattr(item, "label_id", None) == label_id:
                self.zoomable_graphics_view.scene.removeItem(item)

        # Clean model
        self.current_image_item.image_polygons = [
            poly for poly in self.current_image_item.image_polygons
            if poly.get("label") != label_id
        ]
        self.selected_polygon = None
        self.current_image_item.update_labeling_overlay()
