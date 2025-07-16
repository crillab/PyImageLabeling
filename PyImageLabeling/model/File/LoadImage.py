

from PyImageLabeling.model.Core import Core
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap
import os

class LoadImage(Core):
    def __init__(self):
        super().__init__() 
        self.loaded_image_paths = []

    def set_view(self, view):
        super().set_view(view)
    
    def load_image(self, pixmap):
        self.zoomable_graphics_view.scene.clear()
        self.pixmap_item = self.zoomable_graphics_view.scene.addPixmap(pixmap)
        self.pixmap_item.setZValue(0)  # Base laye
        self.zoomable_graphics_view.setSceneRect(self.pixmap_item.boundingRect())
        #self.zoomable_graphics_view.centerOn(0,0)
        self.zoomable_graphics_view.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def init_load_image(self):

        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self.view, "Open Image", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_paths == "": return
        
        valid_images = []
        for file_path in file_paths:
            image = QPixmap(file_path)
            if not image.isNull() and file_path not in self.loaded_image_paths:
                valid_images.append(file_path)
                filename = os.path.basename(file_path)
                self.view.file_bar_list.addItem(self.view.add_file_to_list(filename, self.loaded_image_paths))
                self.loaded_image_paths.append(file_path)
            else:
                print(f"Warning: Could not load image {file_path}")
        
        if not valid_images:
            print("Load Images", "Could not load any of the selected images.")
            return
        
        # Load the first valid image
        first_image = QPixmap(valid_images[0])
        self.load_image(first_image)
        
        for button_name in self.view.buttons_file_bar:
            if 'previous' in button_name or 'next' in button_name:
                self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list
        if self.view.file_bar_list.count() > 0:
            self.view.file_bar_list.setCurrentRow(0) 
            self.view.select_image()

            # Check all possible button names for previous/next
            
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

    
    
