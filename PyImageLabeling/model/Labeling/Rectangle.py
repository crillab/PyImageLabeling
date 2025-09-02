from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtGui import QPen, QCursor
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF

HANDLE_SIZE = 8  # Size of corner handles for resizing

class RectangleItem(QGraphicsRectItem):
    def __init__(self, x, y, width, height, color=Qt.GlobalColor.red):
        super().__init__(x, y, width, height)

        self.pen = QPen(color, 2)
        self.pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(self.pen)

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.handles = {}  # Dictionary to track corner handles
        self.handle_selected = None
        self.mouse_press_pos = None
        self.update_handles()

    def update_handles(self):
        """Update corner handle positions"""
        rect = self.rect()
        self.handles = {
            'top_left': QRectF(rect.topLeft() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'top_right': QRectF(rect.topRight() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom_left': QRectF(rect.bottomLeft() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom_right': QRectF(rect.bottomRight() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
        }

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.transparent, 1, Qt.PenStyle.SolidLine))
            for handle_rect in self.handles.values():
                painter.drawRect(handle_rect)

    def mousePressEvent(self, event):
        self.handle_selected = None
        self.mouse_press_pos = event.pos()

        # Check if user clicked a handle
        for name, rect in self.handles.items():
            if rect.contains(event.pos()):
                self.handle_selected = name
                break

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected:
            pos = event.pos()
            rect = self.rect()

            if self.handle_selected == 'top_left':
                rect.setTopLeft(pos)
            elif self.handle_selected == 'top_right':
                rect.setTopRight(pos)
            elif self.handle_selected == 'bottom_left':
                rect.setBottomLeft(pos)
            elif self.handle_selected == 'bottom_right':
                rect.setBottomRight(pos)

            self.setRect(rect)
            self.update_handles()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.handle_selected = None
        super().mouseReleaseEvent(event)


class Rectangle(Core):
    def __init__(self):
        super().__init__()
        self.first_click_pos = None
        self.current_rectangle = None
        self.is_drawing = False
        self.selected_rectangle = None  # Track clicked rectangle

    def rectangle(self):
        self.checked_button = self.rectangle.__name__

    def cleanup_temporary_rectangles(self):
        """Remove preview rectangles"""
        if self.current_rectangle:
            if self.current_rectangle in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(self.current_rectangle)
            self.current_rectangle = None

    def start_rectangle_tool(self, current_position):
        """Mouse press → start drawing"""
        self.view.zoomable_graphics_view.change_cursor("rectangle")
        self.cleanup_temporary_rectangles()

        self.first_click_pos = QPointF(current_position.x(), current_position.y())
        self.color = self.labels[self.current_label]["color"]
        self.is_drawing = True

        # Preview rectangle
        self.current_rectangle = QGraphicsRectItem(
            self.first_click_pos.x(),
            self.first_click_pos.y(),
            1, 1
        )
        pen = QPen(self.color, 2)
        pen.setStyle(Qt.PenStyle.DashLine)
        self.current_rectangle.setPen(pen)
        self.current_rectangle.setZValue(2)
        self.zoomable_graphics_view.scene.addItem(self.current_rectangle)

    def move_rectangle_tool(self, current_position):
        """Mouse move → resize preview rectangle"""
        if not self.is_drawing or not self.current_rectangle:
            return

        current_pos = QPointF(current_position.x(), current_position.y())
        x = min(self.first_click_pos.x(), current_pos.x())
        y = min(self.first_click_pos.y(), current_pos.y())
        w = abs(current_pos.x() - self.first_click_pos.x())
        h = abs(current_pos.y() - self.first_click_pos.y())

        self.current_rectangle.setRect(x, y, w, h)

    def end_rectangle_tool(self):
        """Mouse release → finalize rectangle"""
        if not self.is_drawing or not self.current_rectangle:
            return

        rect = self.current_rectangle.rect()
        self.cleanup_temporary_rectangles()

        if rect.width() > 5 and rect.height() > 5:
            final_rectangle = RectangleItem(
                rect.x(), rect.y(),
                rect.width(), rect.height(),
                self.color
            )
            final_rectangle.setZValue(2)
            final_rectangle.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.zoomable_graphics_view.scene.addItem(final_rectangle)

        self.first_click_pos = None
        self.is_drawing = False

