
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
        self.model.new_labeling_overlay(data_new_label)   


    def load_labels(self):
        self.all_events(self.load_labels.__name__)

        print("load_layers")

    def save_labels(self):
        self.all_events(self.save_labels.__name__)
        print("save_layers")

    def select_label(self, activation_name):
        self.all_events(activation_name)
        
        label_name = activation_name.split("_")[-1] #Get the label name
        self.desactivate_buttons_label_bar(activation_name) # Deactivate the other labels
        self.view.update_labeling_buttons(self.model.labels[self.model.current_label]["labeling_mode"]) # Active or deactivate the good labeling buttons 
        self.model.select_labeling_overlay(label_name) # Call the model part to change the labeling overlay 

        print("select_label")

    def color(self):
        self.all_events(self.color.__name__)

        print("color")

    def visibility(self):
        self.all_events(self.visibility.__name__)
        if self.view.buttons_label_bar_temporary[self.visibility.__name__].isChecked() is True:
            self.model.visibility(True)
        else:
            self.model.visibility(False)
            
    def opacity(self):
        self.all_events(self.opacity.__name__)
        print("opacity")


    def label_setting(self):
        self.all_events(self.label_setting.__name__)

        print("label_setting")
    
    def unload_label(self):
        self.all_events(self.unload_label.__name__)

        print("unload_label")

    






        
