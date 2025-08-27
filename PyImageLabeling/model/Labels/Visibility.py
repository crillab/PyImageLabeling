from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Core import Core

class Visibility(Core):
    def __init__(self):
        super().__init__()

    def visibility(self, visible=False):
        """Set the visibility of all drawings and overlays on the canvas"""

        # Set visibility of all paint brush items (QGraphicsItems) in the scene
        scene = self.view.zoomable_graphics_view.scene

        for item in scene.items():
            if isinstance(item, (QGraphicsEllipseItem, QGraphicsPathItem)):
                item.setVisible(visible)

        # Clear magic pen overlay by making it transparent
        if hasattr(self, 'overlay_pixmap') and self.overlay_pixmap:
            self.overlay_pixmap.fill(Qt.GlobalColor.transparent)
            if hasattr(self, 'overlay_pixmap_item') and self.overlay_pixmap_item:
                self.overlay_pixmap_item.setVisible(visible)

        # Clear contour filling overlays by making them transparent
        if hasattr(self, 'overlay_pixmap_filled') and self.overlay_pixmap_filled:
            self.overlay_pixmap_filled.fill(Qt.GlobalColor.transparent)
            if hasattr(self, 'overlay_pixmap_item_filled') and self.overlay_pixmap_item_filled:
                self.overlay_pixmap_item_filled.setVisible(visible)

        # Clear filled points data
        if hasattr(self, 'filled_points') and self.filled_points:
            self.filled_points.clear()

        # Clear contour filling object's data
        contour_filling = getattr(self, 'contour_filling', None)
        if contour_filling and hasattr(contour_filling, 'filled_points'):
            contour_filling.filled_points.clear()

        # Update the view
        self.view.zoomable_graphics_view.update()
