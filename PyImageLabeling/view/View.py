
from PyImageLabeling.view.Builder import Builder
from PyImageLabeling.model.Utils import Utils

from PyQt6.QtWidgets import QListWidget, QProgressDialog, QApplication, QMainWindow, QWidget, QHBoxLayout,  QListWidgetItem, QLabel,  QPushButton, QGraphicsItem, QGraphicsEllipseItem
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF, QDateTime
from functools import partial
import os
import time

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
        
        self.container_label_bar_temporary = dict()
        
        self.zoomable_graphics_view = None

        self.file_bar_layout = None

        # Set the main properties of the view
        self.initialize()

        # Build the components of the view
        self.builder = Builder(self)
        self.builder.build()

        self.icon_asterisk_green = QPixmap(Utils.get_icon_path("asterisk-green"))
        self.icon_asterisk_green = self.icon_asterisk_green.scaled(QSize(*self.config["window_size"]["icon_save_marker"]), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
        
        self.icon_asterisk_red = QPixmap(Utils.get_icon_path("asterisk-red"))
        self.icon_asterisk_red = self.icon_asterisk_red.scaled(QSize(*self.config["window_size"]["icon_save_marker"]), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
        
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

    

    def file_bar_add(self, current_file_paths):
        
        item_widgets = []
        for file in current_file_paths:
            if file in self.controller.model.file_paths:
                continue
            self.controller.model.file_paths.append(file)
            self.controller.model.image_items[file] = None

            filename = os.path.basename(file)

            # Create list item
            item = QListWidgetItem()
            item.file_path = file
            item.filename = filename

            self.file_bar_list.addItem(item)
            
            # Create custom widget for the item
            item_widget = QWidget()
            item_widget.setObjectName("file_item")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)

            # The save marker
            icon_button = QLabel()
            icon_button.setPixmap(self.icon_asterisk_green)
            icon_button.setObjectName("save_marker")
            self.controller.model.icon_button_files[file] = icon_button
            
            # File name label
            file_label = QLabel(filename)
            file_label.setObjectName("label_files")
            file_label.setToolTip(filename)  # Full filename as tooltip
            
            # Remove button
            remove_button = QPushButton("×")
            remove_button.setToolTip("Remove file")
            remove_button.setObjectName("remove_image_button")
            
            # Connect remove button to removal function
            remove_button.clicked.connect(partial(self.file_bar_remove, item, self.controller.model.file_paths, self.controller.model.image_items))

            item_layout.addWidget(icon_button)
            item_layout.addWidget(file_label)
            item_layout.addWidget(remove_button)
            item_widgets.append((item, item_widget))
            
        for item, item_widget in item_widgets:
            self.file_bar_list.setItemWidget(item, item_widget)
            
        
    def file_bar_remove(self, item, loaded_image_paths, image_items):
        # Get the row of the item
        for path in loaded_image_paths:
            if item.filename in path:
                loaded_image_paths.remove(path)
                del image_items[path]
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
            #self.pixmap_item = None
            #self.zoomable_graphics_view.setSceneRect(0, 0, 0, 0)
            #self.zoomable_graphics_view.resetTransform()

    def file_bar_select(self):
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
        
   