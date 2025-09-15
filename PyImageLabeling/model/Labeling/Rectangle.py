from model.Core import Core
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtGui import QPen, QCursor, QBrush
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
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected == 'rotation':
            self.rotate_item(event)
        elif self.handle_selected:
            self.resize_item(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.handle_selected == 'rotation':
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        self.handle_selected = None
        self.handles_visible = True
        self.update()
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
        self.color = self.get_labeling_overlay().get_color()
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

    def end_rectangle_tool(self):
        if not (self.is_drawing and self.current_rectangle):
            return

        rect = self.current_rectangle.rect()
        self.cleanup_temporary_rectangles()

        if rect.width() > 5 and rect.height() > 5:
            final_rectangle = RectangleItem(rect.x(), rect.y(), rect.width(), rect.height(), self.color)
            final_rectangle.setZValue(2)
            final_rectangle.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.zoomable_graphics_view.scene.addItem(final_rectangle)
            self.selected_rectangle = final_rectangle

        self.first_click_pos = None
        self.is_drawing = False

    def update_selected_rectangle(self):
        items = self.zoomable_graphics_view.scene.selectedItems()
        self.selected_rectangle = next((i for i in reversed(items) if isinstance(i, RectangleItem)), None)

    def clear_rectangle(self):
        if self.selected_rectangle and self.selected_rectangle in self.zoomable_graphics_view.scene.items():
            self.zoomable_graphics_view.scene.removeItem(self.selected_rectangle)
        self.selected_rectangle = None
