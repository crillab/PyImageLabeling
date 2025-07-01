
from PyImageLabeling.controller.Events import Events

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap, QImage


class FileEvents(Events):
    def __init__(self):
        super().__init__()

    def set_view(self, view):
        super().set_view(view)

    def set_model(self, model):
        super().set_model(model)
        
    def load_image(self):
        self.all_events(self.load_image.__name__)
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self.view, "Open Image", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path == "": return
        
        image = QPixmap(file_path)
        if image.isNull(): self.error_message("Load Image", "Could not load the image.")

        self.model.load_image(image)
            
        
    def save_image(self):
        self.all_events(self.save_image.__name__)
        print("save_image")

    def load_layer(self):
        self.all_events(self.load_layer.__name__)
        print("load_layer")

    def unload_layer(self):
        self.all_events(self.unload_layer.__name__)
        print("unload_layer")


        
