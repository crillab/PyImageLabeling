from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap
from PyImageLabeling.model.Core import Core

class ClearAll(Core):
    def __init__(self):
        super().__init__()

    def clear_all(self):
        if not self.overlayers_pixmap:
            print("No overlays to clear")
            return False
    
        # Clear the entire overlay list
        self.overlayers_pixmap.clear()

        # Hide overlay display since none are left
        self._hide_overlay_display()

        return True

    def _hide_overlay_display(self):
        """Remove overlay pixmap item from the scene and update the view."""
        if self.overlayer_pixmap_item is not None:
            self.view.zoomable_graphics_view.scene.removeItem(self.overlayer_pixmap_item)
            self.overlayer_pixmap_item = None

        # Refresh the scene
        self.view.zoomable_graphics_view.scene.update()
        self.view.zoomable_graphics_view.update()

