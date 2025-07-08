
from PyImageLabeling.view.Builder import Builder
from PyImageLabeling.model.Utils import Utils

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF, QDateTime

import os

class View(QMainWindow):
    def __init__(self, controller, config):
        
        super().__init__()
        # Parameters
        self.controller = controller
        self.controller.set_view(self) 
        self.config = config

        #Components of the view 
        self.buttons_labeling_bar = dict()
        self.buttons_label_bar_permanent = dict()
        self.buttons_label_bar_temporary = dict()
        self.buttons_image_bar = dict()
        self.buttons_file_bar = dict()
        
        self.zoomable_graphics_view = None

        # Set the main properties of the view
        self.initialize()

        # Build the components of the view
        self.builder = Builder(self)
        self.builder.build()

        # Display
        self.show()

    # Here we are sure that clicked is checkable
    def desactivate_buttons(self, clicked, list_buttons_bars):
        for buttons_bar in list_buttons_bars:
            for button in buttons_bar.keys():
                # The button have not to be the same that clicked
                # The button have to be checked 
                # The clicked button have to be checkable 
                if button != clicked and buttons_bar[button].isChecked() is True:
                    buttons_bar[button].setChecked(False)


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

        
   