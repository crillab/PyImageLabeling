
from PyImageLabeling.controller.Events import Events

from PyQt6.QtWidgets import QFileDialog, QDialog
from PyQt6.QtGui import QPixmap, QImage

class LayerEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_layer(self):
        self.all_events(self.new_layer.__name__)
        
        self.view.build_label_setting_form()

        self.model.new_layer()
        #self.view.build_new_layer_bottom_bar()
        
        print("load_layer")
        
    def load_layers(self):
        self.all_events(self.load_layers.__name__)

        print("load_layers")

    def save_layers(self):
        self.all_events(self.save_layers.__name__)
        print("save_layers")





        
