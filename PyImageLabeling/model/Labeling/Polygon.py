from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtGui import QPen, QCursor, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF
import math

HANDLE_SIZE = 8  # Size of corner handles for resizing
HANDLE_DETECTION_DISTANCE = 15  # Distance for auto-showing handles
CLOSE_DISTANCE = 20  # Distance threshold to close polygon

class PolygonItem(QGraphicsPolygonItem):
    def __init__(self, polygon, color=Qt.GlobalColor.red):
        super().__init__(polygon)

        self.pen = QPen(color, 2)
        self.pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(self.pen)

        self.setFlags(
            QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsPolygonItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsPolygonItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.handles = {}  # Dictionary to track vertex handles
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
        """Update vertex handles and rotation handle positions"""
        polygon = self.polygon()
        
        # Vertex handles for resizing
        self.handles = {}
        for i, point in enumerate(polygon):
            self.handles[f'vertex_{i}'] = QRectF(
                point - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), 
                QSizeF(HANDLE_SIZE, HANDLE_SIZE)
            )
        
        # Rotation handle at polygon center
        if polygon.size() > 0:
            center = polygon.boundingRect().center()
            self.handles['rotation'] = QRectF(
                center - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), 
                QSizeF(HANDLE_SIZE, HANDLE_SIZE)
            )

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
        
        # Check vertex handles
        for handle_rect in self.handles.values():
            if self.distance_to_rect(pos, handle_rect) < HANDLE_DETECTION_DISTANCE:
                near_handle = True
                break
        
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
  
        # Check handles
        for name, rect in self.handles.items():
            if rect.contains(pos):
                if name == 'rotation':
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                else:  # vertex handles
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                return
        
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        if self.handles_visible:
            # Draw vertex handles
            painter.setPen(QPen(Qt.GlobalColor.black, 1, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(Qt.GlobalColor.white, Qt.BrushStyle.SolidPattern))
            
            for name, handle_rect in self.handles.items():
                if name != 'rotation':
                    painter.drawRect(handle_rect)
            
            # Draw rotation handle (circular) at center
            if 'rotation' in self.handles:
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
                    # Store initial rotation data
                    center = self.polygon().boundingRect().center()
                    self.setTransformOriginPoint(center)
                    center_scene = self.mapToScene(center)
                    mouse_scene = self.mapToScene(event.pos())
                    self.initial_rotation = math.atan2(
                        mouse_scene.y() - center_scene.y(),
                        mouse_scene.x() - center_scene.x()
                    )
                    self.initial_angle = self.rotation()
                break

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected == 'rotation':
            # Handle rotation
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.handles_visible = False
            
            center = self.polygon().boundingRect().center()
            center_scene = self.mapToScene(center)
            mouse_scene = self.mapToScene(event.pos())
            
            current_angle = math.atan2(
                mouse_scene.y() - center_scene.y(),
                mouse_scene.x() - center_scene.x()
            )
            
            angle_diff = math.degrees(current_angle - self.initial_rotation)
            new_rotation = self.initial_angle + angle_diff
            self.setRotation(new_rotation)
            
            self.update_handles()
            self.update()
            
        elif self.handle_selected and self.handle_selected.startswith('vertex_'):
            # Handle vertex moving
            vertex_index = int(self.handle_selected.split('_')[1])
            polygon = self.polygon()
            
            if 0 <= vertex_index < polygon.size():
                polygon[vertex_index] = event.pos()
                self.setPolygon(polygon)
                self.update_handles()
                self.handles_visible = False
                self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.handle_selected == 'rotation':
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        self.handle_selected = None
        self.handles_visible = True
        self.update()

        # Only call super if we didn't handle rotation
        if not (self.handle_selected == 'rotation' or event.isAccepted()):
            super().mouseReleaseEvent(event)


class Polygon(Core):
    def __init__(self):
        super().__init__()
        self.polygon_points = []  # Store current polygon points
        self.is_drawing_polygon = False
        self.current_polygon_lines = []  # Preview lines
        self.first_point_indicator = None  # Visual indicator for first point
        self.selected_polygon = None

    def polygon(self):
        self.checked_button = self.polygon.__name__
        self.zoomable_graphics_view.scene.selectionChanged.connect(self.update_selected_polygon)
        
    def cleanup_temporary_polygon(self):
        """Remove preview lines and indicators"""
        for line in self.current_polygon_lines:
            if line in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(line)
        self.current_polygon_lines.clear()
        
        if self.first_point_indicator:
            if self.first_point_indicator in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(self.first_point_indicator)
            self.first_point_indicator = None

    def start_polygon_tool(self, current_position):
        """Mouse click → add point to polygon"""
        self.zoomable_graphics_view.change_cursor("polygon")
        current_pos = QPointF(current_position.x(), current_position.y())
        
        # If not currently drawing, start new polygon
        if not self.is_drawing_polygon:
            self.cleanup_temporary_polygon()
            self.polygon_points = [current_pos]
            self.is_drawing_polygon = True
            self.color = self.labels[self.current_label]["color"]
            
            # Add visual indicator for first point
            self.first_point_indicator = QGraphicsEllipseItem(
                current_pos.x() - 5, current_pos.y() - 5, 10, 10
            )
            self.first_point_indicator.setPen(QPen(self.color, 2))
            self.first_point_indicator.setBrush(QBrush(self.color))
            self.first_point_indicator.setZValue(3)
            self.zoomable_graphics_view.scene.addItem(self.first_point_indicator)
            
        else:
            # Check if close to first point to close polygon
            first_point = self.polygon_points[0]
            distance = math.sqrt(
                (current_pos.x() - first_point.x()) ** 2 + 
                (current_pos.y() - first_point.y()) ** 2
            )
            
            if distance <= CLOSE_DISTANCE and len(self.polygon_points) >= 3:
                # Close the polygon
                self.finalize_polygon()
                return
            
            # Add new point
            self.polygon_points.append(current_pos)
            
            # Create preview line from previous point to current point
            prev_point = self.polygon_points[-2]
            line = QGraphicsLineItem(
                prev_point.x(), prev_point.y(),
                current_pos.x(), current_pos.y()
            )
            pen = QPen(self.color, 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            line.setPen(pen)
            line.setZValue(2)
            self.zoomable_graphics_view.scene.addItem(line)
            self.current_polygon_lines.append(line)

    def move_polygon_tool(self, current_position):
        """Mouse move → update preview line from last point to current position"""
        if not self.is_drawing_polygon or len(self.polygon_points) == 0:
            return
            
        current_pos = QPointF(current_position.x(), current_position.y())
        
        # Remove previous preview line if exists
        if hasattr(self, 'preview_line') and self.preview_line:
            if self.preview_line in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(self.preview_line)
        
        # Create new preview line from last point to current mouse position
        last_point = self.polygon_points[-1]
        self.preview_line = QGraphicsLineItem(
            last_point.x(), last_point.y(),
            current_pos.x(), current_pos.y()
        )
        pen = QPen(self.color, 1)
        pen.setStyle(Qt.PenStyle.DotLine)
        self.preview_line.setPen(pen)
        self.preview_line.setZValue(1)
        self.zoomable_graphics_view.scene.addItem(self.preview_line)

    def finalize_polygon(self):
        """Create final polygon from collected points"""
        if len(self.polygon_points) < 3:
            return
            
        # Clean up temporary items
        self.cleanup_temporary_polygon()
        if hasattr(self, 'preview_line') and self.preview_line:
            if self.preview_line in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(self.preview_line)
            self.preview_line = None
        
        # Create QPolygonF from points
        qt_polygon = QPolygonF(self.polygon_points)
        
        # Create final polygon item
        final_polygon = PolygonItem(qt_polygon, self.color)
        final_polygon.setZValue(2)
        final_polygon.setFlag(QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.zoomable_graphics_view.scene.addItem(final_polygon)
        self.selected_polygon = final_polygon
        
        # Reset state
        self.polygon_points = []
        self.is_drawing_polygon = False

    def cancel_polygon(self):
        """Cancel current polygon drawing"""
        if self.is_drawing_polygon:
            self.cleanup_temporary_polygon()
            if hasattr(self, 'preview_line') and self.preview_line:
                if self.preview_line in self.zoomable_graphics_view.scene.items():
                    self.zoomable_graphics_view.scene.removeItem(self.preview_line)
                self.preview_line = None
            self.polygon_points = []
            self.is_drawing_polygon = False

    def end_polygon_tool(self):
        """Mouse release → not used for polygon tool (click-based)"""
        pass

    def update_selected_polygon(self):
        """Update selected_polygon when user clicks on a polygon"""
        selected_items = self.zoomable_graphics_view.scene.selectedItems()
        if selected_items:
            item = selected_items[-1]  # last selected item
            if isinstance(item, PolygonItem):
                self.selected_polygon = item
        else:
            self.selected_polygon = None

    def clear_polygon(self):
        """Remove the currently selected polygon from the scene"""
        if self.selected_polygon:
            if self.selected_polygon in self.zoomable_graphics_view.scene.items():
                self.zoomable_graphics_view.scene.removeItem(self.selected_polygon)
            self.selected_polygon = None
        
        # Also cancel any ongoing polygon drawing
        self.cancel_polygon()