



from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel, QGroupBox, QLayout, QStackedLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
from model.Utils import Utils

from PyImageLabeling.view.ZoomableGraphicsView import ZoomableGraphicsView

import os

class Builder:

    def __init__(self, view):
        self.view = view

    def build(self):

        # Central widget
        self.view.central_widget = QWidget()
        self.view.setCentralWidget(self.view.central_widget)
        self.view.main_layout = QHBoxLayout(self.view.central_widget)
        
        self.build_left_layout()
        self.build_right_layout()

    def build_left_layout(self):
        # Left side - bottons area
        self.left_layout_container = QWidget()
    
        left_layout = QVBoxLayout(self.left_layout_container)
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        
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


            frame.setMinimumWidth(self.view.left_panel_width)    
            left_layout.addWidget(frame)

        self.view.main_layout.addWidget(self.left_layout_container, 1, Qt.AlignmentFlag.AlignTop)  
        self.left_layout_container.setMinimumSize(self.view.left_panel_width, self.view.left_panel_height)
        
    
    def build_right_layout(self):
        # Right side - image area
        self.right_layout_container = QWidget()
        self.right_layout = QStackedLayout(self.right_layout_container)
        
        self.view.zoomable_graphics_view = ZoomableGraphicsView()
        self.view.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.right_layout.addWidget(self.view.zoomable_graphics_view)  # Give it stretch priority

        self.view.main_layout.addWidget(self.right_layout_container)  
        self.right_layout_container.setMinimumSize(self.view.right_panel_width, self.view.right_panel_height)
        
        
            
        
