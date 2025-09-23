


from PyQt6.QtCore import Qt, QFileInfo
from PyQt6.QtWidgets import QFileDialog, QProgressDialog, QMessageBox, QLineEdit
from PyQt6.QtGui import QPixmap, QBitmap, QImage

from PyImageLabeling.model.Core import Core, KEYWORD_SAVE_LABEL
from PyImageLabeling.model.Utils import Utils


import os

        
class Files(Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def select_image(self, path_image):
        #remove all overlays#
        #self.clear_all()
        super().select_image(path_image)
        
    def save(self):
        print("save")
        if self.save_directory == "":
            # Open a directory        
            self.default_path_save = Utils.load_parameters()["save"]["path"]
            
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
            dialog.setOption(QFileDialog.Option.ReadOnly, False)  
            dialog.setDirectory(self.default_path_save)
            
            def check_selection(path):
                info = QFileInfo(path)
                if info.isFile():
                    self.default_path = info.absolutePath()
                    dialog.done(0)  
                    self.controller.error_message("Load Error", "You can not select a file, chose a folder !")
                    self.load()
                    
            dialog.currentChanged.connect(check_selection)
            dialog.setModal(True)
            if dialog.exec() == 0: return 
            #print("result:", result)
            #if dialog.exec():
            #print("default_path:", default_path)
            self.default_path_save = dialog.selectedFiles()[0]
            current_file_path = self.default_path_save
            
            if len(current_file_path) == 0: return

            data = Utils.load_parameters()
            data["save"]["path"] = current_file_path
            Utils.save_parameters(data)
            self.save_directory = current_file_path

        super().save()

    def save_copy(self):
        """Save a copy of the project to a different directory."""
        print("save_copy")
        
        # Get the default save path from parameters
        default_path_save_copy = Utils.load_parameters()["save"]["path"]
        
        # Open directory selection dialog
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
        dialog.setOption(QFileDialog.Option.ReadOnly, False)  
        dialog.setDirectory(default_path_save_copy)
        dialog.setWindowTitle("Select Directory to Save Copy")
        
        def check_selection(path):
            info = QFileInfo(path)
            if info.isFile():
                dialog.done(0)  
                self.controller.error_message("Save Copy Error", "You cannot select a file, choose a folder!")
                self.save_copy()  # Retry
                
        dialog.currentChanged.connect(check_selection)
        dialog.setModal(True)
        
        if dialog.exec() == 0: 
            return 
        
        # Get the selected directory
        selected_directories = dialog.selectedFiles()
        if len(selected_directories) == 0 or len(selected_directories[0]) == 0:
            return
        
        target_directory = selected_directories[0]
        
        # Call the parent class save_copy method with the target directory
        super().save_copy(target_directory)

    def load(self):
        print("load")
        self.default_path = Utils.load_parameters()["load"]["path"]
        
        # file_dialog = QFileDialog()
        # current_file_path = file_dialog.getExistingDirectory(
        #         parent=self.view, 
        #         caption="Open Folder", 
        #         directory=default_path)
        
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
        dialog.setOption(QFileDialog.Option.ReadOnly, False)  
        dialog.setDirectory(self.default_path)
        
        def check_selection(path):
            info = QFileInfo(path)
            if info.isFile():
                self.default_path = info.absolutePath()
                dialog.done(0)  
                self.controller.error_message("Load Error", "You can not select a file, chose a folder !")
                self.load()
                 
        dialog.currentChanged.connect(check_selection)
        dialog.setModal(True)

        if dialog.exec() == 0: return 
        #print("result:", result)
        #if dialog.exec():
        #print("default_path:", default_path)
        self.default_path = dialog.selectedFiles()[0]
        current_file_path = self.default_path
        
        if len(current_file_path) == 0: return
        current_file_path = current_file_path + os.sep
        data = Utils.load_parameters()
        data["load"]["path"] = os.path.dirname(current_file_path)
        Utils.save_parameters(data)

        # Update the model with the good images
        # The model variables is update in this method: file_paths and image_items
        print("current_file_path:", current_file_path)
        current_files = [current_file_path+os.sep+f for f in os.listdir(current_file_path)]
        current_files_to_add = []
        print("current_files:", current_files)
        labels_json = None
        labels_images = []
        for file in current_files:
            print("file:", file)
            if file in self.file_paths:
                continue
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                if KEYWORD_SAVE_LABEL in file:
                    # It is a label file  
                    labels_images.append(file)
                else:
                    # It is a image 
                    print("file2:", file)
                    self.file_paths.append(file)
                    self.image_items[file] = None
                    current_files_to_add.append(file)
            elif file.endswith("labels.json"):
                labels_json = file # Load it later 
        self.view.file_bar_add(current_files_to_add)

        # Activate previous and next buttons
        for button_name in self.view.buttons_file_bar:
            self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list if we have some images and no image selected
        if self.view.file_bar_list.count() > 0 and self.view.file_bar_list.currentRow() == -1:
            self.view.file_bar_list.setCurrentRow(0) 

        if (len(labels_images) != 0 and labels_json is None) or \
            (len(labels_images) == 0 and labels_json is not None):
            self.controller.error_message("Load Error", "The labeling image or the `labels.json` file is missing !")
            return 

        if len(labels_images) == 0 and labels_json is None:
            return

        if labels_json is not None and self.get_edited():
            msgBox = QMessageBox(self.view.zoomable_graphics_view)
            msgBox.setWindowTitle("Load")
            msgBox.setText("Are you sure you want to load the new labeling overview without save our previous works ?")
            msgBox.setInformativeText("All previous works not saved will be reset.")
            msgBox.setStandardButtons(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            msgBox.setDefaultButton(QMessageBox.StandardButton.No)
            msgBox.setModal(True)
            result = msgBox.exec()

            if result == QMessageBox.StandardButton.No:
                return
        
        # Reset all labeling overview in the model
        self.reset()
        self.labeling_overview_was_loaded.clear()
        self.labeling_overview_file_paths.clear()

        # Reset the view
        to_delete = []
        for label_id in self.view.container_label_bar_temporary:
            widget, separator = self.view.container_label_bar_temporary[label_id]
            
            widget.hide()
            self.view.label_bar_layout.removeWidget(widget)
            separator.hide()
            self.view.label_bar_layout.removeWidget(separator)
            
            # Clean up the view dictionaries
            to_delete.append(label_id)
            if label_id in self.view.buttons_label_bar_temporary:
                del self.view.buttons_label_bar_temporary[label_id]
        
        for label_id in to_delete:
            del self.view.container_label_bar_temporary[label_id]

        # Clear the labels in the model
        self.label_items.clear()

        # Reset the icon file 
        self.update_icon_file()

        # We load the overview labelings
        if labels_images is not None:
            for file in labels_images:
                self.load_labels_images(file)

        # Load the labels and initalize the first one
        if labels_json is not None:
            self.load_labels_json(labels_json)
            first_id = list(self.get_label_items().keys())[0]
            self.controller.select_label(first_id)

        # Now, we have to save in this directory :)
        self.save_directory = current_file_path

        
            
            


    
