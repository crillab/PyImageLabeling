
from PyImageLabeling.controller.Events import Events

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialog, QColorDialog
from PyQt6.QtGui import QPixmap, QImage

from PyImageLabeling.controller.settings.OpacitySetting import OpacitySetting
from PyImageLabeling.controller.settings.LabelSetting import LabelSetting
from PyImageLabeling.model.Utils import Utils

import os
import glob 

class LabelEvents(Events):
    def __init__(self):
        super().__init__()

        
    def new_label(self):
        self.all_events(self.new_label.__name__)
        label_setting = LabelSetting(self.view.zoomable_graphics_view)   
        
        if label_setting.exec():
            if self.model.name_already_exists(label_setting.name):
                    self.error_message("Error", f"The label name '{label_setting.name}' already exists!")
                    return

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

            if label_setting.importdata is True:
                self.model.save_labels(self.model.save_directory)
                self.model.load(self.model.save_directory)
                
            
    def select_label(self, label_id):
        self.all_events(label_id)
        
        # Uncheck all activation buttons except the selected label
        for id in self.view.buttons_label_bar_temporary:
            if id == label_id:
                self.view.buttons_label_bar_temporary[id]["activation"].setChecked(True)
            else:
                self.view.buttons_label_bar_temporary[id]["activation"].setChecked(False)
        
        self.move_image()
        # Active or deactivate the good labeling buttons 
        self.view.update_labeling_buttons(self.model.get_label_items()[label_id].get_labeling_mode())
        
        label_item = self.model.get_label_items()[label_id]
        if not label_item.get_visible():
            # Set the label as visible
            label_item.set_visible(True)
            
        # Call the model part to change the labeling overlay
        self.model.update_labeling_overlays(label_id)      
        #self.model.select_labeling_overlay(label_id) 

        # Ensure that the visibility button of this label is checked
        self.view.buttons_label_bar_temporary[label_id]["visibility"].setChecked(True)

    def color(self, label_id):
        self.all_events(self.color.__name__)
        label_item = self.model.get_label_items()[label_id]

        color = QColorDialog.getColor(label_item.get_color())
        if label_item.get_color() != color:
            label_item.set_color(color)
            self.model.update_color(label_id)
            print("label_id:", label_id)
            print("color:", color)
            print("color:", type(color))
            
            self.view.buttons_label_bar_temporary[label_id]["color"].setStyleSheet(Utils.color_to_stylesheet(color))

    def thickness(self, label_id, new_thickness):
        """Handle thickness change event for a label."""
        self.all_events(self.thickness.__name__)
        
        label_item = self.model.get_label_items()[label_id]
        label_item.set_thickness(new_thickness)
        self.model.update_thickness(new_thickness)
        
        # Save changes
        self.model.save_labels(self.model.save_directory)
        self.model.save_labels_geometric_shape(self.model.save_directory)

    def visibility(self, label_id):
        """Toggle visibility of a label and all its associated shapes."""
        self.all_events(self.visibility.__name__)

        current_label_id = self.model.get_current_label_item().get_label_id()
        if current_label_id == label_id:
            # Always keep current label visible
            self.view.buttons_label_bar_temporary[label_id]["visibility"].setChecked(True)
            return

        # Toggle visibility in the label model
        label_item = self.model.get_label_items()[label_id]
        new_visibility = not label_item.get_visible()
        label_item.set_visible(new_visibility)

        # Update overlays and scene
        image_item = self.model.get_current_image_item()
        if image_item is not None:
            image_item.update_scene()

        # Update geometric shapes in the scene
        for item in self.model.zoomable_graphics_view.scene.items():
            if hasattr(item, "label_id") and item.label_id == label_id:
                item.setVisible(new_visibility)

    def opacity(self):
        self.all_events(self.opacity.__name__)
        opacity_setting = OpacitySetting(self.view.zoomable_graphics_view)
        if opacity_setting.exec():
            self.model.set_opacity(opacity_setting.opacity/100) # To normalize


    def label_setting(self, label_id):
        self.all_events(self.label_setting.__name__)
        
        label_item = self.model.get_label_items()[label_id]
        #name = self.model.labeling_overlays[label_id].get_name()
        #labeling_mode = self.model.labeling_overlays[label_id].get_labeling_mode() 
        #color = self.model.labeling_overlays[label_id].get_color()   
        
        label_setting = LabelSetting(self.view.zoomable_graphics_view, 
                                     label_item.get_name(), 
                                     label_item.get_labeling_mode(), 
                                     label_item.get_color())

        if label_setting.exec():
            if label_item.get_name() != label_setting.name:
                if self.model.name_already_exists(label_setting.name):
                    self.error_message("Error", f"The label name '{label_setting.name}' already exists!")
                    return

                # Change the name in the model 
                label_item.set_name(label_setting.name)
                
                # Change the name in the view 
                self.view.buttons_label_bar_temporary[label_id]["activation"].setText(label_setting.name) 
                
            if label_item.get_labeling_mode() != label_setting.labeling_mode:
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
                    label_item.set_labeling_mode(label_setting.labeling_mode)

                    # Reset the labeling overlay 
                    for file_path in self.model.file_paths:
                        image_item = self.model.image_items[file_path]
                        if image_item is not None and label_id in image_item.labeling_overlays:
                            image_item.labeling_overlays[label_id].reset()
                            self.model.clear_all_rectangles(self.model.get_current_label_item().get_label_id())
                            self.model.clear_all_polygons(self.model.get_current_label_item().get_label_id())
                            self.model.clear_all_ellipses(self.model.get_current_label_item().get_label_id())

                    # Put the good labeling buttons according to the mode 
                    self.view.update_labeling_buttons(label_setting.labeling_mode)
                    self.move_image()
            if label_item.get_color() != label_setting.color:
                label_item.set_color(label_setting.color)
                self.model.update_color(label_id)
                self.view.buttons_label_bar_temporary[label_id]["color"].setStyleSheet(Utils.color_to_stylesheet(label_setting.color))

            if label_item.get_labeling_mode() == self.view.config["labeling_bar"]["geometric"]["name_view"]:
                print("caco")
                old_thickness = Utils.load_parameters()["geometric_shape"]["thickness"]
                new_thickness = label_setting.thickness_spin.value()
                data = Utils.load_parameters()
                data["geometric_shape"]["thickness"] = new_thickness
                Utils.save_parameters(data)
                self.model.update_thickness(new_thickness)
        

    def remove_label(self, label_id):
        self.all_events(self.remove_label.__name__)
        msgBox = QMessageBox(self.view.zoomable_graphics_view)
        msgBox.setWindowTitle("Remove Label")
        msgBox.setText("Are you sure you want to delete this label ?")
        msgBox.setInformativeText("All previous works done with this label will be erased on all images and in your save.")
        msgBox.setStandardButtons(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
        msgBox.setDefaultButton(QMessageBox.StandardButton.No)
        for button in msgBox.buttons():
            button.setObjectName("dialog")

        msgBox.setModal(True)
        result = msgBox.exec()
        if result == QMessageBox.StandardButton.Yes:
            self.default_path_save = Utils.load_parameters()["save"]["path"]
            if os.path.exists(self.default_path_save):
                pattern = os.path.join(self.default_path_save, f"*.{label_id}.png")
                png_files = glob.glob(pattern)
                for png_file in png_files:
                        os.remove(png_file)

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
                self.model.remove_contour()
                self.model.set_current_label_item(None)
            # Select another label if the deleted one was selected (this condition should never be true now)
            elif self.model.get_current_label_item() is not None and self.model.get_current_label_item().get_label_id() == label_id:
                first_id = list(self.model.get_label_items().keys())[0]
                self.select_label(first_id)
            
   






        
