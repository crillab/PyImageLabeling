from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPainterPath
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from model.Core import Core
import math
from model.Utils import Utils

class Eraser(Core):
    def __init__(self):
        super().__init__()
        self.erasing_active = False
        self.last_pos = None

    def eraser(self):
        self.checked_button = self.eraser.__name__

    def start_eraser(self, scene_pos):
        self.eraser_size = Utils.load_parameters()["eraser"]["size"] 
        self.view.zoomable_graphics_view.change_cursor("eraser")
        self.erasing_active = True
        self.last_pos = scene_pos
        self.erase_at_position(scene_pos)

    def move_eraser(self, scene_pos):
        if self.erasing_active:
            if self.last_pos:
                self.erase_line(self.last_pos, scene_pos)
            else:
                self.erase_at_position(scene_pos)
            self.last_pos = scene_pos

    def end_eraser(self):
        self.erasing_active = False
        self.last_pos = None

    def erase_at_position(self, scene_pos):
        """Erase all drawing elements at the given position"""
        self._erase_paint_brush_items(scene_pos)
        self._erase_magic_pen_overlay(scene_pos)
        self._erase_contour_filling_overlays(scene_pos)

    def erase_line(self, start_pos, end_pos):
        """Smooth erasing between two points"""
        distance = self._calculate_distance(start_pos, end_pos)
        steps = max(1, int(distance / (self.eraser_size/ 2)))
        for i in range(steps + 1):
            t = i / steps
            interp_x = start_pos.x() + (end_pos.x() - start_pos.x()) * t
            interp_y = start_pos.y() + (end_pos.y() - start_pos.y()) * t
            self.erase_at_position(QPointF(interp_x, interp_y))

    def _erase_paint_brush_items(self, scene_pos):
        """Erase QGraphicsItems from PaintBrush strokes"""
        scene = self.view.zoomable_graphics_view.scene
        eraser_rect = QRectF(
            scene_pos.x() - self.eraser_size,
            scene_pos.y() - self.eraser_size,
            self.eraser_size * 2,
            self.eraser_size * 2
        )

        items_in_area = scene.items(eraser_rect)
        items_to_remove = []
        items_to_modify = []

        for item in items_in_area:
            if isinstance(item, QGraphicsEllipseItem):
                center = item.rect().center()
                scene_center = item.mapToScene(center)
                if self._calculate_distance(scene_pos, scene_center) <= self.eraser_size:
                    items_to_remove.append(item)
            elif isinstance(item, QGraphicsPathItem):
                new_paths = self._erase_path_portion(item.path(), scene_pos, self.eraser_size)
                if not new_paths:
                    items_to_remove.append(item)
                else:
                    items_to_modify.append((item, new_paths))

        for item in items_to_remove:
            scene.removeItem(item)
        for item, new_paths in items_to_modify:
            scene.removeItem(item)
            for segment in new_paths:
                if not segment.isEmpty():
                    new_item = QGraphicsPathItem(segment)
                    new_item.setPen(item.pen())
                    new_item.setBrush(item.brush())
                    new_item.setZValue(item.zValue())
                    new_item.setOpacity(item.opacity())
                    scene.addItem(new_item)

    def _erase_path_portion(self, path: QPainterPath, eraser_center: QPointF, eraser_radius: float):
        """Remove portions of a path intersecting the eraser circle"""
        if path.length() == 0:
            return []

        sample_distance = min(2.0, eraser_radius / 4)
        num_samples = max(int(path.length() / sample_distance), 1)
        sampled_points = []

        for i in range(num_samples + 1):
            t = i / num_samples
            point = path.pointAtPercent(t)
            keep = self._calculate_distance(eraser_center, point) > eraser_radius
            sampled_points.append((point, keep))

        path_segments = []
        current_segment = []

        for point, keep in sampled_points:
            if keep:
                current_segment.append(point)
            elif current_segment:
                if len(current_segment) > 1:
                    segment = QPainterPath()
                    segment.moveTo(current_segment[0])
                    for p in current_segment[1:]:
                        segment.lineTo(p)
                    path_segments.append(segment)
                current_segment = []

        if current_segment and len(current_segment) > 1:
            segment = QPainterPath()
            segment.moveTo(current_segment[0])
            for p in current_segment[1:]:
                segment.lineTo(p)
            path_segments.append(segment)

        return path_segments

    def _erase_magic_pen_overlay(self, scene_pos):
        if self.overlayers_pixmap and self.overlayer_pixmap_item:
            self._erase_from_pixmap_overlay(self.overlayers_pixmap, self.overlayer_pixmap_item, scene_pos)

    def _erase_contour_filling_overlays(self, scene_pos):
        if self.overlay_pixmap_filled and self.overlay_pixmap_item_filled:
            self._erase_from_pixmap_overlay(self.overlay_pixmap_filled, self.overlay_pixmap_item_filled, scene_pos)

        if hasattr(self, 'filled_points'):
            self._erase_filled_points(self.filled_points, scene_pos)

    def _erase_from_pixmap_overlay(self, overlay_pixmaps, overlay_item, scene_pos):
        """Erase from a pixmap overlay by painting transparent pixels"""
        if not overlay_pixmaps or not overlay_item:
            return

        # Take the topmost overlay for painting
        overlay_image = overlay_pixmaps[-1]

        # Paint eraser on the image
        painter = QPainter(overlay_image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(Qt.PenStyle.NoPen)

        erase_x = int(scene_pos.x() - self.eraser_size)
        erase_y = int(scene_pos.y() - self.eraser_size)
        erase_diameter = int(self.eraser_size * 2)

        painter.drawEllipse(erase_x, erase_y, erase_diameter, erase_diameter)
        painter.end()

        # Convert QImage to QPixmap before setting
        self.update_overlay(overlay_image)

    def _calculate_distance(self, pos1, pos2):
        dx = pos1.x() - pos2.x()
        dy = pos1.y() - pos2.y()
        return math.sqrt(dx * dx + dy * dy)
