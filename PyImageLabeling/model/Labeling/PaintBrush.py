from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsScene, QGraphicsItem, QMessageBox
import cv2
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter, QPixmap, QColor, QRadialGradient
from PyQt6.QtCore import QPointF, Qt, QRectF, QRect
from collections import deque
from PyImageLabeling.model.Utils import Utils

class PaintBrushItem(QGraphicsItem):

    # Extra texture room (px) reserved when the stroke outgrows the current
    # texture, so a drag does not reallocate on every single mouse-move.
    _GROW_PAD = 64

    def __init__(self, core, x, y, color, size, brush_type="circle"):
        super().__init__()

        # Initialize the variable of the first point
        self.core = core
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.brush_type = brush_type
        # Cache the overlay: it is asked for on every paint/move, and
        # get_current_image_item() walks the model each time.
        self.overlay = self.core.get_current_image_item().get_labeling_overlay()
        self.labeling_overlay_painter = self.overlay.get_painter()

        self.position_x = int(self.x-(self.size/2))
        self.position_y = int(self.y-(self.size/2))
        self.bounding_rect = QRectF(self.position_x, self.position_y, self.size, self.size)
        self.bounding_rect = self.bounding_rect.intersected(core.get_current_image_item().image_qrectf)

        # Create the image of the first point
        self.texture = QPixmap(self.size, self.size) 
        self.texture.fill(Qt.GlobalColor.transparent)
        # top-left of `texture` in image coordinates: the UN-intersected
        # position, i.e. the texture always starts at the raw brush corner
        # (this is what the first-dab drawing below assumes).
        self.tex_x = self.position_x
        self.tex_y = self.position_y
        self._seed_x = self.x
        self._seed_y = self.y

        painter = QPainter(self.texture)
        
        # Draw based on brush type
        self._draw_brush_shape(painter, int(self.size/2), int(self.size/2))

        # Remove the existing pixel label already colored 
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.drawPixmap(QRect(0, 0, self.size, self.size), self.overlay.labeling_overlay_pixmap, self.bounding_rect.toRect())
        
        painter.end()
    
    def _draw_brush_shape(self, painter, center_x, center_y):
        """Draw different brush shapes based on brush_type.

        `self._seed_x/_seed_y` must hold the dab center in image coordinates
        (see the spray branch).
        """
        self._seed_x = center_x
        self._seed_y = center_y
        if self.brush_type == "circle":
            # Original circular brush
            self.pen = QPen(self.color, self.size)
            self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(self.pen)
            painter.drawPoint(center_x, center_y)
        
        elif self.brush_type == "square":
            # Square brush
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            half_size = self.size // 2
            painter.drawRect(center_x - half_size, center_y - half_size, self.size, self.size)
        
        elif self.brush_type == "diamond":
            # Diamond/rhombus brush
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            half_size = self.size // 2
            path.moveTo(center_x, center_y - half_size)  # Top
            path.lineTo(center_x + half_size, center_y)  # Right
            path.lineTo(center_x, center_y + half_size)  # Bottom
            path.lineTo(center_x - half_size, center_y)  # Left
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "star":
            # Star brush (5-pointed)
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
            # Triangle brush
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            half_size = self.size // 2
            path.moveTo(center_x, center_y - half_size)  # Top
            path.lineTo(center_x + half_size, center_y + half_size)  # Bottom right
            path.lineTo(center_x - half_size, center_y + half_size)  # Bottom left
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "cross":
            # Cross/plus brush
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            thickness = self.size // 3
            half_size = self.size // 2
            # Vertical bar
            painter.drawRect(center_x - thickness//2, center_y - half_size, thickness, self.size)
            # Horizontal bar
            painter.drawRect(center_x - half_size, center_y - thickness//2, self.size, thickness)
        
        elif self.brush_type == "x":
            # X/diagonal cross brush
            painter.setPen(QPen(self.color, max(2, self.size // 5), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            half_size = self.size // 2
            painter.drawLine(center_x - half_size, center_y - half_size, center_x + half_size, center_y + half_size)
            painter.drawLine(center_x + half_size, center_y - half_size, center_x - half_size, center_y + half_size)
        
        elif self.brush_type == "hexagon":
            # Hexagon brush
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
        
        elif self.brush_type == "spray":
            # Spray/scatter brush (random dots)
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            # Seed from the dab's position in IMAGE coordinates, not in
            # texture-local ones: the texture origin moves as the stroke
            # grows, so a local seed made the same dab change pattern
            # depending on how large the stroke already was.
            np.random.seed(int(self._seed_x + self._seed_y))
            num_dots = max(10, self.size // 2)
            radius = self.size // 2
            for _ in range(num_dots):
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0, radius)
                dot_x = center_x + dist * np.cos(angle)
                dot_y = center_y + dist * np.sin(angle)
                dot_size = max(1, self.size // 10)
                painter.drawEllipse(QPointF(dot_x, dot_y), dot_size, dot_size)
        
        elif self.brush_type == "soft":
            # Soft/blurred circular brush with gradient
            gradient = QRadialGradient(center_x, center_y, self.size // 2)
            gradient.setColorAt(0, self.color)
            transparent = QColor(self.color)
            transparent.setAlpha(0)
            gradient.setColorAt(1, transparent)
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(center_x, center_y), self.size // 2, self.size // 2)
        
        else:
            # Default to circle if unknown type
            self.pen = QPen(self.color, self.size)
            self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(self.pen)
            painter.drawPoint(center_x, center_y)
        
    def _grow_texture(self, need_rect):
        """Reallocate the texture so it covers need_rect, keeping what is drawn.

        Only called when the stroke leaves the current texture, and the new
        texture is padded so the next few moves do not reallocate again.
        The texture is clamped to the image rect: that keeps the dab clipping
        at the image border identical to re-allocating the exact union.
        """
        image_rect = self.core.get_current_image_item().image_qrectf
        pad = self._GROW_PAD
        x0 = min(self.tex_x, int(need_rect.x())) - pad
        y0 = min(self.tex_y, int(need_rect.y())) - pad
        x1 = max(self.tex_x + self.texture.width(),
                 int(need_rect.right())) + pad
        y1 = max(self.tex_y + self.texture.height(),
                 int(need_rect.bottom())) + pad
        # The texture is anchored on the raw brush corner, which can sit
        # outside the image (a dab clipped by the image border), so it must
        # not be clamped to the image rect.
        new_texture = QPixmap(max(1, x1 - x0), max(1, y1 - y0))
        new_texture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(new_texture)
        painter.drawPixmap(self.tex_x - x0, self.tex_y - y0, self.texture)
        painter.end()
        self.texture = new_texture
        self.tex_x = x0
        self.tex_y = y0

    def add_point(self, new_x, new_y):
        # Compute the bounding rect of the new point
        new_position_x = int(new_x-(self.size/2))
        new_position_y = int(new_y-(self.size/2))
        new_bounding_rect = QRectF(new_position_x, new_position_y, self.size, self.size)
        new_bounding_rect = new_bounding_rect.intersected(
            self.core.get_current_image_item().image_qrectf)
        if new_bounding_rect.isEmpty():
            return

        # Do the union of the two bounding rects
        self.united_bounding_rect = self.bounding_rect.united(new_bounding_rect)

        # Grow the texture only when the stroke actually outgrows it.
        if not (self.tex_x <= self.united_bounding_rect.x()
                and self.tex_y <= self.united_bounding_rect.y()
                and self.tex_x + self.texture.width()
                >= self.united_bounding_rect.right()
                and self.tex_y + self.texture.height()
                >= self.united_bounding_rect.bottom()):
            self._grow_texture(self.united_bounding_rect)

        painter = QPainter(self.texture)
        # Clip to the union so a dab at the image border is cut exactly
        # where the previous implementation cut it.
        painter.setClipRect(QRect(
            int(self.united_bounding_rect.x() - self.tex_x),
            int(self.united_bounding_rect.y() - self.tex_y),
            int(self.united_bounding_rect.width()),
            int(self.united_bounding_rect.height())))
        local_x = int(new_position_x - self.tex_x + (self.size/2))
        local_y = int(new_position_y - self.tex_y + (self.size/2))
        # image-space center of this dab (for the spray brush's RNG seed)
        self._seed_x = int(new_position_x + self.size / 2)
        self._seed_y = int(new_position_y + self.size / 2)
        self._draw_brush_shape(painter, local_x, local_y)

        # Erase the already-colored pixels. The old implementation drew the
        # new dab first, then the previous texture on top of it; with
        # SourceOver and the same color the result is identical to drawing
        # the dab on top, which is what happens here without a rebuild.
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.setClipRect(QRect(
            int(self.united_bounding_rect.x() - self.tex_x),
            int(self.united_bounding_rect.y() - self.tex_y),
            int(self.united_bounding_rect.width()),
            int(self.united_bounding_rect.height())))
        painter.drawPixmap(
            QRect(0, 0, self.texture.width(), self.texture.height()),
            self.overlay.labeling_overlay_pixmap,
            QRect(self.tex_x, self.tex_y,
                  self.texture.width(), self.texture.height()))
        painter.end()

        # Update the good variable for the painter
        self.bounding_rect = self.united_bounding_rect
        self.position_x = int(self.bounding_rect.x())
        self.position_y = int(self.bounding_rect.y())

    def boundingRect(self):
        return QRectF(self.tex_x, self.tex_y,
                      self.texture.width(), self.texture.height())

    def paint(self, painter, option, widget):
        painter.setOpacity(self.overlay.get_opacity())
        painter.drawPixmap(self.tex_x, self.tex_y, self.texture)

    def labeling_overlay_paint(self):
        self.labeling_overlay_painter.drawPixmap(
            self.tex_x, self.tex_y, self.texture)


class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.last_position_x, self.last_position_y = None, None
        self.point_spacing = 2
        self.paint_brush_items = []
        self.previous_pixmap = None

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__      

    def start_paint_brush(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("paint")
        
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        params = Utils.load_parameters()
        self.size_paint_brush = params["paint_brush"]["size"]
        # Load brush type from parameters, default to "circle" if not specified
        self.brush_type = params["paint_brush"].get("brush_type", "circle")
        self.color = self.get_current_label_item().get_color()
        
        self.paint_brush_item = PaintBrushItem(self, self.current_position_x, self.current_position_y, 
                                                self.color, self.size_paint_brush, self.brush_type)
        self.paint_brush_item.setZValue(2)
        self.zoomable_graphics_view.scene.addItem(self.paint_brush_item)
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y
        self.drawn_points = [(self.current_position_x, self.current_position_y)]

    def _dab_step(self):
        """Spacing between dabs when interpolating along a fast drag.

        Dabs only need to overlap, so this scales with the brush: a quarter
        of the diameter gives 75% overlap, which looks solid, instead of the
        fixed 2 px spacing that used to emit hundreds of dabs for a single
        long fast stroke.
        """
        return max(self.point_spacing,
                   max(1.0, self.size_paint_brush * self._DAB_OVERLAP_RATIO))

    # fraction of the brush diameter between two interpolated dabs
    _DAB_OVERLAP_RATIO = 1.0 / 6.0

    def move_paint_brush(self, current_position):
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        dx = self.current_position_x - self.last_position_x
        dy = self.current_position_y - self.last_position_y
        distance = (dx * dx + dy * dy) ** 0.5
        step = self._dab_step()
        if distance < step:
            return

        # A fast drag makes Qt report positions far apart: one dab per event
        # then leaves gaps (the brush is only `size` px wide, so any step
        # above that breaks the line into beads). Walk the segment and drop
        # overlapping dabs so the whole passage is covered.
        steps = int(distance // step)
        for i in range(1, steps + 1):
            t = i * step / distance
            x = int(round(self.last_position_x + dx * t))
            y = int(round(self.last_position_y + dy * t))
            self.paint_brush_item.add_point(x, y)
            self.drawn_points.append((x, y))
        # the real event position, in case the last step overshot it
        self.paint_brush_item.add_point(self.current_position_x,
                                        self.current_position_y)
        self.drawn_points.append((self.current_position_x,
                                  self.current_position_y))
        self.paint_brush_item.update()

        self.last_position_x, self.last_position_y = (self.current_position_x,
                                                      self.current_position_y)

    def _is_shape_closed(self, points, tolerance=10):
        """Return True if the drawn path forms a closed loop."""
        if len(points) < 10:
            return False
        first, last = points[0], points[-1]
        dist = np.hypot(first[0] - last[0], first[1] - last[1])
        adjusted_tolerance = tolerance + self.size_paint_brush
        return dist < adjusted_tolerance

    def _fill_closed_shape(self, points):
        """Fill a closed pen shape by creating a polygon path and filling it."""
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

    def end_paint_brush(self, release_position=None):
        # A fast stroke ends between two mouse-move events, so the release
        # point can be well past the last one we saw: interpolate that last
        # segment too, otherwise the stroke is cut short.
        if release_position is not None:
            class _P:
                def __init__(self, x, y):
                    self._x, self._y = x, y

                def x(self):
                    return self._x

                def y(self):
                    return self._y
            self.move_paint_brush(
                _P(release_position.x(), release_position.y()))

        # Paint the good pixmap 
        self.paint_brush_item.labeling_overlay_paint()

        # Display it
        self.get_current_image_item().update_labeling_overlay()

        # Remove the fake item 
        self.zoomable_graphics_view.scene.removeItem(self.paint_brush_item)

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