from PyQt6.QtWidgets import QMessageBox, QGraphicsView, QApplication, QGraphicsItem
from PyQt6.QtCore import QObject, QEvent, Qt, QRectF, QRect
from PyQt6.QtGui import QPixmap, QMouseEvent, QKeyEvent, QBrush, QColor
from PyQt6.QtWidgets import QLabel
import os

from PyImageLabeling.model.Utils import Utils




class eventEater(QObject):
    def __init__(self, controler, view, model):
        super().__init__()
        self.controler = controler
        self.view = view
        self.model = model

    def set_model(self, model):
        self.model = model

    def eventFilter(self, event):
        #self.view.zoomable_graphics_view.setDragMode(QGraphicsView.DragMode.NoDrag)
        #print("event.type() QObject", event.type())
        #print("event.type() QObject", obj)
        
        if event.type() == QEvent.Type.GraphicsSceneMousePress and event.button() == Qt.MouseButton.LeftButton:
            if self.model.checked_button == "zoom_plus":
                self.model.start_zoom_plus()
            elif self.model.checked_button == "zoom_minus":
                self.model.start_zoom_minus()
            elif self.model.checked_button == "move_image":
                self.model.start_move_tool(event)
            elif self.model.checked_button == "paint_brush":
                self.model.start_paint_brush(event.scenePos())
            elif self.model.checked_button == "magic_pen":
                self.model.start_magic_pen(event.scenePos())
            elif self.model.checked_button == "contour_filling":
                # Fill the contour clicked
                self.model.fill_contour(event.scenePos())
            elif self.model.checked_button == "eraser":
                self.model.start_eraser(event.scenePos())

        elif event.type() == QEvent.Type.GraphicsSceneMouseMove and event.buttons() == Qt.MouseButton.LeftButton: 
            if self.model.checked_button == "paint_brush":
                self.model.move_paint_brush(event.scenePos())
            elif self.model.checked_button == "move_image":
                self.model.move_move_tool(event)
            elif self.model.checked_button == "eraser":
                self.model.move_eraser(event.scenePos())
                

        elif event.type() == QEvent.Type.GraphicsSceneMouseRelease and event.button() == Qt.MouseButton.LeftButton: 
            if self.model.checked_button == "paint_brush":
                self.model.end_paint_brush()
            elif self.model.checked_button == "move_image":
                self.model.end_move_tool()
            elif self.model.checked_button == "contour_filling":
                self.model.end_contour_filling()
            elif self.model.checked_button == "magic_pen":
                
                self.view.zoomable_graphics_view.change_cursor("magic")
            elif self.model.checked_button == "eraser":
                self.model.end_eraser()

        #elif event.type() == QEvent.Type.GraphicsSceneMousePress and event.button() == Qt.MouseButton.RightButton:
        #    if self.model.checked_button == "contour_filling":
        #        if self.view.layer_activation == True :
        #            self.model.fill_contour(event.scenePos())
        
        #MouseButton.MiddleButton: move tool
        elif event.type() == QEvent.Type.GraphicsSceneMousePress and event.button() == Qt.MouseButton.MiddleButton:
            self.model.start_move_tool(event)
        elif event.type() == QEvent.Type.GraphicsSceneMouseMove:
            self.model.move_move_tool(event)
        elif event.type() == QEvent.Type.GraphicsSceneMouseRelease and event.button() == Qt.MouseButton.MiddleButton:
            self.model.end_move_tool()

        #MouseButton.MiddleButton: zoom tool
        elif event.type() == QEvent.Type.Wheel and self.model.move_tool_activation == False:
            #if QApplication.mouseButtons() & Qt.MiddleButton:
            #    return False  
            if hasattr(self.view, 'zoomable_graphics_view'):
                self.view.zoomable_graphics_view.wheelEvent(event)

        return True

class Events:
    def __init__(self):
        self.view = None
        self.model = None
        self.event_eater = None

    def set_view(self, view):
        self.view = view
        self.event_eater = eventEater(self, self.view, self.model)
        #self.view.zoomable_graphics_view.scene.installEventFilter(self.event_eater)
    
    def set_model(self, model):
        self.model = model
        self.event_eater.set_model(model)

    def all_events(self, event_name):
        print("all_events")
    
    def desactivate_buttons_labeling_image_bar(self, event_name):
        self.view.desactivate_buttons(event_name, [self.view.buttons_labeling_bar, self.view.buttons_image_bar])
        
    def desactivate_buttons_label_bar(self, event_name):
        buttons_bar = {key: self.view.buttons_label_bar_temporary[key] for key in self.view.buttons_label_bar_temporary.keys() if key.startswith("activation_")}
        self.view.desactivate_buttons(event_name, [buttons_bar])
    
    def error_message(self, title, text):
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("Error: "+str(title))
        msg_box.setText(text)
        msg_box.exec()