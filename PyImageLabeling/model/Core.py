
from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap

class Core():

    def __init__(self):
        self.labels = dict()
        self.current_label = None
        self.checked_button = None

        self.overlayers_pixmap = []
        self.image_pixmap = None

        self.image_pixmap_item = None
        self.overlayer_pixmap_item = None

    def update_overlay(self, new_overlay):
        if len(self.overlayers_pixmap) != 0:
            painter = QPainter(new_overlay)
            painter.setCompositionMode(QPainter.CompositionMode.RasterOp_NotSource)
            #painter.setCompositionMode(QPainter.CompositionMode.RasterOp_NotSourceAndDestination)
            painter.drawPixmap(0, 0, QBitmap(new_overlay))

            painter.end()
            
        self.overlayers_pixmap.append(new_overlay)

        # If a overlayer_item already exists, we delete it 
        if self.overlayer_pixmap_item is None:
            self.overlayer_pixmap_item = self.view.zoomable_graphics_view.scene.addPixmap(QPixmap(new_overlay))
            self.overlayer_pixmap_item.setZValue(1)  # Set Z-value to be above the base image
        else:
            self.overlayer_pixmap_item.setPixmap(QPixmap(new_overlay))

        # Update the scene
        self.view.zoomable_graphics_view.scene.update()
        self.view.zoomable_graphics_view.update()


    def set_view(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut
    
    def new_label(self, data_new_label):
        self.labels[data_new_label["name"]] = data_new_label
        self.set_current_label(data_new_label["name"])

    def set_current_label(self, name):
        self.current_label = name
        print("current_label:", self.current_label)
        
    

    