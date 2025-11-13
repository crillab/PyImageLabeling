from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtGui import QPen, QBrush
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

HANDLE_SIZE = 8  # Size of handles for resizing
HANDLE_DETECTION_DISTANCE = 15  # Distance for auto-showing handles


class EllipseItem(QGraphicsEllipseItem):
    def __init__(self, x, y, width, height, color=Qt.GlobalColor.red, rotation=0):
        super().__init__(x, y, width, height)

        self.pen = QPen(color, 2)
        self.pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(self.pen)

        self.model_ref = None  # Reference to model data dictionary
        
        # Set initial rotation if provided
        if rotation != 0:
            self.setTransformOriginPoint(self.rect().center())
            self.setRotation(rotation)

        self.setFlags(
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.handles = {}  # Dictionary to track handles
        self.rotation_handle = None  # Rotation handle
        self.handle_selected = None
        self.mouse_press_pos = None
        self.handles_visible = False
        self.initial_rotation = 0
        self.initial_angle = 0
        
        # Accept hover events to detect mouse proximity
        self.setAcceptHoverEvents(True)
        
        self.update_handles()

    def itemChange(self, change, value):
        """Track position and transform changes to update model"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.update_model()  # update coordinates whenever the ellipse moves
        elif change == QGraphicsItem.GraphicsItemChange.ItemTransformHasChanged:
            self.update_model()  # update when rotated or transformed
        return super().itemChange(change, value)

    def update_model(self):
        """Push the updated ellipse back to the model list."""
        if self.model_ref is not None:
            # Get the center position in scene coordinates
            center_scene = self.mapToScene(self.rect().center())
            
            # Store the unrotated dimensions
            rect = self.rect()
            
            # Calculate top-left position based on center
            x = center_scene.x() - rect.width() / 2
            y = center_scene.y() - rect.height() / 2
            
            self.model_ref["x"] = x
            self.model_ref["y"] = y
            self.model_ref["width"] = rect.width()
            self.model_ref["height"] = rect.height()
            self.model_ref["rotation"] = self.rotation()

    def get_ellipse_point(self, angle_degrees):
        """Get a point on the ellipse perimeter at the given angle"""
        rect = self.rect()
        center_x = rect.center().x()
        center_y = rect.center().y()
        
        # Semi-major and semi-minor axes
        a = rect.width() / 2  # horizontal radius
        b = rect.height() / 2  # vertical radius
        
        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)
        
        # Parametric equations for ellipse
        x = center_x + a * math.cos(angle_rad)
        y = center_y + b * math.sin(angle_rad)
        
        return QPointF(x, y)

    def update_handles(self):
        """Update handle positions on the ellipse perimeter"""
        rect = self.rect()
        
        # Place handles at 0°, 90°, 180°, 270° on the ellipse perimeter
        right_point = self.get_ellipse_point(0)      # Right (0°)
        bottom_point = self.get_ellipse_point(90)    # Bottom (90°) 
        left_point = self.get_ellipse_point(180)     # Left (180°)
        top_point = self.get_ellipse_point(270)      # Top (270°)
        
        # Create handle rectangles centered on these points
        self.handles = {
            'right': QRectF(right_point - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'bottom': QRectF(bottom_point - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'left': QRectF(left_point - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'top': QRectF(top_point - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE)),
            'rotation': QRectF(QPointF(rect.center()) - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE))
        }

    def check_handle_proximity(self, pos):
        """Show handles when cursor is inside the circle or near a handle (ignore selection)."""
        # Check if cursor is inside the ellipse (circle area)
        inside_circle = self.rect().contains(pos)

        # Check if cursor is close to any handle
        near_handle = any(
            self.distance_to_rect(pos, rect) < HANDLE_DETECTION_DISTANCE
            for rect in self.handles.values()
        )

        # Show handles if inside or near handle
        should_show = inside_circle or near_handle

        if should_show != self.handles_visible:
            self.handles_visible = should_show
            self.update()

    @staticmethod
    def distance_to_rect(point, rect):
        """Calculate distance from point to rectangle center"""
        center = rect.center()
        return math.hypot(point.x() - center.x(), point.y() - center.y())

    def update_cursor(self, pos):
        """Update cursor based on which handle is under mouse"""
        if not self.handles_visible:
            return
  
        # Check resize handles
        for name, rect in self.handles.items():
            if rect.contains(pos):
                if name == 'rotation':
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                elif name in ['right', 'left']:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif name in ['top', 'bottom']:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                return
        
        self.setCursor(Qt.CursorShape.SizeAllCursor)

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

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        if self.handles_visible:
            # Draw resize handles
            painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(Qt.GlobalColor.white, Qt.BrushStyle.SolidPattern))
            
            # Draw square handles for resize
            for name, handle_rect in self.handles.items():
                if name != 'rotation':
                    painter.drawRect(handle_rect)
            
            # Draw rotation handle (circular) at center
            if self.handles.get('rotation'):
                painter.setPen(QPen(Qt.GlobalColor.blue, 2, Qt.PenStyle.SolidLine))
                painter.setBrush(QBrush(Qt.GlobalColor.blue, Qt.BrushStyle.SolidPattern))
                painter.drawEllipse(self.handles['rotation'])

    def mousePressEvent(self, event):
        self.handle_selected = None
        self.mouse_press_pos = event.pos()

        if not self.handles_visible:
            super().mousePressEvent(event)
            return

        # Check handles
        for name, rect in self.handles.items():
            if rect.contains(event.pos()):
                self.handle_selected = name
                if name == 'rotation':
                    # Store initial rotation data for rotation handle
                    rect_center = self.rect().center()
                    self.setTransformOriginPoint(rect_center)
                    
                    rect_center_scene = self.mapToScene(rect_center)
                    mouse_scene_pos = self.mapToScene(event.pos())
                    self.initial_rotation = math.atan2(
                        mouse_scene_pos.y() - rect_center_scene.y(),
                        mouse_scene_pos.x() - rect_center_scene.x()
                    )
                    self.initial_angle = self.rotation()
                break

        if self.handle_selected:
            self.handles_visible = False
            self.update()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected == 'rotation':
            self.handles_visible = False
            self.rotate_item(event)
        elif self.handle_selected:
            self.handles_visible = False
            self.resize_item(event)
        else:
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
        """Handle rotation of the ellipse"""
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        
        rect_center = self.rect().center()
        self.setTransformOriginPoint(rect_center)
        
        # Map center to scene coordinates
        rect_center_scene = self.mapToScene(rect_center)
        
        # Calculate current mouse angle relative to ellipse center
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
        self.update_model()

    def resize_item(self, event):
        """Handle resizing of the ellipse"""
        pos = event.pos()
        rect = self.rect()
        center = rect.center()
        
        if self.handle_selected == 'right':
            # Resize horizontally from right edge
            new_width = 2 * abs(pos.x() - center.x())
            new_width = max(10, new_width)  # Minimum width
            rect.setWidth(new_width)
            rect.moveCenter(center)
            
        elif self.handle_selected == 'left':
            # Resize horizontally from left edge
            new_width = 2 * abs(pos.x() - center.x())
            new_width = max(10, new_width)  # Minimum width
            rect.setWidth(new_width)
            rect.moveCenter(center)
            
        elif self.handle_selected == 'bottom':
            # Resize vertically from bottom edge
            new_height = 2 * abs(pos.y() - center.y())
            new_height = max(10, new_height)  # Minimum height
            rect.setHeight(new_height)
            rect.moveCenter(center)
            
        elif self.handle_selected == 'top':
            # Resize vertically from top edge
            new_height = 2 * abs(pos.y() - center.y())
            new_height = max(10, new_height)  # Minimum height
            rect.setHeight(new_height)
            rect.moveCenter(center)

        self.setRect(rect)
        self.update_handles()
        self.update()
        self.update_model()