
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyQt6.QtCore import Qt

from model.Core import Core

class ClearAll(Core):
    def __init__(self):
        super().__init__() 
    
    def clear_all(self):
        """Clear all drawings and overlays from the canvas"""
        
        # Clear all paint brush items (QGraphicsItems) from the scene
        scene = self.view.zoomable_graphics_view.scene
        items_to_remove = []
        
        for item in scene.items():
            if isinstance(item, (QGraphicsEllipseItem, QGraphicsPathItem)):
                items_to_remove.append(item)
        
        for item in items_to_remove:
            scene.removeItem(item)
        
        # Clear magic pen overlay
        if hasattr(self, 'overlay_pixmap') and self.overlay_pixmap:
            self.overlay_pixmap.fill(Qt.GlobalColor.transparent)
            if hasattr(self, 'overlay_pixmap_item') and self.overlay_pixmap_item:
                self.overlay_pixmap_item.setPixmap(self.overlay_pixmap)
        
        # Clear contour filling overlays
        if hasattr(self, 'overlay_pixmap_filled') and self.overlay_pixmap_filled:
            self.overlay_pixmap_filled.fill(Qt.GlobalColor.transparent)
            if hasattr(self, 'overlay_pixmap_item_filled') and self.overlay_pixmap_item_filled:
                self.overlay_pixmap_item_filled.setPixmap(self.overlay_pixmap_filled)
        
        # Clear filled points data
        if hasattr(self, 'filled_points') and self.filled_points:
            self.filled_points.clear()
        
        # Clear contour filling object's data
        contour_filling = getattr(self, 'contour_filling', None)
        if contour_filling and hasattr(contour_filling, 'filled_points'):
            contour_filling.filled_points.clear()
        
        # Update the view
        self.view.zoomable_graphics_view.update()