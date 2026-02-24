from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy, QWidget, QListWidget, QHBoxLayout, QPushButton, QStatusBar, QGroupBox, QLayout, QStackedLayout, QLabel, QScrollArea, QGridLayout, QProgressBar, QSlider, QCheckBox, QSpinBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize, QRect
from PyImageLabeling.model.Utils import Utils

from PyImageLabeling.view.ZoomableGraphicsView import ZoomableGraphicsView

from PyImageLabeling.view.QWidgets import QBlanckWidget1, QSeparator1
import os

class Builder:

    def __init__(self, view):
        self.view = view

    def build(self):

        # Central widget
        self.view.central_widget = QWidget()
        self.view.setCentralWidget(self.view.central_widget)
        self.view.main_layout = QGridLayout(self.view.central_widget)
        self.view.main_layout.setSpacing(0)
        
        self.build_left_mode_bar()
        self.build_graphics_view()
        self.build_label_bar()
        self.build_image_bar()
        self.build_file_bar()
        self.build_status_bar()

        self.view.switch_mode_button.setText("Switch to ML")

    def switch_left_mode(self):
        if self.view.current_mode == "labeling":
            self.labeling_bar_scroll.hide()
            self.ml_bar_scroll.show()
            self.view.current_mode = "ml"
            self.view.switch_mode_button.setText("Switch to Labeling")
        else:
            self.ml_bar_scroll.hide()
            self.labeling_bar_scroll.show()
            self.view.current_mode = "labeling"
            self.view.switch_mode_button.setText("Switch to ML")

    def build_status_bar(self):
        self.view.statusBar().showMessage('Ready')
        self.view.progressBar = QProgressBar()
        self.view.statusBar().addPermanentWidget(self.view.progressBar) 
        
        # Add ML status indicator
        self.view.ml_status_label = QLabel("ML: Not trained")
        self.view.ml_status_label.setStyleSheet("color: gray;")
        self.view.statusBar().addPermanentWidget(self.view.ml_status_label)
        
    def build_file_bar(self):
        self.view.file_bar_container = QWidget()
        self.view.file_bar_layout = QVBoxLayout(self.view.file_bar_container)
        self.file_bar_scroll = QScrollArea()
        self.file_bar_button_container = QWidget()
        self.file_bar_button_container.setObjectName("file_bar")

        self.file_bar_button_layout = QHBoxLayout(self.file_bar_button_container)
        
        for button in self.view.config["file_bar"]:
            button_name = button["name"]
            self.view.buttons_file_bar[button_name] = QPushButton()
            self.view.buttons_file_bar[button_name].setToolTip(button["tooltip"]) # Detailed tooltip
            self.view.buttons_file_bar[button_name].setObjectName("permanent")
            icon_path = Utils.get_icon_path(button["icon"])
            if os.path.exists(icon_path):
                self.view.buttons_file_bar[button_name].setIcon(QIcon(icon_path))
                self.view.buttons_file_bar[button_name].setIconSize(QSize(*self.view.config["window_size"]["icon"]))
            self.view.buttons_file_bar[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
            self.view.buttons_file_bar[button_name].setCheckable(button["checkable"])
            if 'previous' in button_name or 'next' in button_name or 'save' in button_name:
                self.view.buttons_file_bar[button_name].setEnabled(False)

            self.file_bar_button_layout.addWidget(self.view.buttons_file_bar[button_name])
        self.view.file_bar_layout.addWidget(self.file_bar_button_container)
        self.file_bar_button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.view.file_bar_list = QListWidget()
        self.view.file_bar_list.itemSelectionChanged.connect(self.view.file_bar_select)
        
        self.view.file_bar_list.setMinimumWidth(0)
        
        self.view.file_bar_layout.setSpacing(0)
        self.view.file_bar_layout.setContentsMargins(0,0,0,10)

        
        self.view.file_bar_container.setMinimumWidth(self.view.config["window_size"]["file_bar"]["width"])
        self.view.file_bar_container.setMaximumWidth(self.view.config["window_size"]["file_bar"]["width"])
        
        self.view.file_bar_layout.addWidget(self.view.file_bar_list)
        
        self.view.main_layout.addWidget(self.view.file_bar_container, 0, 3, 3, 1)

    def build_left_mode_bar(self):
        self.build_labeling_bar()
        self.build_ml_bar()

        self.ml_bar_scroll.hide()
        self.view.current_mode = "labeling"

        self.view.main_layout.addWidget(self.ml_bar_scroll, 0, 0, 1, 1)

    def build_ml_bar(self):
        """
        Build ML prediction panel on the left sidebar using config["ml_buttons_config"].
        Matches the aesthetic of the labeling bar with QGroupBox sections.
        """

        # Container for scroll area content
        self.ml_bar_container = QWidget()
        ml_bar_layout = QVBoxLayout(self.ml_bar_container)
        ml_bar_layout.setContentsMargins(0, 0, 0, 0)
        ml_bar_layout.setSpacing(0)
        ml_bar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ML Actions Section 
        actions_frame = QGroupBox()
        actions_frame.setTitle("ML Actions")
        actions_layout = QVBoxLayout(actions_frame)
        
        # Collect ML setting buttons (same pattern as labeling bar)
        ml_setting_buttons = {}
        for category in self.view.config["labeling_bar_setting"]:
            category_name = tuple(category.keys())[0]
            if "Setting" in category_name:
                for button in category[category_name]:
                    base_name = button["name"].replace("_setting", "")
                    ml_setting_buttons[base_name] = button

        # Dynamically create buttons from config
        self.view.buttons_ml_bar = {}

        for btn_cfg in self.view.config["ml_buttons_config"]:
            btn_name = btn_cfg["name"]

            self.view.buttons_ml_bar[btn_name] = QPushButton(btn_cfg["name_view"])
            self.view.buttons_ml_bar[btn_name].setToolTip(btn_cfg["tooltip"])
            self.view.buttons_ml_bar[btn_name].setCheckable(btn_cfg["checkable"])
            icon_path = Utils.get_icon_path(btn_cfg["icon"])
            if os.path.exists(icon_path):
                self.view.buttons_ml_bar[btn_name].setIcon(QIcon(icon_path))
                self.view.buttons_ml_bar[btn_name].setIconSize(QSize(*self.view.config["window_size"]["icon"]))
            self.view.buttons_ml_bar[btn_name].clicked.connect(getattr(self.view.controller, btn_cfg["slot"]))

            if btn_name in ml_setting_buttons:
                setting_button_config = ml_setting_buttons[btn_name]

                h_layout = QHBoxLayout()
                self.view.buttons_ml_bar[btn_name].setObjectName("with_parameters")
                h_layout.addWidget(self.view.buttons_ml_bar[btn_name])

                setting_button_name = setting_button_config["name"]
                self.view.buttons_ml_bar[setting_button_name] = QPushButton()
                self.view.buttons_ml_bar[setting_button_name].setObjectName("setting_button")
                self.view.buttons_ml_bar[setting_button_name].setToolTip(setting_button_config["tooltip"])
                setting_icon_path = Utils.get_icon_path(setting_button_config["icon"])
                if os.path.exists(setting_icon_path):
                    self.view.buttons_ml_bar[setting_button_name].setIcon(QIcon(setting_icon_path))
                    self.view.buttons_ml_bar[setting_button_name].setIconSize(QSize(*self.view.config["window_size"]["icon"]))
                self.view.buttons_ml_bar[setting_button_name].clicked.connect(getattr(self.view.controller, setting_button_name))
                self.view.buttons_ml_bar[setting_button_name].setCheckable(setting_button_config["checkable"])

                h_layout.setSpacing(0)
                h_layout.addWidget(self.view.buttons_ml_bar[setting_button_name])
                actions_layout.addLayout(h_layout)
            else:
                self.view.buttons_ml_bar[btn_name].setObjectName("without_parameters")
                actions_layout.addWidget(self.view.buttons_ml_bar[btn_name])

        ml_bar_layout.addWidget(actions_frame)

        display_frame = QGroupBox()
        display_frame.setTitle("Display Settings")
        display_layout = QVBoxLayout(display_frame)

        # redictions checkbox
        self.view.ml_show_predictions_checkbox = QCheckBox("Show Predictions")
        self.view.ml_show_predictions_checkbox.setChecked(True)
        self.view.ml_show_predictions_checkbox.setToolTip("Toggle visibility of ML predictions")
        self.view.ml_show_predictions_checkbox.stateChanged.connect(self.view.controller.ml_toggle_predictions)
        display_layout.addWidget(self.view.ml_show_predictions_checkbox)

        # Confidence Threshold
        confidence_label = QLabel("Confidence Threshold:")
        display_layout.addWidget(confidence_label)

        confidence_container = QWidget()
        confidence_layout = QHBoxLayout(confidence_container)
        confidence_layout.setContentsMargins(0, 0, 0, 0)

        self.view.ml_confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.view.ml_confidence_slider.setMinimum(10)
        self.view.ml_confidence_slider.setMaximum(100)
        self.view.ml_confidence_slider.setValue(70)
        self.view.ml_confidence_slider.setToolTip("Adjust confidence threshold for predictions")
        self.view.ml_confidence_slider.valueChanged.connect(self.view.controller.ml_update_confidence)
        confidence_layout.addWidget(self.view.ml_confidence_slider)

        self.view.ml_confidence_label = QLabel("0.70")
        self.view.ml_confidence_label.setMinimumWidth(40)
        confidence_layout.addWidget(self.view.ml_confidence_label)
        display_layout.addWidget(confidence_container)

        ml_bar_layout.addWidget(display_frame)

        stats_frame = QGroupBox()
        stats_frame.setTitle("Statistics")
        stats_layout = QVBoxLayout(stats_frame)

        self.view.ml_stats_label = QLabel(
            "Annotated Images: 0\n"
            "Total Annotations: 0\n"
            "Model Status: Not trained"
        )
        self.view.ml_stats_label.setWordWrap(True)
        stats_layout.addWidget(self.view.ml_stats_label)

        ml_bar_layout.addWidget(stats_frame)

        # Scroll Area - 
        self.ml_bar_scroll = QScrollArea()
        self.ml_bar_scroll.setWidget(self.ml_bar_container)
        self.ml_bar_scroll.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.ml_bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.ml_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ml_bar_scroll.setWidgetResizable(True)
        self.ml_bar_scroll.setMinimumWidth(self.view.config["window_size"]["labeling_bar"]["width"])    
        self.ml_bar_scroll.setMaximumWidth(self.view.config["window_size"]["labeling_bar"]["width"])
        
        self.ml_bar_scroll.setMinimumHeight(self.view.config["window_size"]["labeling_bar"]["height"]) 
        self.ml_bar_scroll.setMaximumHeight(583)     

        self.ml_bar_scroll.hide()

    def build_labeling_bar(self):
        self.labeling_bar_container = QWidget()
        self.labeling_bar_scroll = QScrollArea()
        labeling_bar_layout = QVBoxLayout(self.labeling_bar_container)
        #left_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        
        setting_buttons = {}
        for category in self.view.config["labeling_bar_setting"]:
            category_name = tuple(category.keys())[0]
            if "Setting" in category_name:
                for button in category[category_name]:
                    # Extract the base name (remove "_setting" suffix)
                    base_name = button["name"].replace("_setting", "")
                    setting_buttons[base_name] = button

        for category_key in self.view.config["labeling_bar"].keys():
            category = self.view.config["labeling_bar"][category_key]
            category_name = category["name_view"]
            frame = QGroupBox()
            frame.setTitle(category_name)
            buttons_layout = QVBoxLayout(frame)
            
            for button in category["buttons"]:
                button_name = button["name"]
                self.view.buttons_labeling_bar[button_name] = QPushButton(button["name_view"])
                self.view.buttons_labeling_bar[button_name].setToolTip(button["tooltip"]) # Detailed tooltip
                icon_path = Utils.get_icon_path(button["icon"])
                if os.path.exists(icon_path):
                    self.view.buttons_labeling_bar[button_name].setIcon(QIcon(icon_path))
                    self.view.buttons_labeling_bar[button_name].setIconSize(QSize(*self.view.config["window_size"]["icon"])) 
                self.view.buttons_labeling_bar[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
                self.view.buttons_labeling_bar[button_name].setCheckable(button["checkable"])
                self.view.buttons_labeling_bar[button_name].setEnabled(False)
                
                if button_name in setting_buttons:
                    setting_button_config = setting_buttons[button_name]
                    
                    # Create horizontal layout: tool button + setting button
                    h_layout = QHBoxLayout()
                    self.view.buttons_labeling_bar[button_name].setObjectName("with_parameters")
                    h_layout.addWidget(self.view.buttons_labeling_bar[button_name])
                    
                    # Create setting button
                    setting_button_name = setting_button_config["name"]
                    self.view.buttons_labeling_bar[setting_button_name] = QPushButton()
                    self.view.buttons_labeling_bar[setting_button_name].setObjectName("setting_button")
                    self.view.buttons_labeling_bar[setting_button_name].setToolTip(setting_button_config["tooltip"])
                    
                    setting_icon_path = Utils.get_icon_path(setting_button_config["icon"])
                    if os.path.exists(setting_icon_path):
                        self.view.buttons_labeling_bar[setting_button_name].setIcon(QIcon(setting_icon_path))
                        self.view.buttons_labeling_bar[setting_button_name].setIconSize(QSize(*self.view.config["window_size"]["icon"]))
                    
                    self.view.buttons_labeling_bar[setting_button_name].clicked.connect(getattr(self.view.controller, setting_button_name))
                    self.view.buttons_labeling_bar[setting_button_name].setCheckable(setting_button_config["checkable"])
                    self.view.buttons_labeling_bar[setting_button_name].setEnabled(False)

                    h_layout.setSpacing(0)
                    h_layout.addWidget(self.view.buttons_labeling_bar[setting_button_name])
                    
                    buttons_layout.addLayout(h_layout)
                else:
                    # No setting button, add main button directly
                    self.view.buttons_labeling_bar[button_name].setObjectName("without_parameters")
                    buttons_layout.addWidget(self.view.buttons_labeling_bar[button_name])

            labeling_bar_layout.addWidget(frame)

        #self.labeling_bar_container.setMinimumWidth(self.view.config["window_size"]["labeling_bar"]["width"])    
        #self.labeling_bar_container.setMaximumWidth(self.view.config["window_size"]["labeling_bar"]["width"])
        #labeling_bar_layout.setContentsMargins(0,0,0,self.view.config["window_size"]["margin"])
        #labeling_bar_layout.setSpacing(self.view.config["window_size"]["margin"])
        
        self.labeling_bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.labeling_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.labeling_bar_scroll.setWidgetResizable(True)
        self.labeling_bar_scroll.setMinimumWidth(self.view.config["window_size"]["labeling_bar"]["width"])    
        self.labeling_bar_scroll.setMaximumWidth(self.view.config["window_size"]["labeling_bar"]["width"])
        
        self.labeling_bar_scroll.setMinimumHeight(self.view.config["window_size"]["labeling_bar"]["height"]) 
        self.labeling_bar_scroll.setMaximumHeight(583)     
        #self.labeling_bar_scroll.setMaximumWidth(self.view.config["window_size"]["labeling_bar"]["width"])
        labeling_bar_layout.setContentsMargins(0,0,0,0)
        #self.labeling_bar_scroll.setMaximumHeight(self.view.config["window_size"]["label_bar"]["height"])    

        #self.labeling_bar_container.setContentsMargins(0,0,0,self.view.config["window_size"]["margin"]) 
        #self.labeling_bar_scroll.setSpacing(self.view.config["window_size"]["margin"])
        self.labeling_bar_scroll.setWidget(self.labeling_bar_container)
        
        labeling_bar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.view.main_layout.addWidget(self.labeling_bar_scroll, 0, 0, 1, 1)    
    
    def build_graphics_view(self):
        self.graphics_view_container = QWidget()
        graphics_view_main_layout = QVBoxLayout(self.graphics_view_container)
        graphics_view_main_layout.setSpacing(0)
        graphics_view_main_layout.setContentsMargins(0, 0, 0, 0)

        # Create the stacked layout for the graphics view
        self.graphics_view_layout = QStackedLayout()
        self.graphics_view_layout.setContentsMargins(0, 0, 0, 0)
        graphics_view_main_layout.addLayout(self.graphics_view_layout)

        self.view.zoomable_graphics_view = ZoomableGraphicsView(self.view)
        self.view.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.graphics_view_layout.addWidget(self.view.zoomable_graphics_view)

        # Menu container
        self.option_container = QWidget(self.view.zoomable_graphics_view)
        self.option_container.setGeometry(10, 10, 1, 1)  # temporary size
        self.option_container.raise_()

        # Main menu button
        self.view.menu_button = QPushButton("Menu")
        self.view.menu_button.setObjectName("menu_button")
        self.view.menu_button.setToolTip("Show/hide options")
        self.view.menu_button.clicked.connect(self.toggle_menu)

        # Menu content (hidden by default)
        self.menu_content = QWidget()
        self.menu_content.setVisible(False)
        self.menu_content.setStyleSheet("background-color: white; border: 1px solid gray;")

        # Vertical layout for menu items
        menu_layout = QVBoxLayout(self.menu_content)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(5)

        # Add the three buttons to the menu
        self.view.image_option_button = QPushButton("Image Option")
        self.view.image_option_button.clicked.connect(self.view.controller.image_option)
        menu_layout.addWidget(self.view.image_option_button)

        self.view.option_button = QPushButton("Option")
        self.view.option_button.clicked.connect(self.view.controller.global_option)
        menu_layout.addWidget(self.view.option_button)

        self.view.switch_mode_button = QPushButton("Switch mode")
        self.view.switch_mode_button.setObjectName("mode_switch")
        self.view.switch_mode_button.setToolTip("Switch between Labeling and ML modes")
        self.view.switch_mode_button.clicked.connect(self.switch_left_mode)
        menu_layout.addWidget(self.view.switch_mode_button)

        # Layout for the menu button and its content
        layout = QVBoxLayout(self.option_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view.menu_button)
        layout.addWidget(self.menu_content)

        # Make the container resize to fit its contents
        self.option_container.adjustSize()
        self.view.main_layout.addWidget(self.graphics_view_container, 0, 1, 3, 1)
        self.graphics_view_container.setMinimumWidth(self.view.config["window_size"]["graphics_view"]["width"])

    # New method to toggle menu visibility
    def toggle_menu(self):
        self.menu_content.setVisible(not self.menu_content.isVisible())
        self.option_container.adjustSize()
    
    def build_image_bar(self):
        self.image_bar_container_1 = QWidget()
        
        self.image_bar_container_1.setMinimumHeight(self.view.config["window_size"]["image_bar"]["height"])
        self.image_bar_container_1.setMaximumHeight(self.view.config["window_size"]["image_bar"]["height"])
        
        self.view.image_bar_layout_1 = QVBoxLayout(self.image_bar_container_1)

        self.image_bar_container_2 = QWidget()
        self.image_bar_container_2.setObjectName("image_bar")
        self.view.image_bar_layout_1.addWidget(self.image_bar_container_2)
        self.view.image_bar_layout_1.setContentsMargins(0,0,0,self.view.config["window_size"]["margin"])

        self.view.image_bar_layout_1.setAlignment(Qt.AlignmentFlag.AlignRight)        

        self.view.image_bar_layout_2 = QVBoxLayout(self.image_bar_container_2)
        
        self.image_bar_container_2.setMinimumWidth(self.view.config["window_size"]["image_bar"]["width"])
        self.image_bar_container_2.setMaximumWidth(self.view.config["window_size"]["image_bar"]["width"])

        for button in self.view.config["image_bar"]:
            button_name = button["name"]
            self.view.buttons_image_bar[button_name] = QPushButton()
            self.view.buttons_image_bar[button_name].setObjectName("permanent")
            self.view.buttons_image_bar[button_name].setToolTip(button["tooltip"])
            icon_path = Utils.get_icon_path(button["icon"])
            if os.path.exists(icon_path):
                self.view.buttons_image_bar[button_name].setIcon(QIcon(icon_path))
                self.view.buttons_image_bar[button_name].setIconSize(QSize(*self.view.config["window_size"]["icon"])) 
            self.view.buttons_image_bar[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
            self.view.buttons_image_bar[button_name].setCheckable(button["checkable"])
            self.view.buttons_image_bar[button_name].setEnabled(False)
            self.view.image_bar_layout_2.addWidget(self.view.buttons_image_bar[button_name])

        self.view.image_bar_layout_2.setAlignment(Qt.AlignmentFlag.AlignRight)  
        self.view.image_bar_layout_1.setContentsMargins(0, 10, 0, 10)     
        self.view.main_layout.addWidget(self.image_bar_container_1, 2, 0, 1, 1)

    def build_label_bar(self):
        self.label_bar_container = QWidget()
        self.label_bar_scroll = QScrollArea()
        self.label_bar_container.setObjectName("label_bar")
        self.view.label_bar_layout = QHBoxLayout(self.label_bar_container)
        
        self.view.label_bar_layout.addWidget(QBlanckWidget1())

        for button in self.view.config["label_bar"]["permanent"]:
            button_name = button["name"]
            self.view.buttons_label_bar_permanent[button_name] = QPushButton()
            self.view.buttons_label_bar_permanent[button_name].setObjectName("permanent")
            self.view.buttons_label_bar_permanent[button_name].setToolTip(button["tooltip"])
            self.view.buttons_label_bar_permanent[button_name].setCheckable(button["checkable"])
            self.view.buttons_label_bar_permanent[button_name].setEnabled(False)

            icon_path = Utils.get_icon_path(button["icon"])
            if os.path.exists(icon_path):
                self.view.buttons_label_bar_permanent[button_name].setIcon(QIcon(icon_path))
                self.view.buttons_label_bar_permanent[button_name].setIconSize(QSize(*self.view.config["window_size"]["icon"])) 
            self.view.buttons_label_bar_permanent[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
            self.view.label_bar_layout.addWidget(self.view.buttons_label_bar_permanent[button_name])
        
        self.view.label_bar_layout.setContentsMargins(0,0,0,0)
        self.view.label_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.label_bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.label_bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.label_bar_scroll.setWidgetResizable(True)
        self.label_bar_scroll.setWidget(self.label_bar_container)
        self.label_bar_scroll.setMaximumHeight(self.view.config["window_size"]["label_bar"]["height"])    
    
        self.view.main_layout.addWidget(self.label_bar_scroll, 4, 0, 1, 4) 
        self.view.main_layout.setRowMinimumHeight(2, 100)

    def build_new_layer_label_bar(self, label_id, name, labeling_mode, color):
        
        push_buttons = dict() # Dictionnary of push buttons for this label 
        
        new_layer_label_bar_container = QWidget()
        new_layer_label_bar_container.setObjectName("label_bar_new")

        new_layer_label_bar_layout = QHBoxLayout(new_layer_label_bar_container)
        new_layer_label_bar_layout.setContentsMargins(0,0,0,0)
        new_layer_label_bar_layout.setSpacing(0)
        new_layer_label_bar_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        
        # Activation button
        push_buttons["activation"] = QPushButton(name)
        push_buttons["activation"].setObjectName('activation')
        push_buttons["activation"].setCheckable(True)
        push_buttons["activation"].setChecked(True)
        push_buttons["activation"].clicked.connect(lambda: self.view.controller.select_label(label_id))    
        new_layer_label_bar_layout.addWidget(push_buttons["activation"])
        separator = QSeparator1()
        self.view.label_bar_layout.addWidget(separator)

        # The others buttons
        for button in self.view.config["label_bar"]["layer"]:        
            type_name_button = button["name"]
            
            push_buttons[type_name_button] = QPushButton()
            push_buttons[type_name_button].setObjectName(button["name"])
            push_buttons[type_name_button].setToolTip(button["tooltip"])
            push_buttons[type_name_button].setCheckable(button["checkable"])
            
            if type_name_button != "color":
                icon_path = Utils.get_icon_path(button["icon"])
                if os.path.exists(icon_path):
                    push_buttons[type_name_button].setIcon(QIcon(icon_path))
                    push_buttons[type_name_button].setIconSize(QSize(*self.view.config["window_size"]["icon"])) 

            if type_name_button == "color":
                push_buttons[type_name_button].setStyleSheet(Utils.color_to_stylesheet(color))
                push_buttons[type_name_button].clicked.connect(lambda: self.view.controller.color(label_id))
            
            elif type_name_button == "visibility":
                push_buttons[type_name_button].setChecked(True)
                push_buttons[type_name_button].clicked.connect(lambda: self.view.controller.visibility(label_id))
            
            elif type_name_button == "label_setting":
                push_buttons[type_name_button].clicked.connect(lambda: self.view.controller.label_setting(label_id))

            elif type_name_button == "remove_label":
                push_buttons[type_name_button].clicked.connect(lambda: self.view.controller.remove_label(label_id))
        
            new_layer_label_bar_layout.addWidget(push_buttons[type_name_button])
        
        self.view.label_bar_layout.addWidget(new_layer_label_bar_container)

        self.view.buttons_label_bar_temporary[label_id] = push_buttons # Usefull to control all buttons :)
        self.view.container_label_bar_temporary[label_id] = (new_layer_label_bar_container, separator) # Usefull to delete these qwidget :)