
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
        
    

    def initialize(self):
        self.setWindowTitle("PyImageLabeling")
        self.label_properties_dialogs = []
        # Get screen information
        self.screen = QApplication.primaryScreen()
        self.screen_geometry = self.screen.availableGeometry()
        self.screen_width = self.screen_geometry.width()
        self.screen_height = self.screen_geometry.height()
        
        # Calculate dynamic window size based on screen dimensions
        self.window_width = int(self.screen_width * 0.85)  # Use 85% of screen width
        self.window_height = int(self.screen_height * 0.85)  # Use 85% of screen height
        
        # Set window position and size
        self.setGeometry(
            (self.screen_width - self.window_width) // 2,  # Center horizontally
            (self.screen_height - self.window_height) // 2,  # Center vertically
            self.window_width,
            self.window_height
        )
        
        # Icon
        self.setWindowIcon(QIcon(Utils.get_icon_path("maia2")))

        # Font scaling with better minimum
        self.base_font_size = max(9, int(self.window_width / 180))
        self.app_font = QFont()
        self.app_font.setPointSize(self.base_font_size)
        QApplication.setFont(self.app_font)

        
    