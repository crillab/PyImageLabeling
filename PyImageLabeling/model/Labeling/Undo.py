from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap
from model.Core import Core

class Undo(Core):
    def __init__(self):
        super().__init__() 
    
    def undo(self):
        if not self.overlayers_pixmap:
            print("No overlays to undo")
            return False
        
        # Remove the last overlay
        self.overlayers_pixmap.pop()
        
        # Update the display based on remaining overlays
        if self.overlayers_pixmap:
            # There are still overlays remaining, display the last one
            self._display_current_overlay()
        else:
            # No overlays left, hide the overlay display
            self._hide_overlay_display()
        
        return True
    
    def _display_current_overlay(self):
        """Display the current top overlay with the current label's color."""
        if not self.overlayers_pixmap or not self.current_label:
            return
        
        current_overlay = self.overlayers_pixmap[-1].copy()
        
        self.overlayers_pixmap.pop()
        
        self.update_overlay(current_overlay)
    
    def _hide_overlay_display(self):
        if self.overlayer_pixmap_item is not None:
            self.view.zoomable_graphics_view.scene.removeItem(self.overlayer_pixmap_item)
            self.overlayer_pixmap_item = None
        
        # Update the scene
        self.view.zoomable_graphics_view.scene.update()
        self.view.zoomable_graphics_view.update()
    
    def can_undo(self):
        return len(self.overlayers_pixmap) > 0
    
    def get_overlay_count(self):
        return len(self.overlayers_pixmap)