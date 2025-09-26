from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PyQt6.QtGui import QPen, QBrush
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

HANDLE_SIZE = 8
HANDLE_DETECTION_DISTANCE = 15
MIN_RECT_SIZE = 10


class RectangleItem(QGraphicsRectItem):
    HANDLE_TYPES = {
        'top_left': Qt.CursorShape.SizeFDiagCursor,
        'top_right': Qt.CursorShape.SizeBDiagCursor,
        'bottom_left': Qt.CursorShape.SizeBDiagCursor,
        'bottom_right': Qt.CursorShape.SizeFDiagCursor,
        'rotation': Qt.CursorShape.OpenHandCursor,
    }

    def __init__(self, x, y, width, height, color=Qt.GlobalColor.red):
        super().__init__(x, y, width, height)

        pen = QPen(color, 2, Qt.PenStyle.SolidLine)
        self.setPen(pen)


        self.model_ref = None  

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.handles = {}
        self.handle_selected = None
        self.handles_visible = False
        self.initial_rotation = 0
        self.initial_angle = 0

        self.update_handles()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.update_model()  # update coordinates whenever the rectangle moves
        elif change == QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged:
            self.update_model()  # update when rotated or transformed
        return super().itemChange(change, value)

    def update_model(self):
        """Push the updated rect back to the model list."""
        if self.model_ref is not None:
            rect = self.mapRectToScene(self.rect())
            self.model_ref["x"] = rect.x()
            self.model_ref["y"] = rect.y()
            self.model_ref["width"] = rect.width()
            self.model_ref["height"] = rect.height()

    def update_handles(self):
        rect = self.rect()
        self.handles = {
            'top_left': QRectF(rect.topLeft() - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'top_right': QRectF(rect.topRight() - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom_left': QRectF(rect.bottomLeft() - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom_right': QRectF(rect.bottomRight() - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'rotation': QRectF(rect.center() - QPointF(HANDLE_SIZE / 2, HANDLE_SIZE / 2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
        }

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
                self.setCursor(self.HANDLE_TYPES.get(name, Qt.CursorShape.ArrowCursor))
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

        # Draw resize handles
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        for name, handle in self.handles.items():
            if name == "rotation":
                painter.setPen(QPen(Qt.GlobalColor.blue, 2))
                painter.setBrush(QBrush(Qt.GlobalColor.blue))
                painter.drawEllipse(handle)
            else:
                painter.drawRect(handle)

    def mousePressEvent(self, event):
        self.handle_selected = None
        for name, rect in self.handles.items():
            if rect.contains(event.pos()):
                self.handle_selected = name
                if name == "rotation":
                    rect_center = self.rect().center()
                    self.setTransformOriginPoint(rect_center)

                    # Save starting angle
                    rect_center_scene = self.mapToScene(rect_center)
                    mouse_scene_pos = self.mapToScene(event.pos())
                    self.initial_rotation = math.atan2(
                        mouse_scene_pos.y() - rect_center_scene.y(),
                        mouse_scene_pos.x() - rect_center_scene.x(),
                    )
                    self.initial_angle = self.rotation()
                break


        if self.handle_selected:
            self.handles_visible = False
            self.update()
            
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected == 'rotation':
            self.rotate_item(event)
        elif self.handle_selected:
            self.resize_item(event)
        else:
            if self.handle_selected:
                self.handles_visible = False
                self.update()
            super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.handle_selected == 'rotation':
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        self.handle_selected = None
        self.handles_visible = True
        self.setSelected(False)
        self.update()
        self.update_model()
        if not event.isAccepted():
            super().mouseReleaseEvent(event)

    def rotate_item(self, event):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        rect_center_scene = self.mapToScene(self.rect().center())
        mouse_scene_pos = self.mapToScene(event.pos())

        current_angle = math.atan2(
            mouse_scene_pos.y() - rect_center_scene.y(),
            mouse_scene_pos.x() - rect_center_scene.x(),
        )
        angle_diff = math.degrees(current_angle - self.initial_rotation)
        self.setRotation(self.initial_angle + angle_diff)

        self.update_handles()
        self.update()
        self.update_model()

    def resize_item(self, event):
        rect = self.rect()
        pos = event.pos()

        if self.handle_selected == 'top_left':
            rect.setTopLeft(pos)
        elif self.handle_selected == 'top_right':
            rect.setTopRight(pos)
        elif self.handle_selected == 'bottom_left':
            rect.setBottomLeft(pos)
        elif self.handle_selected == 'bottom_right':
            rect.setBottomRight(pos)

        # Enforce minimum size
        if rect.width() < MIN_RECT_SIZE:
            rect.setWidth(MIN_RECT_SIZE)
        if rect.height() < MIN_RECT_SIZE:
            rect.setHeight(MIN_RECT_SIZE)

        self.setRect(rect)
        self.update_handles()
        self.update()
        self.update_model()

