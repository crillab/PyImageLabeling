



from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QStatusBar, QGroupBox, QLayout, QStackedLayout, QLabel, QScrollArea, QGridLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize, QRect
from model.Utils import Utils

from PyImageLabeling.view.ZoomableGraphicsView import ZoomableGraphicsView
from PyImageLabeling.view.QLabelSettingForm import QLabelSettingForm

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
        self.build_left_layout()
        self.build_right_layout()
        self.build_bottom_layout()
        self.build_image_layout()
        

    def build_left_layout(self):
        # Left side - bottons area
        self.left_layout_container = QWidget()
    
        left_layout = QVBoxLayout(self.left_layout_container)
        #left_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        
        for category in self.view.config["buttons"]:
            category_name = tuple(category.keys())[0]
            frame = QGroupBox()
            frame.setTitle(category_name)
            buttons_layout = QVBoxLayout(frame)
            
            for button in category[category_name]:
                button_name = button["name"]
                self.view.buttons[button_name] = QPushButton(button["name_view"])
                self.view.buttons[button_name].setToolTip(button["tooltip"]) # Detailed tooltip
                icon_path = Utils.get_icon_path(button["icon"])
                if os.path.exists(icon_path):
                    self.view.buttons[button_name].setIcon(QIcon(icon_path))
                
                self.view.buttons[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
                self.view.buttons[button_name].setCheckable(button["checkable"])
                
                buttons_layout.addWidget(self.view.buttons[button_name])


            self.left_layout_container.setMinimumWidth(200)    
            self.left_layout_container.setMaximumWidth(200)
            left_layout.addWidget(frame)

        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.view.main_layout.addWidget(self.left_layout_container, 0, 0)  
        #self.left_layout_container.setMinimumSize(self.view.left_panel_width+20, self.view.left_panel_height)
        
    
    def build_right_layout(self):
        # Right side - image area
        self.right_layout_container = QWidget()
        self.right_layout = QStackedLayout(self.right_layout_container)
        

        self.view.zoomable_graphics_view = ZoomableGraphicsView()
        self.view.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.right_layout.addWidget(self.view.zoomable_graphics_view)  
        
        self.view.main_layout.addWidget(self.right_layout_container, 0, 1, 2, 2)  
        #self.right_layout_container.setMinimumSize(self.view.right_panel_width, self.view.right_panel_height)
        
    def build_bottom_layout(self):
        self.bottom_layout_container = QWidget()
        self.bottom_scroll = QScrollArea()
        self.bottom_layout_container.setObjectName("bottom_bar")
        self.view.bottom_layout = QHBoxLayout(self.bottom_layout_container)
        
        self.view.bottom_layout.addWidget(QBlanckWidget1())
        self.view.bottom_layout.addWidget(QSeparator1())
        
        for button in self.view.config["status_bar"]["permanent"]:
            button_name = button["name"]
            self.view.buttons[button_name] = QPushButton()
            self.view.buttons[button_name].setObjectName("permanent")
            self.view.buttons[button_name].setToolTip(button["tooltip"])
            icon_path = Utils.get_icon_path(button["icon"])
            if os.path.exists(icon_path):
                self.view.buttons[button_name].setIcon(QIcon(icon_path))
                self.view.buttons[button_name].setIconSize(QSize(25, 25)) 
            self.view.buttons[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
            
            self.view.bottom_layout.addWidget(self.view.buttons[button_name])
        
        self.view.bottom_layout.addWidget(QSeparator1())
        self.view.bottom_layout.setContentsMargins(0,0,0,0)
        self.view.bottom_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        #self.bottom_layout.addWidget(self.view.bottom_bar)  
        self.bottom_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bottom_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.bottom_scroll.setWidgetResizable(True)
        self.bottom_scroll.setWidget(self.bottom_layout_container)
        self.bottom_scroll.setMaximumHeight(60)    
        
        self.view.main_layout.addWidget(self.bottom_scroll, 2, 0, 1, 3) 

    def build_image_layout(self):
        self.image_layout_container = QWidget()
        
        self.image_layout_container.setMinimumHeight(200)
        self.image_layout_container.setMaximumHeight(200)
        
        self.view.image_layout = QVBoxLayout(self.image_layout_container)

        self.image_layout_container_tmp = QWidget()
        self.image_layout_container_tmp.setObjectName("image_bar")
        self.view.image_layout.addWidget(self.image_layout_container_tmp)
        self.view.image_layout.setContentsMargins(0,0,0,10)

        self.view.image_layout.setAlignment(Qt.AlignmentFlag.AlignRight)        

        self.view.image_layout_tmp = QVBoxLayout(self.image_layout_container_tmp)
        
        self.image_layout_container_tmp.setMinimumWidth(50)
        self.image_layout_container_tmp.setMaximumWidth(50)

        for button in self.view.config["image_bar"]:
            button_name = button["name"]
            self.view.buttons[button_name] = QPushButton()
            self.view.buttons[button_name].setObjectName("permanent")
            self.view.buttons[button_name].setToolTip(button["tooltip"])
            icon_path = Utils.get_icon_path(button["icon"])
            if os.path.exists(icon_path):
                self.view.buttons[button_name].setIcon(QIcon(icon_path))
                self.view.buttons[button_name].setIconSize(QSize(25, 25)) 
            self.view.buttons[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
            self.view.buttons[button_name].setCheckable(button["checkable"])
            
            #self.view.buttons[button_name].clicked.connect(getattr(self.view.controller, button["name"]))
            
            self.view.image_layout_tmp.addWidget(self.view.buttons[button_name])

        #self.view.image_layout_tmp.addWidget(QSeparator1())
        #self.view.image_layout_tmp.addWidget(QSeparator1())

        self.view.image_layout_tmp.setAlignment(Qt.AlignmentFlag.AlignRight)        

        self.view.main_layout.addWidget(self.image_layout_container, 1, 0)
        
    def build_label_setting_dialog(self):
        qlabelsettingdialog = QLabelSettingForm(self.view, self)
        qlabelsettingdialog.open()
        

    def build_new_layer_bottom_bar(self, name, color):
        print("build_new_layer")
        
        new_layer_layout_container = QWidget()
        
        new_layer_layout = QHBoxLayout(new_layer_layout_container)
        new_layer_layout.setContentsMargins(0,0,0,0)
        #new_layer_layout_container.setContentsMargins(0,0,0,0)
        new_layer_layout.setSpacing(0)
        new_layer_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        

        new_layer_activation = QPushButton(name)
        color_style = f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); color: {'white' if color.lightness() < 128 else 'black'};"
        new_layer_activation.setStyleSheet(color_style)

        new_layer_activation.setObjectName("activation")
        new_layer_activation.setCheckable(True)
        new_layer_activation.setChecked(True)
        new_layer_layout.addWidget(new_layer_activation)
        
        for button in self.view.config["status_bar"]["layer"]:
            button_name = button["name"]
            tmp_button = QPushButton()
            tmp_button.setObjectName(button_name)
            tmp_button.setToolTip(button["tooltip"])
            icon_path = Utils.get_icon_path(button["icon"])
            if os.path.exists(icon_path):
                tmp_button.setIcon(QIcon(icon_path))
            new_layer_layout.addWidget(tmp_button)
        
        self.view.bottom_layout.addWidget(new_layer_layout_container)
        self.view.bottom_layout.addWidget(QSeparator1())
        

        