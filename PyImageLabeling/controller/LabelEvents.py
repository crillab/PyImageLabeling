
from  controller.Events import Events

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialog, QColorDialog
from PyQt6.QtGui import QPixmap, QImage

from controller.settings.OpacitySetting import OpacitySetting
from controller.settings.LabelSetting import LabelSetting
from model.Utils import Utils

class LabelEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_label(self):
        self.all_events(self.new_label.__name__)
        label_setting = LabelSetting(self.view.zoomable_graphics_view)   
        
        if label_setting.exec():
            # Uncheck all activation buttons
            for label_id in self.view.buttons_label_bar_temporary:
                self.view.buttons_label_bar_temporary[label_id]["activation"].setChecked(False)

            # Create a new label
            label = self.model.new_label(label_setting.name, label_setting.labeling_mode, label_setting.color) 

            # Display the new label bar 
            self.view.builder.build_new_layer_label_bar(label.get_label_id(), label_setting.name, label_setting.labeling_mode, label_setting.color)
            
            # Update the model with the new labal
            self.model.update_labeling_overlays(label.get_label_id())        
            
            # Put the good labeling buttons according to the mode 
            self.view.update_labeling_buttons(label_setting.labeling_mode)
            
    def select_label(self, label_id):
        self.all_events(label_id)
        
        # Uncheck all activation buttons except the selected label
        for id in self.view.buttons_label_bar_temporary:
            if id == label_id:
                self.view.buttons_label_bar_temporary[id]["activation"].setChecked(True)
            else:
                self.view.buttons_label_bar_temporary[id]["activation"].setChecked(False)
        

        # Active or deactivate the good labeling buttons 
        self.view.update_labeling_buttons(self.model.get_label_items()[label_id].get_labeling_mode())
        
        label_item = self.model.get_label_items()[label_id]
        if not label_item.get_visible():
            # Set the label as visible
            label_item.set_visible(True)
            
            # Apply visibility to all loaded images
            image_items = self.model.get_image_items()
            for file_path, image_item in image_items.items():
                if image_item is not None and label_id in image_item.labeling_overlays:
                    overlay = image_item.labeling_overlays[label_id]
                    if overlay.is_displayed_in_scene:
                        # Only change if currently not visible
                        if not overlay.labeling_overlay_item.isVisible():
                            overlay.change_visible()

        # Call the model part to change the labeling overlay 
        self.model.update_labeling_overlays(label_id)      
        #self.model.select_labeling_overlay(label_id) 

        # Ensure that the visibility button of this label is checked
        self.view.buttons_label_bar_temporary[label_id]["visibility"].setChecked(True)

    def color(self, label_id):
        self.all_events(self.color.__name__)
        labeling_overlay = self.model.labeling_overlays[label_id]
        color = QColorDialog.getColor(labeling_overlay.get_color())
        if labeling_overlay.get_color() != color:
            labeling_overlay.set_color(color)
            labeling_overlay.update_color()
            self.view.buttons_label_bar_temporary[label_id]["color"].setStyleSheet(Utils.color_to_stylesheet(color))
            
    def visibility(self, label_id):
        self.all_events(self.visibility.__name__)
        
        if self.model.get_current_label_item().get_label_id() == label_id:
            # Do nothing 
            self.view.buttons_label_bar_temporary[label_id]["visibility"].setChecked(True)
        else:
            # Get the label visibility state
            label_item = self.model.get_label_items()[label_id]
            new_visibility = not label_item.get_visible() 
            label_item.set_visible(new_visibility)
            
            # Apply to all loaded images
            image_items = self.model.get_image_items()
            for file_path, image_item in image_items.items():
                if image_item is not None and label_id in image_item.labeling_overlays:
                    overlay = image_item.labeling_overlays[label_id]
                    if overlay.is_displayed_in_scene:
                        overlay.set_visible(new_visibility)
        
    def opacity(self):
        self.all_events(self.opacity.__name__)
        opacity_setting = OpacitySetting(self.view.zoomable_graphics_view)
        if opacity_setting.exec():
            self.model.set_opacity(opacity_setting.opacity/100) # To normalize


    def label_setting(self, label_id):
        self.all_events(self.label_setting.__name__)
        
        name = self.model.labeling_overlays[label_id].get_name()
        labeling_mode = self.model.labeling_overlays[label_id].get_labeling_mode() 
        color = self.model.labeling_overlays[label_id].get_color()   
        
        label_setting = LabelSetting(self.view.zoomable_graphics_view, name, labeling_mode, color)

        if label_setting.exec():
            if name != label_setting.name:
                if self.model.name_already_in_labels(label_setting.name) is True:
                    self.error_message("Error", "This label name already exists !")
                    return

                # Change the name in the model 
                self.model.labeling_overlays[label_id].set_name(label_setting.name)

                # Change the name in the view 
                self.view.buttons_label_bar_temporary[label_id]["activation"].setText(label_setting.name) 
                
            if labeling_mode != label_setting.labeling_mode:
                msgBox = QMessageBox(self.view.zoomable_graphics_view)
                msgBox.setWindowTitle("Labeling Mode")
                msgBox.setText("Are you sure you want to change the labeling mode ?")
                msgBox.setInformativeText("All previous works done with this label will be erased.")
                msgBox.setStandardButtons(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
                msgBox.setDefaultButton(QMessageBox.StandardButton.No)
                msgBox.setModal(True)
                result = msgBox.exec()
                if result == QMessageBox.StandardButton.Yes:
                    # Change in the model 
                    self.model.labeling_overlays[label_id].set_labeling_mode(label_setting.labeling_mode)

                    # Reset the labeling overlay 
                    self.model.labeling_overlays[label_id].reset()

                    # Put the good labeling buttons according to the mode 
                    self.view.update_labeling_buttons(label_setting.labeling_mode)
            
            if color != label_setting.color:
                self.model.labeling_overlays[label_id].set_color(label_setting.color)
                self.model.labeling_overlays[label_id].update_color()
                self.view.buttons_label_bar_temporary[label_id]["color"].setStyleSheet(Utils.color_to_stylesheet(label_setting.color))
            

    def remove_label(self, label_id):
        self.all_events(self.remove_label.__name__)
        msgBox = QMessageBox(self.view.zoomable_graphics_view)
        msgBox.setWindowTitle("Remove Label")
        msgBox.setText("Are you sure you want to delete this label ?")
        msgBox.setInformativeText("All previous works done with this label will be erased.")
        msgBox.setStandardButtons(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
        msgBox.setDefaultButton(QMessageBox.StandardButton.No)
        for button in msgBox.buttons():
            button.setObjectName("dialog")

        msgBox.setModal(True)
        result = msgBox.exec()
        if result == QMessageBox.StandardButton.Yes:
            # Remove from all images (replace the old single overlay removal)
            image_items = self.model.get_image_items()
            for file_path, image_item in image_items.items():
                if image_item is not None and label_id in image_item.labeling_overlays:
                    image_item.labeling_overlays[label_id].remove()
                    del image_item.labeling_overlays[label_id]

            # Remove from the model's label_items
            if label_id in self.model.get_label_items():
                del self.model.get_label_items()[label_id]

            # Remove from the view
            if label_id in self.view.container_label_bar_temporary:
                widget, separator = self.view.container_label_bar_temporary[label_id]
                
                widget.hide()
                self.view.label_bar_layout.removeWidget(widget)
                separator.hide()
                self.view.label_bar_layout.removeWidget(separator)
                
                # Clean up the view dictionaries
                del self.view.container_label_bar_temporary[label_id]
                if label_id in self.view.buttons_label_bar_temporary:
                    del self.view.buttons_label_bar_temporary[label_id]

            # Check if there are no more labels
            if len(self.model.get_label_items()) == 0:
                for button_key in self.view.buttons_labeling_bar.keys():
                    self.view.buttons_labeling_bar[button_key].setEnabled(False)
                self.move_image()  # To deactivate the last used tool, we active the move button :)  
                if hasattr(self.model, 'remove_contour'):
                    self.model.remove_contour()
            # Select another label if the deleted one was selected (this condition should never be true now)
            elif self.model.get_current_label_item() is not None and self.model.get_current_label_item().get_label_id() == label_id:
                first_id = list(self.model.get_label_items().keys())[0]
                self.select_label(first_id)
            
    def load_labels(self):
        self.all_events(self.load_labels.__name__)
        print("load_layers")

    def save_labels(self):
        self.all_events(self.save_labels.__name__)
        print("save_layers")






        
