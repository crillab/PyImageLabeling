from PyQt6.QtWidgets import QMessageBox

class Events:

    def __init__(self):
        pass

    def set_view(self, view):
        self.view = view
    
    def set_model(self, model):
        self.model = model

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


        
