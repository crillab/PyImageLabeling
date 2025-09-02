
from view.Builder import Builder
from model.Utils import Utils

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout,  QListWidgetItem, QLabel,  QPushButton, QGraphicsItem, QGraphicsEllipseItem
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF, QDateTime

import os

class View(QMainWindow):
    def __init__(self, controller, config):
        
        super().__init__()
        # Parameters
        self.controller = controller
        self.config = config
        
        #Components of the view 
        self.buttons_labeling_bar = dict()
        self.buttons_label_bar_permanent = dict()
        self.buttons_label_bar_temporary = dict()
        self.buttons_image_bar = dict()
        self.buttons_file_bar = dict()
        self.buttons_apply_cancel_bar = dict()
        
        
        self.zoomable_graphics_view = None

        # Set the main properties of the view
        self.initialize()

        # Build the components of the view
        self.builder = Builder(self)
        self.builder.build()


        self.controller.set_view(self) 
        
        # Display
        self.show()

    # Here we are sure that clicked is checkable
    def desactivate_buttons(self, clicked, list_buttons_bars):
        for buttons_bar in list_buttons_bars:
            for button in buttons_bar.keys():
                # The button have not to be the same that clicked
                # The button have to be checked 
                # The clicked button have to be checkable 
                #print("button:",button)
                if button != clicked and buttons_bar[button].isChecked() is True:
                    buttons_bar[button].setChecked(False)
                if button == clicked:
                    buttons_bar[button].setChecked(True)

   

    def update_labeling_buttons(self, labeling_mode):
        print("labeling_mode", labeling_mode)
        category_key_selected = None
        for category_key in self.config["labeling_bar"].keys():
            category_name = self.config["labeling_bar"][category_key]["name_view"]
            if category_name == labeling_mode:
                category_key_selected = category_key
        if category_key_selected is None:
            raise ValueError("Bad category_key in the dictionnary `self.config[labeling_bar]` for " + str(labeling_mode)+ ".")

        #print("ess:", self.buttons_labeling_bar)
        #print("Labeling Type:", category_key_selected)

        for button_key in self.buttons_labeling_bar.keys():
            self.buttons_labeling_bar[button_key].setEnabled(False)

        for config_buttons in self.config["labeling_bar"][category_key_selected]["buttons"]:
            name = config_buttons["name"]
            self.buttons_labeling_bar[name].setEnabled(True)
            if name+"_setting" in self.buttons_labeling_bar.keys():
                self.buttons_labeling_bar[name+"_setting"].setEnabled(True)
                
        for config_buttons in self.config["labeling_bar"]["edit"]["buttons"]:
            name = config_buttons["name"]
            self.buttons_labeling_bar[name].setEnabled(True)
            if name+"_setting" in self.buttons_labeling_bar.keys():
                self.buttons_labeling_bar[name+"_setting"].setEnabled(True)

        # exit(0)
        # buttons = self.buttons_labeling_bar
        # pixel_tools = ["contour_filling", "paintbrush", "magic_pen"]
        # geometric_tools = ["ellipse", "rectangle", "polygon"]
        # for button in buttons.items():
        #     if labeling_mode == "Geometric":
        #         for button in geometric_tools:
        #             self.buttons_labeling_bar[button].setEnabled(True)
        #         for button in pixel_tools:
        #             self.buttons_labeling_bar[button].setEnabled(False)
        #     elif labeling_mode == "Pixel":
        #         for button in pixel_tools:
        #             self.buttons_labeling_bar[button].setEnabled(True)
        #         for button in geometric_tools:
        #             self.buttons_labeling_bar[button].setEnabled(False)

    def add_file_to_list(self, filename, loaded_image_paths):
        # Create list item
        item = QListWidgetItem()
        self.file_bar_list.addItem(item)
        
        # Create custom widget for the item
        item_widget = QWidget()
        item_widget.setObjectName("file_item")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 2, 5, 2)
        
        # File name label
        file_label = QLabel(filename)
        file_label.setObjectName("label_files")
        file_label.setToolTip(filename)  # Full filename as tooltip
        
        # Remove button
        remove_button = QPushButton("×")
        remove_button.setToolTip("Remove file")
        remove_button.setObjectName("remove_image_button")
        
        # Connect remove button to removal function
        remove_button.clicked.connect(lambda: self.remove_file_from_list(item, filename, loaded_image_paths))
 
        item_layout.addWidget(file_label)
        item_layout.addWidget(remove_button)
        
        self.file_bar_list.setItemWidget(item, item_widget)
    
    def remove_file_from_list(self, item, filename, loaded_image_paths):
        # Get the row of the item
        for path in loaded_image_paths:
            if filename in path:
                loaded_image_paths.remove(path)
        row = self.file_bar_list.row(item)
        if row >= 0:
            # Remove the item from the list
            self.file_bar_list.takeItem(row)
        if len(loaded_image_paths) == 0:
            for button_name in self.buttons_file_bar:
                if 'previous' in button_name or 'next' in button_name:
                    self.buttons_file_bar[button_name].setEnabled(False)
            for button_names in self.buttons_image_bar:
                self.buttons_image_bar[button_names].setEnabled(False)
            self.zoomable_graphics_view.scene.clear()
            self.pixmap_item = None
            self.zoomable_graphics_view.setSceneRect(0, 0, 0, 0)
            self.zoomable_graphics_view.resetTransform()

    def select_image(self):
        """Handle selection change to update styling"""
        for i in range(self.file_bar_list.count()):
            item = self.file_bar_list.item(i)
            item_widget = self.file_bar_list.itemWidget(item)
            
            if item_widget:
                if item.isSelected():
                    # Apply selected style
                    item_widget.setObjectName("selected_file_item")
                    self.controller.select_image(item)
                else:
                    # Apply normal style
                    item_widget.setObjectName("file_item")
                
                # Force style update
                item_widget.style().unpolish(item_widget)
                item_widget.style().polish(item_widget)

    

    def initialize(self):
        self.setWindowTitle("PyImageLabeling")
        self.label_properties_dialogs = []
        # Get screen information
        self.screen = QApplication.primaryScreen()

        self.screen_geometry = self.screen.availableGeometry()
        
        self.screen_width = self.screen_geometry.width()
        self.screen_height = self.screen_geometry.height()
        
        # Calculate dynamic window size based on screen dimensions
        self.window_width = int(self.screen_width * 0.80)  # Use 85% of screen width
        self.window_height = int(self.screen_height * 0.80)  # Use 85% of screen height
        
        self.setWindowIcon(QIcon(Utils.get_icon_path("maia_icon")))
        self.setStyleSheet(Utils.get_style_css())
        
        self.resize(self.window_width, self.window_height)
        

    def build_label_setting_form(self): self.builder.build_label_setting_form()
    def build_new_layer_label_bar(self): self.builder.build_new_layer_label_bar()

        
   