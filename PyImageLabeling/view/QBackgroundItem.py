
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QColor


class QBackgroundItem(QGraphicsItem):
    def __init__(self, rect, controller):
        super().__init__()
        self.rect = rect
        self.controller = controller
        
    def set_model(self, model):
        self.model = model

    def sceneEvent(self, event):
        #self.view.zoomable_graphics_view.setDragMode(QGraphicsView.DragMode.NoDrag)
        print("event.type() move good zone", event.type())
        return self.controller.event_eater.eventFilter(event)
    

    def boundingRect(self):
        return self.rect
    
    def paint(self, painter, option, widget):
        painter.setPen(QColor(139,161,255))
        painter.drawRect(self.rect)
        painter.fillRect(self.rect, QColor(255,255,255))