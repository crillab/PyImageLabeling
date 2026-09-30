
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QColor


class QBackgroundItem(QGraphicsItem):
    def __init__(self, rect, controller, alpha_color):
        super().__init__()
        self.rect = rect
        self.controller = controller
        self.background_color = QColor(*alpha_color)
    
    def set_model(self, model):
        self.model = model

    def sceneEvent(self, event):
        return self.controller.event_eater.eventFilter(event)
    
    def boundingRect(self):
        return self.rect
    def paint(self, painter, option, widget):
        painter.fillRect(self.rect, self.background_color)
        