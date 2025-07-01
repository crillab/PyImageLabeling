
from PyImageLabeling.controller.Events import Events

class EditEvents(Events):
    def __init__(self):
        super().__init__()
    
    def undo(self):
        self.all_events(self.undo.__name__)
        print("undo")
        
    def eraser(self):
        self.all_events(self.eraser.__name__)
        print("eraser")
    
    def clear_all(self):
        self.all_events(self.clear_all.__name__)
        print("clear_all")

    def hide_show_label_shortcut(self):
        self.all_events(self.hide_show_label_shortcut.__name__)
        print("hide_show_label_shortcut")
    
    def opacity(self):
        self.all_events(self.opacity.__name__)
        print("opacity")
   
        
