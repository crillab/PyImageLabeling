from PyQt6.QtWidgets import QMessageBox

from PyQt6.QtCore import QObject, QEvent

from PyQt6.QtGui import QPixmap, QMouseEvent, QKeyEvent

from PyQt6.QtWidgets import QLabel
import os

class eventEater(QObject):
    def __init__(self, controler, view, model):
        super().__init__()
        self.controler = controler
        self.view = view
        self.model = model

    def set_model(self, model):
        self.model = model

    def eventFilter(self, obj, event):
        print("eventEater:", event.type())
        if self.model.checked_button == "zoom_plus":
            if event.type() == QEvent.Type.GraphicsSceneMousePress:
                print("QEvent.Type.GraphicsSceneMousePress")
                self.model.apply_zoom_plus()
                self.view.zoomable_graphics_view.change_cursor("zoom_plus")
                return True
            elif event.type() == 157:
                self.view.zoomable_graphics_view.change_cursor("zoom_plus")
            elif event.type() == 156:
                self.view.zoomable_graphics_view.change_cursor("zoom_plus")
        return True
        #else:
            # standard event processing
        #    return QObject.eventFilter(obj, event)

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
    
    def on_file_double_clicked(self, item):
        """Handle double-click on file list item to load the image"""
        # Get the custom widget for this item
        item_widget = self.view.file_bar_list.itemWidget(item)
        if item_widget:
            file_label = item_widget.findChild(QLabel)
            if file_label:
                filename = file_label.text()
                matching_path = None
                for path in self.model.loaded_image_paths:
                    if os.path.basename(path) == filename:
                        matching_path = path
                        break
                if matching_path:
                    image = QPixmap(matching_path)
                    if not image.isNull():
                        self.model.load_image(image)
                        self.view.file_bar_list.setCurrentItem(item)
                        print(f"Loaded image: {filename}")
                    else:
                        print(f"Error: Could not load image {filename}")
                else:
                    print(f"Error: Could not find path for {filename}")

    def error_message(self, title, text):
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("Error: "+str(title))
        msg_box.setText(text)
        msg_box.exec() 


        
