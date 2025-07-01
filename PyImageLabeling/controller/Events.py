from PyQt6.QtWidgets import QMessageBox

class Events:

    def __init__(self):
        pass

    def set_view(self, view):
        self.view = view

    def all_events(self, event_name):
        self.view.desactivate_buttons(event_name)
        print("all_events")

    def error_message(self, title, text):
        msg_box = QMessageBox(self.view)
        msg_box.setWindowTitle("Error: "+str(title))
        msg_box.setText(text)
        msg_box.exec() 


        
