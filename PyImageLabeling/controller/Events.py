from PyQt6.QtWidgets import QMessageBox

from PyQt6.QtCore import QObject, QEvent, Qt

from PyQt6.QtGui import QPixmap, QMouseEvent, QKeyEvent

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer

import os

class eventEater(QObject):
    def __init__(self, controler, view, model):
        super().__init__()
        self.controler = controler
        self.view = view
        self.model = model
        self.zoom_timer = QTimer()
        self.zoom_timer.timeout.connect(self.continue_zoom)
        self.zoom_timer.setInterval(100)  
        self.current_zoom_action = None

        self.draw_timer = QTimer()
        self.draw_timer.timeout.connect(self.continue_draw)
        self.draw_timer.setInterval(50) # Update every 50ms for smoother drawing
        self.current_draw_pos = None

    def set_model(self, model):
        self.model = model

    def start_continuous_zoom(self, zoom_type):
        self.current_zoom_action = zoom_type
        if zoom_type == "zoom_plus":
            self.model.apply_zoom_plus()
        elif zoom_type == "zoom_minus":
            self.model.apply_zoom_minus()
        self.zoom_timer.start()

    def continue_zoom(self):
        if self.current_zoom_action == "zoom_plus":
            self.model.apply_zoom_plus()
        elif self.current_zoom_action == "zoom_minus":
            self.model.apply_zoom_minus()

    def stop_continuous_zoom(self):
        self.zoom_timer.stop()
        self.current_zoom_action = None

    def start_continuous_draw(self, pos):
        self.current_draw_pos = pos
        self.draw_timer.start()

    def continue_draw(self):
        if self.current_draw_pos and self.view.last_mouse_pos:
            self.model.draw_continuous_line(self.view.last_mouse_pos, self.current_draw_pos)

    def stop_continuous_draw(self):
        self.draw_timer.stop()
        self.current_draw_pos = None

    # Modified eventFilter method:
    def eventFilter(self, obj, event):
        #print("event.type():", event.type())
        #print("obj:", obj)
        if event.type() == QEvent.Type.Wheel:
            if hasattr(self.view, 'zoomable_graphics_view'):
                self.view.zoomable_graphics_view.wheelEvent(event)
            
        if event.type() == QEvent.Type.GraphicsSceneMousePress and event.button() == Qt.MouseButton.LeftButton:
            if self.model.checked_button == "zoom_plus":
                self.view.zoomable_graphics_view.change_cursor("zoom_plus")
                self.start_continuous_zoom("zoom_plus")
            elif self.model.checked_button == "zoom_minus":
                self.view.zoomable_graphics_view.change_cursor("zoom_minus")
                self.start_continuous_zoom("zoom_minus")
            elif self.model.checked_button == "move_image":
                self.view.zoomable_graphics_view.change_cursor("move")
                self.model.apply_move_image()
            elif self.model.checked_button == "paint_brush":
                self.view.scene_pos = event.scenePos()
                if self.view.last_mouse_pos:
                    self.view.zoomable_graphics_view.change_cursor("paint")
                    self.model.draw_continuous_line( self.view.scene_pos, self.view.last_mouse_pos)
                self.view.last_mouse_pos = self.view.scene_pos
                self.start_continuous_draw(self.view.scene_pos)
            
        elif event.type() == QEvent.Type.GraphicsSceneMouseRelease and event.button() == Qt.MouseButton.LeftButton: 
            if self.model.checked_button == "zoom_plus":
                self.view.zoomable_graphics_view.change_cursor("zoom_plus")
                self.stop_continuous_zoom()
            elif self.model.checked_button == "zoom_minus":
                self.view.zoomable_graphics_view.change_cursor("zoom_minus")
                self.stop_continuous_zoom()
            elif self.model.checked_button == "paint_brush":
                self.stop_continuous_draw()

        elif event.type() == QEvent.Type.GraphicsSceneMouseMove and event.button() == Qt.MouseButton.LeftButton: 
            if self.model.checked_button == "paint_brush":       
                self.view.zoomable_graphics_view.change_cursor("paint")
                self.view.scene_pos = event.scenePos()
                if  self.view.last_mouse_pos:
                     self.model.draw_continuous_line(self.view.last_mouse_pos, self.view.scene_pos)
                self.view.last_mouse_pos = self.view.scene_pos

        return True

class Events:

    def __init__(self):
        self.view = None
        self.model = None
        self.event_eater = None

    def set_view(self, view):
        self.view = view
        print("view:", view)
        self.event_eater = eventEater(self, self.view, self.model)
        self.view.zoomable_graphics_view.scene.installEventFilter(self.event_eater)
    
    def set_model(self, model):
        self.model = model
        self.event_eater.set_model(model)

    def all_events(self, event_name):
        #self.view.desactivate_buttons(event_name, [self.view.buttons_labeling_bar, self.view.buttons_image_bar])
        print("all_events")
    
    def desactivate_buttons_labeling_image_bar(self, event_name):
        self.view.desactivate_buttons(event_name, [self.view.buttons_labeling_bar, self.view.buttons_image_bar])
        
    def desactivate_buttons_label_bar(self, event_name):
        # Wihtout the visibility buttons
        buttons_bar = {key: self.view.buttons_label_bar_temporary[key] for key in self.view.buttons_label_bar_temporary.keys() if key.startswith("activation_")}
        
        self.view.desactivate_buttons(event_name, [buttons_bar])
    
    def error_message(self, title, text):
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("Error: "+str(title))
        msg_box.setText(text)
        msg_box.exec() 


        
