from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

HANDLE_SIZE = 8
HANDLE_DETECTION_DISTANCE = 15
CLOSE_DISTANCE = 20


class PolygonItem(QGraphicsPolygonItem):
    HANDLE_TYPES = {
        'rotation': Qt.CursorShape.OpenHandCursor,
        # all vertex handles use SizeAll
    }

    def __init__(self, polygon, color=Qt.GlobalColor.red):
        super().__init__(polygon)

        self.setPen(QPen(color, 2))
        self.setFlags(
            QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsPolygonItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsPolygonItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.handles = {}
        self.handle_selected = None
        self.handles_visible = False
        self.initial_rotation = 0
        self.initial_angle = 0

        self.update_handles()

    def update_handles(self):
        polygon = self.polygon()
        self.handles = {
            f"vertex_{i}": QRectF(
                point - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2),
                QSizeF(HANDLE_SIZE, HANDLE_SIZE),
            )
            for i, point in enumerate(polygon)
        }
        if not polygon.isEmpty():
            center = polygon.boundingRect().center()
            self.handles["rotation"] = QRectF(
                center - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2),
                QSizeF(HANDLE_SIZE, HANDLE_SIZE),
            )

    def check_handle_proximity(self, pos):
        near_handle = any(
            self.distance_to_rect(pos, rect) < HANDLE_DETECTION_DISTANCE
            for rect in self.handles.values()
        )
        if self.isSelected():
            near_handle = True
        if near_handle != self.handles_visible:
            self.handles_visible = near_handle
            self.update()

    @staticmethod
    def distance_to_rect(point, rect):
        center = rect.center()
        return math.hypot(point.x() - center.x(), point.y() - center.y())

    def update_cursor(self, pos):
        if not self.handles_visible:
            return
        for name, rect in self.handles.items():
            if rect.contains(pos):
                self.setCursor(self.HANDLE_TYPES.get(name, Qt.CursorShape.SizeAllCursor))
                return
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def hoverEnterEvent(self, event):
        self.check_handle_proximity(event.pos())
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        self.check_handle_proximity(event.pos())
        self.update_cursor(event.pos())
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.handles_visible = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if not self.handles_visible:
            return

        # Draw vertex handles
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        for name, rect in self.handles.items():
            if name != "rotation":
                painter.drawRect(rect)

        # Draw rotation handle
        if "rotation" in self.handles:
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))
            painter.setBrush(QBrush(Qt.GlobalColor.blue))
            painter.drawEllipse(self.handles["rotation"])

    def mousePressEvent(self, event):
        self.handle_selected = None
        for name, rect in self.handles.items():
            if rect.contains(event.pos()):
                self.handle_selected = name
                if name == "rotation":
                    center = self.polygon().boundingRect().center()
                    self.setTransformOriginPoint(center)
                    center_scene = self.mapToScene(center)
                    mouse_scene = self.mapToScene(event.pos())
                    self.initial_rotation = math.atan2(
                        mouse_scene.y() - center_scene.y(),
                        mouse_scene.x() - center_scene.x(),
                    )
                    self.initial_angle = self.rotation()
                break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected == "rotation":
            self.rotate_item(event)
        elif self.handle_selected and self.handle_selected.startswith("vertex_"):
            self.move_vertex(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.handle_selected == "rotation":
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        self.handle_selected = None
        self.handles_visible = True
        self.update()
        if not event.isAccepted():
            super().mouseReleaseEvent(event)

    def rotate_item(self, event):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        center = self.polygon().boundingRect().center()
        center_scene = self.mapToScene(center)
        mouse_scene = self.mapToScene(event.pos())
        current_angle = math.atan2(
            mouse_scene.y() - center_scene.y(),
            mouse_scene.x() - center_scene.x(),
        )
        angle_diff = math.degrees(current_angle - self.initial_rotation)
        self.setRotation(self.initial_angle + angle_diff)
        self.update_handles()
        self.update()

    def move_vertex(self, event):
        index = int(self.handle_selected.split("_")[1])
        polygon = self.polygon()
        if 0 <= index < polygon.size():
            polygon[index] = event.pos()
            self.setPolygon(polygon)
            self.update_handles()
            self.update()
        self.handles_visible = False


class Polygon(Core):
    def __init__(self):
        super().__init__()
        self.polygon_points = []
        self.is_drawing = False
        self.preview_lines = []
        self.first_point_indicator = None
        self.preview_line = None
        self.selected_polygon = None

    def polygon(self):
        self.checked_button = self.polygon.__name__
        self.zoomable_graphics_view.scene.selectionChanged.connect(
            self.update_selected_polygon
        )

    def cleanup_preview(self):
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
        self.zoomable_graphics_view.change_cursor("polygon")
        pos = QPointF(current_position)
        if not self.is_drawing:
            # Start new polygon
            self.cleanup_preview()
            self.polygon_points = [pos]
            self.is_drawing = True
            self.color = self.get_current_label_item().get_color()
            self.first_point_indicator = QGraphicsEllipseItem(
                pos.x() - 5, pos.y() - 5, 10, 10
            )
            self.first_point_indicator.setPen(QPen(self.color, 2))
            self.first_point_indicator.setBrush(QBrush(self.color))
            self.first_point_indicator.setZValue(3)
            self.zoomable_graphics_view.scene.addItem(self.first_point_indicator)
        else:
            # Close polygon if close enough
            first_point = self.polygon_points[0]
            if (
                math.hypot(pos.x() - first_point.x(), pos.y() - first_point.y())
                <= CLOSE_DISTANCE
                and len(self.polygon_points) >= 3
            ):
                self.finalize_polygon()
                return
            # Add point + preview line
            prev_point = self.polygon_points[-1]
            self.polygon_points.append(pos)
            line = QGraphicsLineItem(prev_point.x(), prev_point.y(), pos.x(), pos.y())
            pen = QPen(self.color, 2, Qt.PenStyle.DashLine)
            line.setPen(pen)
            line.setZValue(2)
            self.zoomable_graphics_view.scene.addItem(line)
            self.preview_lines.append(line)

    def move_polygon_tool(self, current_position):
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
        if len(self.polygon_points) < 3:
            return
        self.cleanup_preview()
        polygon = QPolygonF(self.polygon_points)
        final = PolygonItem(polygon, self.color)
        final.setZValue(2)
        final.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.zoomable_graphics_view.scene.addItem(final)
        self.selected_polygon = final
        self.polygon_points.clear()
        self.is_drawing = False

    def cancel_polygon(self):
        if self.is_drawing:
            self.cleanup_preview()
            self.polygon_points.clear()
            self.is_drawing = False

    def end_polygon_tool(self):
        pass

    def update_selected_polygon(self):
        items = self.zoomable_graphics_view.scene.selectedItems()
        self.selected_polygon = next((i for i in reversed(items) if isinstance(i, PolygonItem)), None)

    def clear_polygon(self):
        if self.selected_polygon and self.selected_polygon in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.selected_polygon)
        self.selected_polygon = None
        self.cancel_polygon()
