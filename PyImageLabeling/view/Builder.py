



from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
from PyImageLabeling.model.Utils import Utils

from PyImageLabeling.view.ZoomableGraphicsView import ZoomableGraphicsView

import os

class Builder:

    def __init__(self, view):
        self.view = view

    def build(self):
        # Dynamic sizing for components
        self.calculate_component_sizes()

        # Central widget
        self.view.central_widget = QWidget()
        self.view.setCentralWidget(self.view.central_widget)
        
        # Main layout with dynamic stretch factors
        self.view.main_layout = QHBoxLayout(self.view.central_widget)

        self.view.main_layout.setContentsMargins(self.view.layout_spacing, self.view.layout_spacing, 
                                      self.view.layout_spacing, self.view.layout_spacing)
        self.view.main_layout.setSpacing(self.view.layout_spacing)

        self.build_left_layout()
        self.build_right_layout()

    def build_left_layout(self):
        
        # Left side - image area
        left_layout_container = QWidget()
        left_layout = QVBoxLayout(left_layout_container)
        
        # Top buttons row
        button_row = QHBoxLayout()
        
        # Load button with dynamic height
        self.view.load_button = QPushButton("Load Image")
        self.view.load_button.setFixedHeight(self.view.button_height)
        self.view.load_button.setMinimumWidth(self.view.button_min_width)
        #self.view.load_button.clicked.connect(self.view.load_image)
        self.view.load_button.setToolTip("Click to load an image into the viewer. This will allow you to select an image file from your system to display.")  # Detailed tooltip
        button_row.addWidget(self.view.load_button)
        
        # Load Layer button with dynamic height
        self.view.load_layer_button = QPushButton("Load Layer")
        self.view.load_layer_button.setFixedHeight(self.view.button_height)
        self.view.load_layer_button.setMinimumWidth(self.view.button_min_width)
        #self.view.load_layer_button.clicked.connect(self.view.load_layer)
        self.view.load_layer_button.setToolTip("Click to load a new layer on top of the existing image. This allows you to add additional content or annotations to the image.")  # Detailed tooltip
        button_row.addWidget(self.view.load_layer_button)
        
        # Unload Layer button with dynamic height
        self.view.unload_layer_button = QPushButton("Unload Layer")
        self.view.unload_layer_button.setFixedHeight(self.view.button_height)
        self.view.unload_layer_button.setMinimumWidth(self.view.button_min_width)
        #self.view.unload_layer_button.clicked.connect(self.view.toggle_layer)
        self.view.unload_layer_button.setToolTip("Click to remove the currently selected layer from the image. This will leave only the base image or other layers you wish to keep.")  # Detailed tooltip
        button_row.addWidget(self.view.unload_layer_button)
        
        # Save button with dynamic height
        self.view.save_button = QPushButton("Save Layer")
        self.view.save_button.setFixedHeight(self.view.button_height)
        self.view.save_button.setMinimumWidth(self.view.button_min_width)
        #self.view.save_button.clicked.connect(self.view.save_image)
        self.view.save_button.setToolTip("Click to save the current layer to a file. This will store the layer as a separate image file on your system.")  # Detailed tooltip
        button_row.addWidget(self.view.save_button)

        self.view.shortcut_button = QPushButton("Shortcut")
        self.view.shortcut_button.setFixedHeight(self.view.button_height)
        self.view.shortcut_button.setMinimumWidth(self.view.button_min_width)
        #self.view.shortcut_button.clicked.connect(self.view.toggle_shortcuts)
        self.view.shortcut_button.setToolTip("Click to hide/show all label property dialogs or select specific ones.")
        button_row.addWidget(self.view.shortcut_button)
        
        button_row.addStretch(1)
        left_layout.addLayout(button_row)
        
        # Image display with dynamic sizing
        self.zoomable_graphics_view = ZoomableGraphicsView()
        self.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoomable_graphics_view.setStyleSheet("background-color: #ccc; border: 1px solid #000;")
        self.zoomable_graphics_view.setMinimumSize(self.view.image_container_width, self.view.image_container_height)
        left_layout.addWidget(self.zoomable_graphics_view, 1)  # Give it stretch priority
        
        self.view.main_layout.addWidget(left_layout_container, 4)  # Set stretch factor for image area

    
        

    def build_right_layout(self):
        
        self.right_layout_container = QWidget()
        self.right_layout_container.setMinimumWidth(self.view.control_panel_width)
        self.right_layout_container.setMaximumWidth(max(200, int(self.view.window_width * 0.15)))
        
        self.right_layout = QVBoxLayout(self.right_layout_container)
        self.right_layout.setSpacing(max(8, int(self.view.button_height * 0.2)))  # Fixed spacing for buttons
        
        self.build_move_tools()
        
        self.build_separator()

        
        self.build_layer_tools()
      
        
        self.right_layout.addStretch(1)
        self.view.main_layout.addWidget(self.right_layout_container, 1)  # Set appropriate stretch factor
        
            
        


    def build_move_tools(self):
          # Move Tools Section
        move_tools_label = QLabel("Move Tools")
        move_tools_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        self.right_layout.addWidget(move_tools_label)
        
        move_tools = [
            ("Move", None, True, "move"),
            ("Reset Move/zoom", None, False, "reset"),
        ]
        
        self.view.tool_buttons = {}
        
        for button_text, callback, checkable, icon_name in move_tools :
            button = QPushButton(button_text)  # Include text for better accessibility
            button.setFixedHeight(self.view.button_height)
            
            # Add scaled icon to button
            icon_path = Utils.get_icon_path(icon_name)
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(self.view.button_icon_size, self.view.button_icon_size))
            
            # Consistent padding based on button height
            padding = max(4, int(self.view.button_height * 0.1))
            border_radius = max(4, int(self.view.button_height * 0.1))
            
            # Enhanced styling with dynamic values but consistent minimums
            button.setStyleSheet(Utils.get_style_css())
            button.setStyleSheet(f"""QPushButton {{padding: {padding}px;padding-left: {padding * 2}px;padding-right: {padding * 2}px;}}""")
            button.setStyleSheet(f"""QPushButton {{border-radius: {border_radius}px;}}""")
            button.setStyleSheet(f"""QPushButton {{font-size: {self.view.base_font_size}pt;}}""")
            
            
            
            if checkable:
                button.setCheckable(True)
            
            # Set tooltip for Move tools with specific function explanation
            if button_text == "Move":
                button.setToolTip("Click to activate Move mode. This allows you to move the image around in the viewer by dragging it.")
            elif button_text == "Reset Move/zoom":
                button.setToolTip("Click to reset the image's position and zoom level to the default view.")
            
            #button.clicked.connect(callback)
            self.right_layout.addWidget(button)
            
            # Store reference in dictionary for easy access
            self.view.tool_buttons[button_text] = button

    def build_layer_tools(self):
        # Layer Tools Section
        layer_tools_label = QLabel("Layer Tools")
        layer_tools_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        self.right_layout.addWidget(layer_tools_label)
        
        layer_tools = [
            ("Undo", None, False, "back"),
            ("Opacity", None, False, "opacity"),
            ("Contour Filling", None, True, "fill"),
            ("Paintbrush", None, True, "paint"),
            ("Magic Pen", None, True, "magic"),
            ("Rectangle", None, True, "select"),
            ("Polygon", None, True, "polygon"),
            ("Eraser", None, True, "eraser"),
            ("Clear All", None, False, "cleaner"),
        ]
        
        for button_text, callback, checkable, icon_name in layer_tools :
            button = QPushButton(button_text)  # Include text for better accessibility
            button.setFixedHeight(self.view.button_height)
            
            # Add scaled icon to button
            icon_path = Utils.get_icon_path(icon_name)
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(self.view.button_icon_size, self.view.button_icon_size))
            
            # Consistent padding based on button height
            padding = max(4, int(self.view.button_height * 0.1))
            border_radius = max(4, int(self.view.button_height * 0.1))
            
            # Enhanced styling with dynamic values but consistent minimums
            button.setStyleSheet(Utils.get_style_css())
            button.setStyleSheet(f"""QPushButton {{padding: {padding}px;padding-left: {padding * 2}px;padding-right: {padding * 2}px;}}""")
            button.setStyleSheet(f"""QPushButton {{border-radius: {border_radius}px;}}""")
            button.setStyleSheet(f"""QPushButton {{font-size: {self.view.base_font_size}pt;}}""")
            
            
            if checkable:
                button.setCheckable(True)
            
            # Set tooltips for Layer tools with specific explanations
            if button_text == "Undo":
                button.setToolTip("Click to undo the last drawing action or modification.")
            elif button_text == "Opacity":
                button.setToolTip("Click to toggle opacity mode, allowing you to adjust the transparency of layers.")
            elif button_text == "Contour Filling":
                button.setToolTip("Click to activate contour filling mode, which lets you fill in outlines of objects.")
            elif button_text == "Paintbrush":
                button.setToolTip("Click to activate paintbrush mode, allowing you to draw freely on the image.")
            elif button_text == "Magic Pen":
                button.setToolTip("Click to activate the Magic Pen mode for drawing precise, automated strokes.")
            elif button_text == "Rectangle":
                button.setToolTip("Click to activate the rectangle select tool for creating rectangular selections.")
            elif button_text == "Polygon":
                button.setToolTip("Click to activate the polygon select tool for creating polygon selections.")
            elif button_text == "Eraser":
                button.setToolTip("Click to activate the eraser tool, allowing you to erase parts of the image or layer.")
            elif button_text == "Clear All":
                button.setToolTip("Click to clear all layers and reset the image to its original state.")
            
            #button.clicked.connect(callback)
            self.right_layout.addWidget(button)
            
            # Store reference in dictionary for easy access
            self.view.tool_buttons[button_text] = button
        

    def build_separator(self):
        self.right_layout.addSpacing(10)
        separator = QLabel("──────────────────")  # Fake visual separator
        separator.setStyleSheet("color: gray;")
        self.right_layout.addWidget(separator)
        

    def calculate_component_sizes(self):
        """Calculate dynamic sizes for UI components based on screen resolution"""
        
        # Dynamic grid cells
        self.view.cell_width = max(100, int(self.view.window_width / 10))
        self.view.cell_height = max(80, int(self.view.window_height / 10))
        
        # Dynamic image container size (scales with window)
        self.view.image_container_width = int(self.view.window_width * 0.75)
        self.view.image_container_height = int(self.view.window_height * 0.8)
        
        # Dynamic button sizes - ensure reasonable minimums
        self.view.button_height = max(40, int(self.view.window_height * 0.05))
        self.view.button_icon_size = max(24, int(self.view.button_height * 0.7))
        self.view.button_min_width = max(80, int(self.view.window_width * 0.06))
        
        # Control panel width - more adaptive
        self.view.control_panel_width = max(120, int(self.view.window_width * 0.12))
        
        # Dynamic spacing - more proportional to screen size
        self.view.layout_spacing = max(8, int(self.view.window_width * 0.008))
        
        