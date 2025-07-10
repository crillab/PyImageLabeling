

from PyImageLabeling.model.Core import Core
from PyQt6.QtCore import Qt

class LoadImage(Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def load_image(self, pixmap):
        self.zoomable_graphics_view.scene.clear()
        self.pixmap_item = self.zoomable_graphics_view.scene.addPixmap(pixmap)
        self.pixmap_item.setZValue(0)  # Base laye
        self.zoomable_graphics_view.setSceneRect(self.pixmap_item.boundingRect())
        #self.zoomable_graphics_view.centerOn(0,0)
        self.zoomable_graphics_view.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio);

        
        
        #self.zoomable_graphics_view.setSceneRect(self.pixmap_item.boundingRect())
        # Resize tthe 
        
        #self.zoomable_graphics_view.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        
        # Reset view
        #self.setSceneRect(self.pixmap_item.boundingRect())
        #
        #self.zoom_factor = 1.0
        
        # Reset transformations
        #self.resetTransform()

        #self.image_label.setBasePixmap(pixmap)
        #self.image_label.reset_view()
        #self.activate_move_mode(True)

    
    
