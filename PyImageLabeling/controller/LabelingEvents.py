from  controller.Events import Events


class LabelingEvents(Events):
    def __init__(self):
        super().__init__()

    ### Buttons events

    def contour_filling(self):
        self.desactivate_buttons_labeling_image_bar(self.contour_filling.__name__)
        self.all_events(self.contour_filling.__name__)
        print("contour_filling")
        
    def paintbrush(self):
        self.desactivate_buttons_labeling_image_bar(self.paintbrush.__name__)
        self.all_events(self.paintbrush.__name__)
        self.model.paint_brush()
        print("paintbrush")
    
    def magic_pen(self):
        self.desactivate_buttons_labeling_image_bar(self.magic_pen.__name__)
        self.all_events(self.magic_pen.__name__)
        print("magic_pen")

    def ellipse(self):
        self.desactivate_buttons_labeling_image_bar(self.ellipse.__name__)
        self.all_events(self.ellipse.__name__)
        print("ellipse")

    def rectangle(self):
        self.desactivate_buttons_labeling_image_bar(self.rectangle.__name__)
        self.all_events(self.rectangle.__name__)
        print("rectangle")
    
    def polygon(self):
        self.desactivate_buttons_labeling_image_bar(self.polygon.__name__)
        self.all_events(self.polygon.__name__)
        print("polygon")

    def undo(self):
        self.all_events(self.undo.__name__)
        print("undo")
        
    def eraser(self):
        self.desactivate_buttons_labeling_image_bar(self.eraser.__name__)
        self.all_events(self.eraser.__name__)
        print("eraser")
    
    def clear_all(self):
        self.all_events(self.clear_all.__name__)
        print("clear_all")

    ### Setting Buttons events

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
   
    def eraser_setting(self):
        self.all_events(self.eraser_setting.__name__)
        print("eraser_setting")
   
