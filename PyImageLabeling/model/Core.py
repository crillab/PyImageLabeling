
from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap
import numpy

class Core():

    def __init__(self):
        self.labels = dict()
        self.current_label = None
        self.checked_button = None

        self.overlayers_pixmap = []
        self.image_pixmap = None

        self.image_pixmap_item = None
        self.overlayer_pixmap_item = None

    def initialyse_zoom_factor(self):
        viewport_width = self.view.zoomable_graphics_view.viewport().width()
        viewport_height = self.view.zoomable_graphics_view.viewport().height()
        diagonal_viewport = numpy.sqrt(viewport_width**2 + viewport_height**2)
        diagonal_pixmap = numpy.sqrt(self.qrect_size.width()**2 + self.qrect_size.height()**2)

        self.view.zoom_factor = diagonal_pixmap / diagonal_viewport
        if self.view.zoom_factor < self.view.min_zoom: self.view.min_zoom = self.view.zoom_factor
        if self.view.zoom_factor > self.view.max_zoom: self.view.max_zoom = self.view.zoom_factor
        self.view.initial_zoom_factor = self.view.zoom_factor


    ###
    # `new_overlay` is a QImage with QImage.Format.Format_Mono
    # This method add this image with the last image in the list `overlayers_pixmap`
    # and display the color of the label for the mask on the QZoomableGraphicView
    ###
    def update_overlay(self, new_overlay):
        
        if len(self.overlayers_pixmap) != 0:
            # Fusion of the `new_overlay` with `self.overlayers_pixmap[-1]`: the result is in `new_overlay`
            painter = QPainter(new_overlay)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            painter.drawImage(0, 0, self.overlayers_pixmap[-1])
            painter.end()
            
        # Add the new mask     
        self.overlayers_pixmap.append(new_overlay)
        
        # Invert the mask 
        inverted_new_overlay = QImage(new_overlay)
        painter = QPainter(inverted_new_overlay)
        painter.setCompositionMode(QPainter.CompositionMode.RasterOp_NotSource)
        painter.drawImage(0, 0, inverted_new_overlay)
        painter.end()

        # Create a overlay for the display 
        width, height = self.image_pixmap.width(), self.image_pixmap.height()
        new_overlay_display = QImage(width, height, QImage.Format.Format_ARGB32)
        current_label_color = self.labels[self.current_label]["color"]    
        new_overlay_display.fill(current_label_color)

        # Apply the (inverted) mask to the overlay 
        p = QPixmap(new_overlay_display)
        p.setMask(QBitmap(inverted_new_overlay))

        # Add or replace the pixmap of the scene of the zoomable_graphics_view
        if self.overlayer_pixmap_item is None:
            self.overlayer_pixmap_item = self.view.zoomable_graphics_view.scene.addPixmap(p)
            self.overlayer_pixmap_item.setZValue(1)  # Set Z-value to be above the base image
        else:
            self.overlayer_pixmap_item.setPixmap(p)

        # Update the scene
        self.view.zoomable_graphics_view.scene.update()
        self.view.zoomable_graphics_view.update()


    def set_view(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut

    def set_controller(self, controller):
        self.controller = controller
        
    def new_label(self, data_new_label):
        self.labels[data_new_label["name"]] = data_new_label
        self.set_current_label(data_new_label["name"])

    def set_current_label(self, name):
        self.current_label = name
        print("current_label:", self.current_label)
        
    

    