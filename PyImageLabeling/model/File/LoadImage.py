
class LoadImage():
    def __init__(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut

    def load_image(self, pixmap):
        self.zoomable_graphics_view.scene.clear()
        self.pixmap_item = self.zoomable_graphics_view.scene.addPixmap(pixmap)
        self.pixmap_item.setZValue(0)  # Base layer

        
        # Reset view
        #self.setSceneRect(self.pixmap_item.boundingRect())
        #self.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        #self.zoom_factor = 1.0
        
        # Reset transformations
        #self.resetTransform()

        #self.image_label.setBasePixmap(pixmap)
        #self.image_label.reset_view()
        #self.activate_move_mode(True)

    
    
