from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap, QPen
from PyQt6.QtCore import Qt, QSize
from PyImageLabeling.model.Core import Core

class Undo(Core):
    def __init__(self):
        super().__init__() 
    
    def undo(self):
        self.get_labeling_overlay().undo()
            
  