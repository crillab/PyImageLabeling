from  controller.Events import Events


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

    def ellipse(self):
        self.all_events(self.ellipse.__name__)
        print("ellipse")

    def rectangle(self):
        self.all_events(self.rectangle.__name__)
        print("rectangle")
    
    def polygon(self):
        self.all_events(self.polygon.__name__)
        print("polygon")

    def contour_filling_setting(self):
        self.all_events(self.contour_filling_setting.__name__)
        print("contour_filling_setting")
        
    def paintbrush_setting(self):
        self.all_events(self.paintbrush_setting.__name__)
        print("paintbrush_setting")
    
    def magic_pen_setting(self):
        self.all_events(self.magic_pen_setting.__name__)
        print("magic_pen_setting")

    def ellipse_setting(self):
        self.all_events(self.ellipse_setting.__name__)
        print("ellipse_setting")

    def rectangle_setting(self):
        self.all_events(self.rectangle_setting.__name__)
        print("rectangle_setting")
    
    def polygon_setting(self):
        self.all_events(self.polygon_setting.__name__)
        print("polygon_setting")
   
        
