
from  controller.Events import Events

from PyQt6.QtWidgets import QFileDialog, QDialog, QColorDialog
from PyQt6.QtGui import QPixmap, QImage

from PyImageLabeling.controller.settings.OpacitySetting import OpacitySetting
from PyImageLabeling.controller.settings.LabelSetting import LabelSetting
from PyImageLabeling.model.Utils import Utils

class LabelEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_label(self):
        self.all_events(self.new_label.__name__)
        label_setting = LabelSetting(self.view.zoomable_graphics_view)   
        if label_setting.exec():

            label_id = self.model.get_next_label_id() # Get a new id for this label
            
            self.view.builder.build_new_layer_label_bar(label_id, label_setting.name, label_setting.labeling_mode, label_setting.color)
            self.model.new_labeling_overlay(label_setting.name, label_setting.labeling_mode, label_setting.color)           
            self.view.update_labeling_buttons(label_setting.labeling_mode)
            
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

    def color(self, activation_name):
        self.all_events(self.color.__name__)
        label_name = activation_name.split("_")[-1] 
        labeling_overlay = self.model.labeling_overlays[label_name]
        color = QColorDialog.getColor(labeling_overlay.get_color())
        if labeling_overlay.get_color() != color:
            labeling_overlay.set_color(color)
            labeling_overlay.update_color()
            self.view.buttons_label_bar_temporary["color_"+label_name].setStyleSheet(Utils.color_to_stylesheet(color))
            self.model.labels[label_name]["color"] = color

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


    def label_setting(self, activation_name):
        self.all_events(self.label_setting.__name__)
        label_name = activation_name.split("_")[-1] 
        data_label = self.model.labels[label_name]
        
        label_setting = LabelSetting(self.view.zoomable_graphics_view, data_label["name"], data_label["labeling_mode"], data_label["color"])   
        if label_setting.exec():
            if data_label["name"] != label_setting.name:
                # Change the name in the model 
                self.model.change_name(label_name, label_setting.name)

                # Change the name in the buttons bar dictionnary
                keys_to_remove = []
                for key in self.view.buttons_label_bar_temporary:
                    if key.endswith(label_name):
                        new_key = key.replace(label_name, label_setting.name)
                        self.view.buttons_label_bar_temporary[key] = self.view.buttons_label_bar_temporary[key]
                 = self.view.buttons_label_bar_temporary["activation_"+label_setting.name]

        print("label_setting")
    
    def unload_label(self, activation_name):
        self.all_events(self.unload_label.__name__)

        print("unload_label")

    






        
