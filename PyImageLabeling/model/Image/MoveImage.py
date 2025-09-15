

from model.Core import Core
from PyQt6.QtWidgets import QGraphicsView


class MoveImage(Core):
    def __init__(self):
        super().__init__() 
        self.move_tool_activation = False 
        self.last_cursor = None
        
    def move_image(self):
        self.checked_button = self.move_image.__name__

    def start_move_tool(self, event):
        self.last_cursor = self.view.zoomable_graphics_view.viewport().cursor()
        self.view.zoomable_graphics_view.change_cursor("move")
        self.last_mouse_pos = event.scenePos()
        self.move_tool_activation = True
        

    def move_move_tool(self, event):
        if self.move_tool_activation is True:
            self.view.zoomable_graphics_view.horizontalScrollBar().setValue(int(self.view.zoomable_graphics_view.horizontalScrollBar().value() - (event.scenePos().x() - self.last_mouse_pos.x())))
            self.view.zoomable_graphics_view.verticalScrollBar().setValue(int(self.view.zoomable_graphics_view.verticalScrollBar().value() - (event.scenePos().y() - self.last_mouse_pos.y())))
        
    def end_move_tool(self):
        self.view.zoomable_graphics_view.change_cursor("move")
        self.view.zoomable_graphics_view.viewport().setCursor(self.last_cursor)
        self.move_tool_activation = False
        