from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem, QMessageBox
import cv2
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter, QPixmap, QColor, QRadialGradient, QPainterPathStroker
from PyQt6.QtCore import QPointF, Qt, QRectF
from collections import deque
from PyImageLabeling.model.Utils import Utils


class SmoothPaintBrushItem(QGraphicsPathItem):
    """
    Ultra-smooth brush using QPainterPath during drawing (vector = super light).
    Rasterizes to pixels only at the end.
    """

    def __init__(self, core, start_x, start_y, color, size, brush_type="circle"):
        super().__init__()
        
        self.core = core
        self.color = color
        self.size = size
        self.brush_type = brush_type
        
        # Create the smooth path (this is VERY lightweight - just vector math)
        self.smooth_path = QPainterPath()
        self.smooth_path.moveTo(start_x, start_y)
        
        # Store points for path smoothing
        self.points = [QPointF(start_x, start_y)]
        
        # Set up the pen for smooth vector rendering
        self.display_pen = self._create_display_pen()
        self.setPen(self.display_pen)
        self.setOpacity(self.core.get_current_image_item().get_labeling_overlay().get_opacity())
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        
        # For final rasterization
        self.overlay_painter = self.core.get_current_image_item().get_labeling_overlay().get_painter()
        
        # Control smoothing
        self.smoothing_threshold = 3  # Points to accumulate before updating path

    def _create_display_pen(self):
        pen = QPen(self.color)
        pen.setWidth(self.size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setColor(self.color)
        return pen

    def add_point(self, x, y):
        """
        Add point to the smooth path (ULTRA LIGHTWEIGHT - just vector operations).
        Uses quadratic curves for smoothness.
        """
        new_point = QPointF(x, y)
        self.points.append(new_point)
        
        num_points = len(self.points)
        
        if num_points == 2:
            # Just draw a line for the second point
            self.smooth_path.lineTo(new_point)
        elif num_points > 2:
            # Use quadratic Bezier curve for smoothness
            # Control point is the previous point
            # End point is the average of current and previous
            p0 = self.points[-3]  # Two points ago
            p1 = self.points[-2]  # Previous point
            p2 = new_point        # Current point
            
            # Create smooth curve using quadTo
            # Control point is p1, end point is midpoint between p1 and p2
            mid_point = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
            self.smooth_path.quadTo(p1, mid_point)
        
        # Update the graphics item path (this is very fast - just vector data)
        self.setPath(self.smooth_path)

    def _rasterize_shaped_brush_single(self, point):
        stamp = self._create_shape_stamp()
        self.overlay_painter.drawPixmap(
            int(point.x() - self.size // 2),
            int(point.y() - self.size // 2),
            stamp
        )
        
    def finalize_and_rasterize(self):
        """
        Finish the path and rasterize it to pixels on the overlay.
        This is called only ONCE at the end.
        """
        # Complete the path to the last point
        if len(self.points) == 1:
            point = self.points[0]

            if self.brush_type == "circle":
                self.overlay_painter.setPen(Qt.PenStyle.NoPen)
                self.overlay_painter.setBrush(QBrush(self.color))
                self.overlay_painter.drawEllipse(
                    point, self.size / 2, self.size / 2
                )
            else:
                self._rasterize_shaped_brush_single(point)

        elif len(self.points) > 1:
            self.smooth_path.lineTo(self.points[-1])
            self.setPath(self.smooth_path)
        
        # Now rasterize based on brush type
        if self.brush_type == "circle":
            self._rasterize_smooth_circle()
        elif self.brush_type in ["square", "diamond", "star", "triangle", "cross", "x", "hexagon"]:
            self._rasterize_shaped_brush()
        elif self.brush_type == "spray":
            self._rasterize_spray()
        elif self.brush_type == "soft":
            self._rasterize_soft_brush()
        else:
            self._rasterize_smooth_circle()

    def _rasterize_smooth_circle(self):
        """Rasterize smooth circular brush (fastest method)"""
        # Create a pen/brush for rasterization
        pen = QPen(self.color, self.size, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        
        # Draw the path on the overlay
        self.overlay_painter.setPen(pen)
        self.overlay_painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.overlay_painter.drawPath(self.smooth_path)

    def _rasterize_soft_brush(self):
        """Rasterize soft brush with gradient"""
        # For soft brush, we need to draw stamps along the path
        # Sample points along the smooth path
        path_length = self.smooth_path.length()
        if path_length == 0:
            return
        
        # Sample at regular intervals
        spacing = max(1, self.size // 4)
        num_samples = max(2, int(path_length / spacing))
        
        # Create soft brush stamp
        stamp = QPixmap(self.size, self.size)
        stamp.fill(Qt.GlobalColor.transparent)
        stamp_painter = QPainter(stamp)
        
        center = self.size // 2
        gradient = QRadialGradient(center, center, self.size // 2)
        gradient.setColorAt(0, self.color)
        transparent = QColor(self.color)
        transparent.setAlpha(0)
        gradient.setColorAt(1, transparent)
        
        stamp_painter.setBrush(QBrush(gradient))
        stamp_painter.setPen(Qt.PenStyle.NoPen)
        stamp_painter.drawEllipse(QPointF(center, center), self.size // 2, self.size // 2)
        stamp_painter.end()
        
        # Draw stamps along the path
        for i in range(num_samples):
            percent = i / max(1, num_samples - 1)
            point = self.smooth_path.pointAtPercent(percent)
            self.overlay_painter.drawPixmap(
                int(point.x() - self.size // 2),
                int(point.y() - self.size // 2),
                stamp
            )

    def _rasterize_spray(self):
        """Rasterize spray brush"""
        path_length = self.smooth_path.length()
        if path_length == 0:
            return
        
        # Sample points along path
        spacing = max(2, self.size // 3)
        num_samples = max(2, int(path_length / spacing))
        
        # Create spray stamp
        stamp = QPixmap(self.size, self.size)
        stamp.fill(Qt.GlobalColor.transparent)
        stamp_painter = QPainter(stamp)
        stamp_painter.setBrush(QBrush(self.color))
        stamp_painter.setPen(Qt.PenStyle.NoPen)
        
        center = self.size // 2
        np.random.seed(42)  # Consistent pattern
        num_dots = max(10, self.size // 2)
        radius = self.size // 2
        
        for _ in range(num_dots):
            angle = np.random.uniform(0, 2 * np.pi)
            dist = np.random.uniform(0, radius)
            dot_x = center + dist * np.cos(angle)
            dot_y = center + dist * np.sin(angle)
            dot_size = max(1, self.size // 10)
            stamp_painter.drawEllipse(QPointF(dot_x, dot_y), dot_size, dot_size)
        
        stamp_painter.end()
        
        # Draw stamps along path
        for i in range(num_samples):
            percent = i / max(1, num_samples - 1)
            point = self.smooth_path.pointAtPercent(percent)
            self.overlay_painter.drawPixmap(
                int(point.x() - self.size // 2),
                int(point.y() - self.size // 2),
                stamp
            )

    def _rasterize_shaped_brush(self):
        """Rasterize shaped brushes (square, diamond, star, etc.)"""
        path_length = self.smooth_path.length()
        if path_length == 0:
            return
        
        # Sample at smaller intervals for shaped brushes
        spacing = max(1, self.size // 5)
        num_samples = max(2, int(path_length / spacing))
        
        # Create shape stamp
        stamp = self._create_shape_stamp()
        
        # Draw stamps along the path
        for i in range(num_samples):
            percent = i / max(1, num_samples - 1)
            point = self.smooth_path.pointAtPercent(percent)
            self.overlay_painter.drawPixmap(
                int(point.x() - self.size // 2),
                int(point.y() - self.size // 2),
                stamp
            )

    def _create_shape_stamp(self):
        """Create a stamp for the current brush shape"""
        stamp = QPixmap(self.size, self.size)
        stamp.fill(Qt.GlobalColor.transparent)
        painter = QPainter(stamp)
        
        center_x = center_y = self.size // 2
        
        if self.brush_type == "square":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            half_size = self.size // 2
            painter.drawRect(center_x - half_size, center_y - half_size, self.size, self.size)
        
        elif self.brush_type == "diamond":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            half_size = self.size // 2
            path.moveTo(center_x, center_y - half_size)
            path.lineTo(center_x + half_size, center_y)
            path.lineTo(center_x, center_y + half_size)
            path.lineTo(center_x - half_size, center_y)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "star":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            outer_radius = self.size // 2
            inner_radius = outer_radius // 2
            
            for i in range(10):
                angle = (i * 36 - 90) * np.pi / 180
                radius = outer_radius if i % 2 == 0 else inner_radius
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "triangle":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            half_size = self.size // 2
            path.moveTo(center_x, center_y - half_size)
            path.lineTo(center_x + half_size, center_y + half_size)
            path.lineTo(center_x - half_size, center_y + half_size)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "cross":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            thickness = self.size // 3
            half_size = self.size // 2
            painter.drawRect(center_x - thickness//2, center_y - half_size, thickness, self.size)
            painter.drawRect(center_x - half_size, center_y - thickness//2, self.size, thickness)
        
        elif self.brush_type == "x":
            painter.setPen(QPen(self.color, max(2, self.size // 5), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            half_size = self.size // 2
            painter.drawLine(center_x - half_size, center_y - half_size, center_x + half_size, center_y + half_size)
            painter.drawLine(center_x + half_size, center_y - half_size, center_x - half_size, center_y + half_size)
        
        elif self.brush_type == "hexagon":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            radius = self.size // 2
            for i in range(6):
                angle = (i * 60) * np.pi / 180
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)
        
        painter.end()
        return stamp


class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.last_position_x, self.last_position_y = None, None
        self.point_spacing = 2  # Minimum distance between points
        self.paint_brush_item = None

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__      

    def start_paint_brush(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("paint")
        
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        params = Utils.load_parameters()
        self.size_paint_brush = params["paint_brush"]["size"]
        self.brush_type = params["paint_brush"].get("brush_type", "circle")
        self.color = self.get_current_label_item().get_color()
        
        # Create the smooth vector-based brush item
        self.paint_brush_item = SmoothPaintBrushItem(
            self, 
            self.current_position_x, 
            self.current_position_y, 
            self.color, 
            self.size_paint_brush, 
            self.brush_type
        )
        self.paint_brush_item.setZValue(2)
        self.zoomable_graphics_view.scene.addItem(self.paint_brush_item)
        
        self.last_position_x = self.current_position_x
        self.last_position_y = self.current_position_y
        self.drawn_points = [(self.current_position_x, self.current_position_y)]

    def move_paint_brush(self, current_position):
        if self.paint_brush_item is None:
            return
            
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        # Check minimum spacing to avoid too many points
        distance = Utils.compute_diagonal(
            self.current_position_x, self.current_position_y, 
            self.last_position_x, self.last_position_y
        )
        
        if distance < self.point_spacing:
            return 
        
        # Add point to the smooth path (ULTRA FAST - just vector math)
        self.drawn_points.append((self.current_position_x, self.current_position_y))
        self.paint_brush_item.add_point(self.current_position_x, self.current_position_y)
        
        self.last_position_x = self.current_position_x
        self.last_position_y = self.current_position_y

    def _is_shape_closed(self, points, tolerance=10):
        """Check if the drawn path forms a closed loop"""
        if len(points) < 10:
            return False
        first, last = points[0], points[-1]
        dist = np.hypot(first[0] - last[0], first[1] - last[1])
        adjusted_tolerance = tolerance + self.size_paint_brush
        return dist < adjusted_tolerance

    def _fill_closed_shape(self, points):
        """Fill a closed shape"""
        path = QPainterPath()
        if not points:
            return
        
        path.moveTo(QPointF(points[0][0], points[0][1]))
        
        for x, y in points[1:]:
            path.lineTo(QPointF(x, y))
        
        path.closeSubpath()
        
        painter = self.get_current_image_item().get_labeling_overlay().get_painter()
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        
        self.get_current_image_item().update_labeling_overlay()

    def end_paint_brush(self):
        if self.paint_brush_item is None:
            return
        
        # Now rasterize the smooth vector path to pixels (done ONCE at the end)
        self.paint_brush_item.finalize_and_rasterize()
        
        # Update the overlay
        self.get_current_image_item().update_labeling_overlay()

        # Remove the vector preview from the scene
        self.zoomable_graphics_view.scene.removeItem(self.paint_brush_item)
        self.paint_brush_item = None

        # Check for closed shape
        if hasattr(self, "drawn_points") and self._is_shape_closed(self.drawn_points):
            reply = QMessageBox.question(
                self.view,
                "Fill Shape",
                "Detected a closed shape. Do you want to fill it automatically?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._fill_closed_shape(self.drawn_points)
        
        self.controller.ml_update_stats()