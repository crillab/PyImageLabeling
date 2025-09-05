from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtGui import QPen, QCursor, QBrush
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

HANDLE_SIZE = 8  # Size of corner handles for resizing
ROTATION_HANDLE_DISTANCE = 20  # Distance of rotation handle from rectangle
HANDLE_DETECTION_DISTANCE = 15  # Distance for auto-showing handles

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
        self.rotation_handle = None  # Rotation handle
        self.handle_selected = None
        self.mouse_press_pos = None
        self.handles_visible = False
        self.initial_rotation = 0
        self.initial_angle = 0
        
        # Accept hover events to detect mouse proximity
        self.setAcceptHoverEvents(True)
        
        self.update_handles()

    def update_handles(self):
        """Update corner handle and rotation handle positions"""
        rect = self.rect()
        
        # Rotation handle (positioned above the rectangle)
        center_top = QPointF(rect.center().x(), rect.center().y())
        rotation_pos = center_top - QPointF(0, ROTATION_HANDLE_DISTANCE)
        self.rotation_handle = QRectF(rotation_pos - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE))

        # Corner handles for resizing
        self.handles = {
            'top_left': QRectF(rect.topLeft() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'top_right': QRectF(rect.topRight() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom_left': QRectF(rect.bottomLeft() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom_right': QRectF(rect.bottomRight() - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'rotation': self.rotation_handle 
        }

    def hoverEnterEvent(self, event):
        """Mouse entered the item area"""
        self.check_handle_proximity(event.pos())
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        """Mouse moved within the item area"""
        self.check_handle_proximity(event.pos())
        self.update_cursor(event.pos())
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        """Mouse left the item area"""
        self.handles_visible = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def check_handle_proximity(self, pos):
        """Check if mouse is near any handle and make them visible"""
        near_handle = False
        
        # Check corner handles
        for handle_rect in self.handles.values():
            if self.distance_to_rect(pos, handle_rect) < HANDLE_DETECTION_DISTANCE:
                near_handle = True
                break
        
        # Check rotation handle
        if not near_handle and self.rotation_handle:
            if self.distance_to_rect(pos, self.rotation_handle) < HANDLE_DETECTION_DISTANCE:
                near_handle = True
        
        # Also show handles when selected
        if self.isSelected():
            near_handle = True
            
        if near_handle != self.handles_visible:
            self.handles_visible = near_handle
            self.update()

    def distance_to_rect(self, point, rect):
        """Calculate distance from point to rectangle"""
        center = rect.center()
        dx = abs(point.x() - center.x())
        dy = abs(point.y() - center.y())
        return math.sqrt(dx*dx + dy*dy)

    def update_cursor(self, pos):
        """Update cursor based on which handle is under mouse"""
        if not self.handles_visible:
            return
            
        # Check rotation handle first
        if self.rotation_handle and self.rotation_handle.contains(pos):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
            
        # Check resize handles
        for name, rect in self.handles.items():
            if rect.contains(pos):
                if name in ['top_left', 'bottom_right']:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif name in ['top_right', 'bottom_left']:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                return
        
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        if self.handles_visible:
            # Draw resize handles
            painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(Qt.GlobalColor.white, Qt.BrushStyle.SolidPattern))
            
            for handle_rect in self.handles.values():
                painter.drawRect(handle_rect)
            
            # Draw rotation handle (circular) at center
            if self.rotation_handle:
                painter.setPen(QPen(Qt.GlobalColor.blue, 2, Qt.PenStyle.SolidLine))
                painter.setBrush(QBrush(Qt.GlobalColor.blue, Qt.BrushStyle.SolidPattern))
                painter.drawEllipse(self.rotation_handle)

    def mousePressEvent(self, event):
        self.handle_selected = None
        self.mouse_press_pos = event.pos()

        if not self.handles_visible:
            super().mousePressEvent(event)
            return

        # Check resize handles
        for name, rect in self.handles.items():
            if rect.contains(event.pos()):
                self.handle_selected = name
                break

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected == 'rotation':
            # Handle rotation
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            rect_center = self.rect().center()
            self.setTransformOriginPoint(rect_center)
            
            # Map center to scene coordinates
            rect_center_scene = self.mapToScene(rect_center)
            
            # Calculate current mouse angle relative to rectangle center
            mouse_scene_pos = self.mapToScene(event.pos())
            current_mouse_angle = math.atan2(
                mouse_scene_pos.y() - rect_center_scene.y(),
                mouse_scene_pos.x() - rect_center_scene.x()
            )
            
            # Calculate angle difference and apply rotation
            angle_diff = math.degrees(current_mouse_angle - self.initial_rotation)
            new_rotation = self.initial_angle + angle_diff
            self.setRotation(new_rotation)
            
            self.update_handles()
            self.update()
            
        elif self.handle_selected and self.handle_selected != 'rotation':
            # Handle resizing
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

            # Ensure minimum size
            if rect.width() < 10:
                if self.handle_selected in ['top_left', 'bottom_left']:
                    rect.setLeft(rect.right() - 10)
                else:
                    rect.setRight(rect.left() + 10)
            
            if rect.height() < 10:
                if self.handle_selected in ['top_left', 'top_right']:
                    rect.setTop(rect.bottom() - 10)
                else:
                    rect.setBottom(rect.top() + 10)

            self.setRect(rect)
            self.update_handles()
            self.update()  # Force repaint to hide handles during resizing
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.handle_selected == 'rotation':
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            # Accept the event to prevent propagation
            event.accept()
        self.handle_selected = None
        
        # Only call super if we didn't handle rotation
        if not (self.handle_selected == 'rotation' or event.isAccepted()):
            super().mouseReleaseEvent(event)


class Rectangle(Core):
    def __init__(self):
        super().__init__()
        self.first_click_pos = None
        self.current_rectangle = None
        self.is_drawing = False
        self.selected_rectangle = None  

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