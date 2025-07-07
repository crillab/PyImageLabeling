
from  controller.Events import Events

from PyQt6.QtWidgets import QFileDialog, QDialog
from PyQt6.QtGui import QPixmap, QImage

class LayerEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_label(self):
        self.all_events(self.new_label.__name__)
        
        self.view.build_label_setting_form()

        self.model.new_layer()
        #self.view.build_new_layer_bottom_bar()
        
        print("load_layer")
        
    def load_labels(self):
        self.all_events(self.load_labels.__name__)

        print("load_layers")

    def save_labels(self):
        self.all_events(self.save_labels.__name__)
        print("save_layers")

    def activation(self, activation_name):
        layer_id = int(activation_name.split('_')[1])
        self.all_events(f"activation_{layer_id}")

        print("activation")

    def color(self):
        self.all_events(self.color.__name__)

        print("color")

    def visibility(self):
        self.all_events(self.visibility.__name__)

        print("visibility")

    def label_setting(self):
        self.all_events(self.label_setting.__name__)

        print("label_setting")
    
    def unload_label(self):
        self.all_events(self.unload_label.__name__)

        print("unload_label")

    






        
