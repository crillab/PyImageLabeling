from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, Qt

class EraserTool:
    def __init__(self, overlay_manager, eraser_size=10):
        """
        overlay_manager: object that has `overlayers_pixmap` list and `update_overlay(new_overlay)` method
        eraser_size: radius of the eraser in pixels
        """
        self.overlay_manager = overlay_manager
        self.eraser_size = eraser_size
        self.last_pos = None

    def start_erase(self, scene_pos):
        self.last_pos = scene_pos
        self.erase_at(scene_pos)

    def move_erase(self, scene_pos):
        if self.last_pos is None:
            self.start_erase(scene_pos)
            return
        self.erase_line(self.last_pos, scene_pos)
        self.last_pos = scene_pos

    def end_erase(self):
        self.last_pos = None

    def erase_at(self, scene_pos):
        """Erase a single point from the top overlay"""
        if not self.overlay_manager.overlayers_pixmap:
            return

        overlay_image = self.overlay_manager.overlayers_pixmap[-1]

        painter = QPainter(overlay_image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(scene_pos, self.eraser_size, self.eraser_size)
        painter.end()

        self.overlay_manager.update_overlay(overlay_image)

    def erase_line(self, start_pos, end_pos):
        """Erase smoothly along a line between two points"""
        if not self.overlay_manager.overlayers_pixmap:
            return

        overlay_image = self.overlay_manager.overlayers_pixmap[-1]

        painter = QPainter(overlay_image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setPen(Qt.PenStyle.NoPen)

        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        distance = (dx**2 + dy**2)**0.5
        steps = max(1, int(distance / (self.eraser_size / 2)))

        for i in range(steps + 1):
            t = i / steps
            interp_x = start_pos.x() + dx * t
            interp_y = start_pos.y() + dy * t
            painter.drawEllipse(QPointF(interp_x, interp_y), self.eraser_size, self.eraser_size)

        painter.end()
        self.overlay_manager.update_overlay(overlay_image)
