
from PyImageLabeling.controller.Events import Events

from PyQt6.QtWidgets import QFileDialog, QLabel
from PyQt6.QtGui import QPixmap, QImage

import os

class FileEvents(Events):
    def __init__(self):
        super().__init__()
        
    def set_view(self, view):
        super().set_view(view)

    def set_model(self, model):
        super().set_model(model)
        
    def load_images(self):
        self.all_events(self.load_images.__name__)
        self.model.init_load_image()
        for button_names in self.view.buttons_image_bar:
            self.view.buttons_image_bar[button_names].setEnabled(True)
        print("load_images")

    def select_image(self, item):
        item_widget = self.view.file_bar_list.itemWidget(item)
        if item_widget:
            file_label = item_widget.findChild(QLabel)
            if file_label:
                filename = file_label.text()
                matching_path = None
                for path in self.model.loaded_image_paths:
                    if os.path.basename(path) == filename:
                        matching_path = path
                        break
                if matching_path:
                    image = QPixmap(matching_path)
                    if not image.isNull():
                        self.model.load_image(image)
                        self.view.file_bar_list.setCurrentItem(item)
                        print(f"Loaded image: {filename}")
                    else:
                        print(f"Error: Could not load image {filename}")
                else:
                    print(f"Error: Could not find path for {filename}")
    
    def next_image(self):
        self.all_events(self.next_image.__name__)
        self.model.next_image()

    def previous_image(self):
        self.all_events(self.previous_image.__name__)
        self.model.previous_image()
