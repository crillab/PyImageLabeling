

from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsView


class MoveImage(Core):
    def __init__(self):
        super().__init__() 
    
    def move_image(self):
        self.checked_button = self.move_image.__name__

    def apply_move_image(self):
        self.view.zoomable_graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.zoomable_graphics_view.change_cursor("move")