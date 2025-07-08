
from  controller.Events import Events

from PyQt6.QtWidgets import QFileDialog, QDialog
from PyQt6.QtGui import QPixmap, QImage

class LabelEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_label(self):
        self.all_events(self.new_label.__name__)
        self.view.build_label_setting_form()

        print("new_label")

    def new_label_end(self, data_new_label):  
        self.model.new_label(data_new_label)      
        print("new_label_end:", data_new_label)


    def load_labels(self):
        self.all_events(self.load_labels.__name__)

        print("load_layers")

    def save_labels(self):
        self.all_events(self.save_labels.__name__)
        print("save_layers")

    def activation(self, activation_name):
        label_name = activation_name.split("_")[-1]
        #if self.model.current_label == label_name:
        #    self.view.activate_buttons(activation_name, [self.view.buttons_label_bar_temporary])
        #else:
        self.desactivate_buttons_label_bar(activation_name)
        print("activation_name:", activation_name)
        self.all_events(activation_name)
        self.model.set_current_label(label_name)

        print("activation")

    def color(self):
        self.all_events(self.color.__name__)

        print("color")

    def visibility(self):
        self.all_events(self.visibility.__name__)

        print("visibility")
    
    def opacity(self):
        self.all_events(self.opacity.__name__)
        print("opacity")


    def label_setting(self):
        self.all_events(self.label_setting.__name__)

        print("label_setting")
    
    def unload_label(self):
        self.all_events(self.unload_label.__name__)

        print("unload_label")

    






        
