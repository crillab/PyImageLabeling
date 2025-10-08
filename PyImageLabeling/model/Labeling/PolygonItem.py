from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

HANDLE_SIZE = 8
HANDLE_DETECTION_DISTANCE = 15


class PolygonItem(QGraphicsPolygonItem):
    def __init__(self, polygon, color=Qt.GlobalColor.red, rotation=0):
        super().__init__(polygon)

        self.pen = QPen(color, 2)
        self.pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(self.pen)

        self.model_ref = None  # link to model dict

        # CRITICAL: Store the UNROTATED polygon shape
        self.base_polygon = QPolygonF(polygon)
        
        # Set transform origin point BEFORE applying rotation
        center = polygon.boundingRect().center()
        self.setTransformOriginPoint(center)
        
        # Apply initial rotation if given
        if rotation != 0:
            self.setRotation(rotation)

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

    def itemChange(self, change, value):
        if change in (
            QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged,
            QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged,
        ):
            self.update_model()
        return super().itemChange(change, value)

    def update_model(self):
        """Push updated polygon coordinates and rotation to model_ref in scene coordinates."""
        if self.model_ref is not None:
            # Use self.polygon(), which is a QPolygonF
            polygon_scene = [self.mapToScene(p) for p in self.polygon()]
            self.model_ref["points"] = [(p.x(), p.y()) for p in polygon_scene]
            self.model_ref["rotation"] = self.rotation()

            # Optional: store polygon center in scene coords
            center_scene = self.mapToScene(self.polygon().boundingRect().center())
            self.model_ref["center"] = (center_scene.x(), center_scene.y())

    def update_handles(self):
        # Handles are always based on the current (potentially rotated) visual polygon
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

    @staticmethod
    def distance_to_rect(point, rect):
        center = rect.center()
        return math.hypot(point.x() - center.x(), point.y() - center.y())

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

    def update_cursor(self, pos):
        if not self.handles_visible:
            return
        for name, rect in self.handles.items():
            if rect.contains(pos):
                if name == "rotation":
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
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
            self.handles_visible = False
            self.rotate_item(event)
        elif self.handle_selected and self.handle_selected.startswith("vertex_"):
            self.handles_visible = False
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
        self.update_model()
        if not event.isAccepted():
            super().mouseReleaseEvent(event)

    def rotate_item(self, event):
        """Handle rotation of the polygon."""
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        center = self.polygon().boundingRect().center()
        self.setTransformOriginPoint(center)
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
        self.update_model()

    def move_vertex(self, event):
        """Move individual polygon vertex without affecting rotation."""
        index = int(self.handle_selected.split("_")[1])
        
        # Get current rotation
        current_rotation = self.rotation()
        
        # Temporarily remove rotation to work in unrotated space
        self.setRotation(0)
        
        # Update the base polygon
        if 0 <= index < self.base_polygon.size():
            # Map the mouse position to the unrotated coordinate system
            # We need to inverse-rotate the mouse position
            angle_rad = math.radians(-current_rotation)
            center = self.base_polygon.boundingRect().center()
            
            # Get mouse position relative to center
            rel_x = event.pos().x() - center.x()
            rel_y = event.pos().y() - center.y()
            
            # Rotate back to unrotated space
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            new_x = rel_x * cos_a - rel_y * sin_a + center.x()
            new_y = rel_x * sin_a + rel_y * cos_a + center.y()
            
            # Update base polygon
            self.base_polygon[index] = QPointF(new_x, new_y)
            self.setPolygon(self.base_polygon)
            
            # Update transform origin to new center
            new_center = self.base_polygon.boundingRect().center()
            self.setTransformOriginPoint(new_center)
        
        # Reapply rotation
        self.setRotation(current_rotation)
        
        self.update_handles()
        self.update()
        self.update_model()