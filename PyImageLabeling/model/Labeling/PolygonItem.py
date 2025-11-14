from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math
from PyImageLabeling.model.Utils import Utils
HANDLE_DETECTION_DISTANCE = 15


class PolygonItem(QGraphicsPolygonItem):
    def __init__(self, polygon, color=Qt.GlobalColor.red):
        super().__init__(polygon)
        self.thickness = Utils.load_parameters()["geometric_shape"]["thickness"]
        self.pen = QPen(color, self.thickness)
        self.pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(self.pen)

        self.model_ref = None  # link to model dict

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
        """Push updated polygon coordinates to model_ref in scene coordinates."""
        if self.model_ref is not None:
            polygon_scene = [self.mapToScene(p) for p in self.polygon()]
            self.model_ref["points"] = [(p.x(), p.y()) for p in polygon_scene]
            # Remove rotation line - we don't store rotation anymore
            
            center_scene = self.mapToScene(self.polygon().boundingRect().center())
            self.model_ref["center"] = (center_scene.x(), center_scene.y())

    def update_handles(self):
        # Handles are always based on the current (potentially rotated) visual polygon
        polygon = self.polygon()
        self.handles = {
            f"vertex_{i}": QRectF(
                point - QPointF(self.thickness / 2, self.thickness / 2),
                QSizeF(self.thickness, self.thickness),
            )
            for i, point in enumerate(polygon)
        }
        if not polygon.isEmpty():
            center = polygon.boundingRect().center()
            self.handles["rotation"] = QRectF(
                center - QPointF(self.thickness / 2, self.thickness / 2),
                QSizeF(self.thickness, self.thickness),
            )

    @staticmethod
    def distance_to_rect(point, rect):
        center = rect.center()
        return math.hypot(point.x() - center.x(), point.y() - center.y())

    def check_handle_proximity(self, pos):
        """Show handles only when cursor is inside the polygon (not by selection)."""
        inside_polygon = self.polygon().containsPoint(pos, Qt.FillRule.OddEvenFill)
        near_handle = any(
            self.distance_to_rect(pos, rect) < HANDLE_DETECTION_DISTANCE
            for rect in self.handles.values()
        )
        should_show = inside_polygon or near_handle

        if should_show != self.handles_visible:
            self.handles_visible = should_show
            self.update()

    def update_cursor(self, pos):
        if not self.handles_visible:
            return
        for name, rect in self.handles.items():
            if rect.contains(pos):
                if name == "rotation":
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                elif name.startswith("vertex_"):
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
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
        """Rotate polygon around its center (blue point)."""
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

        polygon = self.polygon()
        center = polygon.boundingRect().center()

        # Rotation center in scene coordinates (stays constant)
        center_scene = self.mapToScene(center)
        mouse_scene = self.mapToScene(event.pos())

        current_angle = math.atan2(
            mouse_scene.y() - center_scene.y(),
            mouse_scene.x() - center_scene.x(),
        )
        angle_diff = current_angle - self.initial_rotation

        # Update visual rotation around the center handle
        self.setTransformOriginPoint(center)
        self.setRotation(self.initial_angle + math.degrees(angle_diff))

        self.update_handles()
        self.update()

    def move_vertex(self, event):
        """Move individual polygon vertex."""
        index = int(self.handle_selected.split("_")[1])
        
        polygon = self.polygon()
        if 0 <= index < polygon.size():
            polygon[index] = event.pos()
            self.setPolygon(polygon)
        
        self.update_handles()
        self.update()