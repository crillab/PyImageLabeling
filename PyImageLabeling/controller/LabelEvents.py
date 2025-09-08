
from  controller.Events import Events

from PyQt6.QtWidgets import QFileDialog, QDialog, QColorDialog
from PyQt6.QtGui import QPixmap, QImage

from PyImageLabeling.controller.settings.OpacitySetting import OpacitySetting

from PyImageLabeling.model.Utils import Utils
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
        
        self.view.buttons_label_bar_temporary["visibility_"+label_name].setChecked(True)
        
        print("select_label")

    def color(self, activation_name):
        self.all_events(self.color.__name__)
        print("dd:", activation_name)
        label_name = activation_name.split("_")[-1] 
        print("label _name:", label_name)
        labeling_overlay = self.model.labeling_overlays[label_name]
        color = QColorDialog.getColor(labeling_overlay.get_color())
        labeling_overlay.set_color(color)
        labeling_overlay.update_color()
        self.view.buttons_label_bar_temporary["color_"+label_name].setStyleSheet(Utils.color_to_stylesheet(color))

        print("color:", color)

    def visibility(self, activation_name):
        self.all_events(self.visibility.__name__)
        label_name = activation_name.split("_")[-1] #Get the label name
        if self.model.current_label == label_name:
            # Do nothing 
            self.view.buttons_label_bar_temporary["visibility_"+label_name].setChecked(True)
        else:
            self.model.visibility(label_name)
        
    def opacity(self):
        self.all_events(self.opacity.__name__)
        opacity_setting = OpacitySetting(self.view.zoomable_graphics_view)
        if opacity_setting.exec():
            self.model.set_opacity(opacity_setting.opacity/100) # To normalize

        print("opacity")


    def label_setting(self, activation_name):
        self.all_events(self.label_setting.__name__)

        print("label_setting")
    
    def unload_label(self, activation_name):
        self.all_events(self.unload_label.__name__)

        print("unload_label")

    






        
