
from PyImageLabeling.controller.Events import Events

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap, QImage


class LayerEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_layer(self):
        self.all_events(self.new_layer.__name__)
        
        self.model.new_layer()
        self.view.new_layer()
        print("load_layer")
        
    def load_layer(self):
        self.all_events(self.load_layer.__name__)

        print("load_layer")

        
