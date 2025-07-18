from PyQt6.QtWidgets import QMessageBox, QGraphicsView, QApplication
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

        self.middle_mouse_pressed = False
        
        # Zoom timer setup
        self.zoom_timer = QTimer()
        self.zoom_timer.timeout.connect(self.continue_zoom)
        self.zoom_timer.setInterval(100)  
        self.current_zoom_action = None

        # Drawing state management
        self.is_drawing = False
        self.last_draw_pos = None
        self.min_draw_distance = 2.0  # Minimum distance between points
        
        # Optional: Throttle drawing updates
        self.draw_timer = QTimer()
        self.draw_timer.timeout.connect(self.process_pending_draw)
        self.draw_timer.setInterval(16) 
        self.pending_draw_pos = None

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

    def start_drawing(self, pos):
        """Start a new drawing stroke"""
        self.is_drawing = True
        self.last_draw_pos = pos
        
        self.model.add_point(pos)

    def continue_drawing(self, pos):
        """Continue the current drawing stroke"""
        if not self.is_drawing or self.last_draw_pos is None:
            return
            
        distance = ((pos.x() - self.last_draw_pos.x()) ** 2 + 
                   (pos.y() - self.last_draw_pos.y()) ** 2) ** 0.5
        
        if distance < self.min_draw_distance:
            return  

        else:
            self.process_draw_to_position(pos)

    def process_draw_to_position(self, pos):
        self.model.continue_stroke(pos)
        self.last_draw_pos = pos

    def process_pending_draw(self):
        if self.pending_draw_pos is not None:
            self.process_draw_to_position(self.pending_draw_pos)
            self.pending_draw_pos = None

    def stop_drawing(self):
        """Stop the current drawing stroke"""
        self.is_drawing = False
        self.last_draw_pos = None
        self.pending_draw_pos = None
        self.model.end_stroke()

    def eventFilter(self, obj, event):
        self.view.zoomable_graphics_view.setDragMode(QGraphicsView.DragMode.NoDrag)
            
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
                self.view.last_mouse_pos = event.scenePos()
                self.view.scene_pos = self.view.last_mouse_pos
                self.view.zoomable_graphics_view.change_cursor("paint")
                self.start_drawing(self.view.scene_pos)
                
        elif event.type() == QEvent.Type.GraphicsSceneMousePress and event.button() == Qt.MouseButton.RightButton:
            self.view.zoomable_graphics_view.change_cursor("move")
            self.middle_mouse_pressed = True
            self.last_mouse_pos = event.scenePos()

        elif event.type() == QEvent.Type.GraphicsSceneMouseMove and self.middle_mouse_pressed:
            delta = event.scenePos() - self.last_mouse_pos
            self.last_mouse_pos = event.scenePos()
            
            if self.view.zoomable_graphics_view.horizontalScrollBar().value() - int(delta.x()*10) >= 0:
                self.view.zoomable_graphics_view.horizontalScrollBar().setValue(self.view.zoomable_graphics_view.horizontalScrollBar().value() - int(delta.x()*10))
            if self.view.zoomable_graphics_view.horizontalScrollBar().value() - int(delta.y()*10) >= 0:
                self.view.zoomable_graphics_view.verticalScrollBar().setValue(self.view.zoomable_graphics_view.verticalScrollBar().value() - int(delta.y()*10))

        elif event.type() == QEvent.Type.GraphicsSceneMouseRelease and event.button() == Qt.MouseButton.RightButton:
            self.view.zoomable_graphics_view.change_cursor("move")
            self.middle_mouse_pressed = False

        elif event.type() == QEvent.Type.GraphicsSceneMouseRelease and event.button() == Qt.MouseButton.LeftButton: 
            if self.model.checked_button == "zoom_plus":
                self.view.zoomable_graphics_view.change_cursor("zoom_plus")
                self.stop_continuous_zoom()
            elif self.model.checked_button == "zoom_minus":
                self.view.zoomable_graphics_view.change_cursor("zoom_minus")
                self.stop_continuous_zoom()
            elif self.model.checked_button == "paint_brush":
                # Stop drawing stroke
                self.stop_drawing()
            elif self.model.checked_button == "move_image":
                self.view.zoomable_graphics_view.change_cursor("move")

        elif event.type() == QEvent.Type.GraphicsSceneMouseMove and event.buttons() == Qt.MouseButton.LeftButton: 
            if self.model.checked_button == "paint_brush":
                self.view.last_mouse_pos = event.scenePos()
                self.view.scene_pos = self.view.last_mouse_pos
                self.view.zoomable_graphics_view.change_cursor("paint")
                # Continue drawing stroke instead of starting new timer
                self.continue_drawing(self.view.scene_pos)
        

        if event.type() == QEvent.Type.Wheel and event.angleDelta().y() != 0:
            if QApplication.mouseButtons() & Qt.MiddleButton:
                return False  
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
        print("view:", view)
        self.event_eater = eventEater(self, self.view, self.model)
        self.view.zoomable_graphics_view.scene.installEventFilter(self.event_eater)
    
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