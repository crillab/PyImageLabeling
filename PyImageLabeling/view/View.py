
from PyImageLabeling.view.Builder import Builder
from PyImageLabeling.view.events.ManagerEvents import ManagerEvents
from PyImageLabeling.model.Utils import Utils

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF, QDateTime

import os

class View(QMainWindow):
    def __init__(self, config):
        
        super().__init__()
        self.config = config

        self.builder = Builder(self)
        self.manager_events = ManagerEvents()
        self.buttons = dict()

        self.initialize()
        self.builder.build()
        self.show()
        
    
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
        
        self.left_panel_width = int(self.window_width * 0.075)
        self.left_panel_height = int(self.window_height * 0.075)
        
        self.right_panel_width = int(self.window_width * 0.90)
        self.right_panel_height = int(self.window_height * 0.90)
        
        self.setWindowIcon(QIcon(Utils.get_icon_path("maia_icon")))

        self.setStyleSheet(Utils.get_style_css())
        
        
   