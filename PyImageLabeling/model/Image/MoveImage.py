from PyImageLabeling.model.Core import Core
from PyQt6.QtWidgets import QGraphicsView

class MoveImage(Core):
    def __init__(self):
        super().__init__()
        self.move_tool_activation = False
        self.last_cursor = None
        self.last_mouse_pos = None

    def move_image(self):
        self.checked_button = self.move_image.__name__

    def start_move_tool(self, event):
        view = self.view.zoomable_graphics_view

        self.last_cursor = view.viewport().cursor()
        view.change_cursor("move")

        # QGraphicsSceneMouseEvent → use screen position
        self.last_mouse_pos = event.screenPos()
        self.move_tool_activation = True

    def move_move_tool(self, event):
        if not self.move_tool_activation:
            return

        view = self.view.zoomable_graphics_view

        # Delta in screen pixels (stable regardless of zoom)
        delta = event.screenPos() - self.last_mouse_pos
        self.last_mouse_pos = event.screenPos()

        view.horizontalScrollBar().setValue(
            view.horizontalScrollBar().value() - delta.x()
        )
        view.verticalScrollBar().setValue(
            view.verticalScrollBar().value() - delta.y()
        )

    def end_move_tool(self):
        view = self.view.zoomable_graphics_view

        view.viewport().setCursor(self.last_cursor)
        self.move_tool_activation = False