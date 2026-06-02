
from PyImageLabeling.view.Builder import Builder
from PyImageLabeling.model.Utils import Utils

from PyQt6.QtWidgets import QListWidget, QProgressDialog, QApplication, QMainWindow, QWidget, QHBoxLayout,  QListWidgetItem, QLabel,  QPushButton, QGraphicsItem, QGraphicsEllipseItem, QCheckBox
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

        self.label_tag = QPixmap(Utils.get_icon_path("label_tag"))
        self.label_tag= self.label_tag.scaled(QSize(*self.config["window_size"]["icon_save_marker"]), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)

        self.loaded = QPixmap(Utils.get_icon_path("loaded"))
        self.loaded= self.loaded.scaled(QSize(*self.config["window_size"]["icon_save_marker"]), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)

        self.empty = QPixmap(Utils.get_icon_path("empty"))
        self.empty= self.empty.scaled(QSize(*self.config["window_size"]["icon_save_marker"]), aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
        
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

    

    def file_bar_add(self, current_file_paths, progress=None, progress_offset=0):
        """Add image files to the file-bar list.

        Args:
            current_file_paths: list of absolute image paths to add.
            progress:           optional QProgressDialog to update while building widgets.
            progress_offset:    value already consumed in the progress range before this call.

        Returns:
            True if the user canceled via the progress dialog, False otherwise.
        """
        ICON_SIZE = QSize(*self.config["window_size"]["icon_save_marker"])
        start_row = self.file_bar_list.count()

        item_widgets = []
        for file in current_file_paths:
            
            filename = os.path.basename(file)

            item = QListWidgetItem()
            item.file_path = file
            item.filename = filename

            self.file_bar_list.addItem(item)
            
            item_widget = QWidget()
            item_widget.setObjectName("file_item")
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            item_layout.setSpacing(4)

            # File name label (takes all remaining space)
            file_label = QLabel(filename)
            file_label.setObjectName("label_files")
            file_label.setToolTip(filename)

            # Remove button
            remove_button = QPushButton("×")
            remove_button.setToolTip("Remove file")
            remove_button.setObjectName("remove_image_button")
            remove_button.setFixedSize(20, 20)

            # label_tag icon — fixed size to always reserve space
            icon_button_1 = QLabel()
            icon_button_1.setPixmap(self.empty)               
            icon_button_1.setObjectName("save_marker")
            icon_button_1.setFixedSize(ICON_SIZE)
            icon_button_1.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # asterisk icon — always visible
            icon_button_2 = QLabel()
            icon_button_2.setPixmap(self.icon_asterisk_green)
            icon_button_2.setObjectName("save_marker")
            icon_button_2.setFixedSize(ICON_SIZE)
            icon_button_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # loaded icon — fixed size to always reserve space
            icon_button_3 = QLabel()
            icon_button_3.setPixmap(self.empty)               
            icon_button_3.setObjectName("save_marker")
            icon_button_3.setFixedSize(ICON_SIZE)
            icon_button_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Complete checkbox
            complete_checkbox = QCheckBox("")
            complete_checkbox.setObjectName("complete_checkbox")
            complete_checkbox.setFixedSize(16, 16)

            self.controller.model.icon_button_files[file] = {
                "label_tag": icon_button_1,
                "asterisk": icon_button_2,
                "loaded": icon_button_3,
                "complete": complete_checkbox,
            }

            remove_button.clicked.connect(partial(self.file_bar_remove, item, self.controller.model.file_paths, self.controller.model.image_items))

            # file label stretches, icons pinned to the right
            item_layout.addWidget(file_label, stretch=1)
            item_layout.addStretch()
            item_layout.addWidget(remove_button)
            item_layout.addWidget(icon_button_1)
            item_layout.addWidget(icon_button_2)
            item_layout.addWidget(icon_button_3)
            item_layout.addWidget(complete_checkbox)
            item_widgets.append((item, item_widget))
            
        n = len(item_widgets)
        # Throttle: update at most ~100 times regardless of dataset size.
        # Each setValue() calls processEvents() internally, which forces a Qt
        # layout pass — calling it on every item would be 50–100× slower.
        _upd = max(1, n // 100)
        for i, (item, item_widget) in enumerate(item_widgets):
            self.file_bar_list.setItemWidget(item, item_widget)
            if progress is not None and (i % _upd == 0 or i == n - 1):
                if progress.wasCanceled():
                    self._file_bar_rollback(current_file_paths, start_row)
                    return True
                progress.setLabelText(f"Adding images to list… ({i + 1} / {n})")
                progress.setValue(progress_offset + i + 1)
                if progress.wasCanceled():
                    self._file_bar_rollback(current_file_paths, start_row)
                    return True
        return False

        
    def _file_bar_rollback(self, file_paths, start_row):
        for row in range(self.file_bar_list.count() - 1, start_row - 1, -1):
            self.file_bar_list.takeItem(row)
        for f in file_paths:
            self.controller.model.icon_button_files.pop(f, None)

    def file_bar_remove(self, item, loaded_image_paths, image_items):
        # Get the row of the item
        path_to_remove = None
        for path in loaded_image_paths:
            if item.filename in path:
                path_to_remove = path
                break
        
        if path_to_remove:
            # Check if this is the currently displayed image
            is_current_image = False
            current_image = self.controller.model.current_image_item
            if (current_image is not None and 
                path_to_remove in image_items and 
                image_items[path_to_remove] == current_image):
                is_current_image = True
            
            # If this is the current image, clear the scene first
            if is_current_image:
                self.zoomable_graphics_view.scene.clear()
                self.controller.model.current_image_item = None
            
            # Properly cleanup the ImageItem
            if path_to_remove in image_items and image_items[path_to_remove] is not None:
                image_item = image_items[path_to_remove]
                
                # Mark all overlays as not displayed since scene might be cleared
                for label_id in list(image_item.labeling_overlays):
                    overlay = image_item.labeling_overlays[label_id]
                    overlay.is_displayed_in_scene = False
                    overlay.labeling_overlay_item = None
                    
                    # End any active painters
                    if  overlay.labeling_overlay_painter.isActive():
                        overlay.labeling_overlay_painter.end()
                    if  overlay.labeling_overlay_opacity_painter.isActive():
                        overlay.labeling_overlay_opacity_painter.end()
                    if  overlay.labeling_overlay_color_painter.isActive():
                        overlay.labeling_overlay_color_painter.end()
                
                # Clear image item scene state
                image_item.is_displayed_in_scene = False
                image_item.image_item = None
                image_item.backgroung_item = None
            
            # Remove from the data structures
            loaded_image_paths.remove(path_to_remove)
            del image_items[path_to_remove]
        
        # Remove from UI
        row = self.file_bar_list.row(item)
        if row >= 0:
            self.file_bar_list.takeItem(row)
        
        # Handle empty list case
        if len(loaded_image_paths) == 0:
            # Disable navigation buttons
            for button_name in self.buttons_file_bar:
                if 'previous' in button_name or 'next' in button_name:
                    self.buttons_file_bar[button_name].setEnabled(False)
            
            # Disable image operation buttons
            for button_names in self.buttons_image_bar:
                self.buttons_image_bar[button_names].setEnabled(False)

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
        version = Utils.get_version()
        self.setWindowTitle("PyImageLabeling - "+ str(version))
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
        
   