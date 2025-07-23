


from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyImageLabeling.model.Core import Core
import math

class Eraser(Core):
    def __init__(self):
        super().__init__()
        self.erasing_active = False

    def eraser(self):
        self.checked_button = self.eraser.__name__

    def set_eraser_radius(self):
        """Set the eraser radius"""
        self.eraser_radius = max(1.0, self.view.eraser_size)

    def start_eraser(self, scene_pos):
        """Start erasing at the given position"""
        self.view.zoomable_graphics_view.change_cursor("eraser")
        self.erasing_active = True
        self.erase_at_position(scene_pos)

    def move_eraser(self, scene_pos):
        """Continue erasing as mouse moves"""
        if self.erasing_active:
            self.erase_at_position(scene_pos)

    def end_eraser(self):
        """Stop erasing"""
        self.erasing_active = False

    def erase_at_position(self, scene_pos):
        """Erase all drawing elements at the given position"""
        # Erase from PaintBrush (scene items)
        self._erase_paint_brush_items(scene_pos)

        # Erase from MagicPen (overlay pixmap)
        self._erase_magic_pen_overlay(scene_pos)

        # Erase from ContourFilling (both contours and filled shapes)
        self._erase_contour_filling_overlays(scene_pos)

    def _erase_paint_brush_items(self, scene_pos):
        """Erase paint brush items (QGraphicsItems) from the scene"""
        items_to_remove = []
        items_to_modify = []
        scene = self.view.zoomable_graphics_view.scene

        # Create QRectF for the eraser area
        eraser_rect = QRectF(
            scene_pos.x() - self.view.eraser_size,
            scene_pos.y() - self.view.eraser_size,
            self.view.eraser_size * 2,
            self.view.eraser_size * 2
        )

        items_in_area = scene.items(eraser_rect)

        for item in items_in_area:
            # Check if it's a paint brush item (ellipse or path)
            if isinstance(item, (QGraphicsEllipseItem, QGraphicsPathItem)):
                # For ellipse items (individual points)
                if isinstance(item, QGraphicsEllipseItem):
                    item_center = item.rect().center()
                    item_scene_pos = item.mapToScene(item_center)
                    distance = self._calculate_distance(scene_pos, item_scene_pos)

                    if distance <= self.view.eraser_size:
                        items_to_remove.append(item)

                # For path items (brush strokes) - modify the path instead of removing entirely
                elif isinstance(item, QGraphicsPathItem):
                    original_path = item.path()
                    new_paths = self._erase_path_portion(original_path, scene_pos, self.view.eraser_size)
                    
                    if not new_paths:
                        # If the entire path was erased, remove the item
                        items_to_remove.append(item)
                    else:
                        # If the path was modified, replace with new segments
                        items_to_modify.append((item, new_paths))

        # Remove the items that were completely erased
        for item in items_to_remove:
            scene.removeItem(item)
        
        # Update the paths that were partially erased
        for item, new_paths in items_to_modify:
            # Remove the old item completely
            scene.removeItem(item)
            
            # Create separate items for each disconnected path segment
            for path_segment in new_paths:
                if not path_segment.isEmpty():
                    new_item = QGraphicsPathItem(path_segment)
                    # Copy the original item's properties (pen, brush, etc.)
                    new_item.setPen(item.pen())
                    new_item.setBrush(item.brush())
                    new_item.setZValue(item.zValue())
                    new_item.setOpacity(item.opacity())
                    scene.addItem(new_item)

        if items_to_remove or items_to_modify:
            self.view.zoomable_graphics_view.update()

    def _erase_path_portion(self, path, eraser_center, eraser_radius):
        """Remove portions of a path that intersect with the eraser circle and return separate path segments"""
        from PyQt6.QtGui import QPainterPath
        from PyQt6.QtCore import QPointF
        
        # Sample points along the path
        path_length = path.length()
        if path_length == 0:
            return []
        
        sample_distance = min(2.0, eraser_radius / 4)  # Sample every 2 pixels or quarter eraser radius
        num_samples = max(int(path_length / sample_distance), 1)
        
        # Collect points and their keep/erase status
        sampled_points = []
        for i in range(num_samples + 1):
            t = i / num_samples if num_samples > 0 else 0
            point = path.pointAtPercent(t)
            distance = self._calculate_distance(eraser_center, point)
            keep = distance > eraser_radius
            sampled_points.append((point, keep))
        
        # Build separate path segments for continuous sequences of kept points
        path_segments = []
        current_segment_points = []
        
        for point, keep in sampled_points:
            if keep:
                current_segment_points.append(point)
            else:
                # End current segment if it has points
                if current_segment_points:
                    if len(current_segment_points) > 1:  # Need at least 2 points for a line
                        segment = QPainterPath()
                        segment.moveTo(current_segment_points[0])
                        for p in current_segment_points[1:]:
                            segment.lineTo(p)
                        path_segments.append(segment)
                    current_segment_points = []
        
        # Don't forget the last segment
        if current_segment_points:
            if len(current_segment_points) > 1:
                segment = QPainterPath()
                segment.moveTo(current_segment_points[0])
                for p in current_segment_points[1:]:
                    segment.lineTo(p)
                path_segments.append(segment)
        
        return path_segments

    def _erase_magic_pen_overlay(self, scene_pos):
        """Erase from magic pen overlay pixmap"""

        if self.overlay_pixmap:
            print("contour333")
            self._erase_from_pixmap_overlay(
                self.overlay_pixmap,
                self.overlay_pixmap_item,
                scene_pos
            )

    def _erase_contour_filling_overlays(self, scene_pos):
        """Erase from contour filling overlays (both contour lines and filled shapes)"""
        contour_filling = getattr(self, 'contour_filling', None)

        if self.overlay_pixmap_filled:
                print("contour222")
                self._erase_from_pixmap_overlay(
                    self.overlay_pixmap_filled,
                    self.overlay_pixmap_item_filled,
                    scene_pos
                )
        if hasattr(contour_filling, 'filled_points'):
                self._erase_filled_points(self.filled_points, scene_pos)

    def _erase_from_pixmap_overlay(self, overlay_pixmap, overlay_item, scene_pos):
        """Erase from a pixmap overlay by painting transparent pixels"""
        if not overlay_pixmap or not overlay_item:
            return

        # Create a painter to erase from the overlay
        painter = QPainter(overlay_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        # Create a transparent brush for erasing
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(Qt.PenStyle.NoPen)

        # Draw a circle to erase
        erase_x = int(scene_pos.x() - self.view.eraser_size)
        erase_y = int(scene_pos.y() - self.view.eraser_size)
        erase_diameter = int(self.view.eraser_size * 2)

        painter.drawEllipse(erase_x, erase_y, erase_diameter, erase_diameter)
        painter.end()

        # Update the graphics item
        overlay_item.setPixmap(overlay_pixmap)
        self.view.zoomable_graphics_view.update()

    def _erase_filled_points(self, filled_points, scene_pos):
        """Remove filled points from the data structure that are within eraser radius"""
        points_to_remove = []

        for point in filled_points:
            distance = self._calculate_distance(scene_pos, point)
            if distance <= self.view.eraser_size:
                points_to_remove.append(point)

        # Remove the points
        for point in points_to_remove:
            filled_points.remove(point)

    def _calculate_distance(self, pos1, pos2):
        """Calculate distance between two points"""
        if isinstance(pos1, QPointF) and isinstance(pos2, QPointF):
            dx = pos1.x() - pos2.x()
            dy = pos1.y() - pos2.y()
        else:
            # Handle mixed types
            x1, y1 = (pos1.x(), pos1.y()) if hasattr(pos1, 'x') else pos1
            x2, y2 = (pos2.x(), pos2.y()) if hasattr(pos2, 'x') else pos2
            dx = x1 - x2
            dy = y1 - y2

        return math.sqrt(dx * dx + dy * dy)

    def _path_intersects_circle(self, path, center):
        """Check if a QPainterPath intersects with a circle"""
        # Simple implementation: check if path bounding rect intersects eraser area
        path_rect = path.boundingRect()
        eraser_rect_x = center.x() - self.view.eraser_size
        eraser_rect_y = center.y() - self.view.eraser_size
        eraser_rect_width = self.view.eraser_size * 2
        eraser_rect_height = self.view.eraser_size * 2

        # Check if rectangles intersect
        return not (path_rect.right() < eraser_rect_x or
                    path_rect.left() > eraser_rect_x + eraser_rect_width or
                    path_rect.bottom() < eraser_rect_y or
                    path_rect.top() > eraser_rect_y + eraser_rect_height)
