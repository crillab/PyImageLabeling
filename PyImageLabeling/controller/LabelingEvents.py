from PyImageLabeling.controller.Events import Events


class LabelingEvents(Events):
    def __init__(self):
        super().__init__()

    def contour_filling(self):
        self.all_events(self.contour_filling.__name__)
        print("contour_filling")
        
    def paintbrush(self):
        self.all_events(self.paintbrush.__name__)
        print("paintbrush")
    
    def magic_pen(self):
        self.all_events(self.magic_pen.__name__)
        print("magic_pen")

    def rectangle(self):
        self.all_events(self.rectangle.__name__)
        print("rectangle")
    
    def polygon(self):
        self.all_events(self.polygon.__name__)
        print("polygon")
   
        
