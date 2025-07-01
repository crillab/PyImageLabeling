from PyImageLabeling.controller.Events import Events


class ToolsEvents(Events):
    def __init__(self):
        super().__init__()

    def move_image(self):
        self.all_events(self.move_image.__name__)
        print("move_image")
        
    def reset_move_zoom_image(self):
        self.all_events(self.reset_move_zoom_image.__name__)
        print("reset_move_zoom_image")



        
