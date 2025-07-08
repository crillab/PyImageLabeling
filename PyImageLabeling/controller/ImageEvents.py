from  controller.Events import Events


class ImageEvents(Events):
    def __init__(self):
        super().__init__()

    def zoom_plus(self):
        self.desactivate_buttons_labeling_image_bar(self.zoom_plus.__name__)
        self.all_events(self.zoom_plus.__name__)
        print("zoom_plus")

    def zoom_minus(self):
        self.desactivate_buttons_labeling_image_bar(self.zoom_minus.__name__)
        self.all_events(self.zoom_minus.__name__)
        print("zoom_minus")

    def move_image(self):
        self.desactivate_buttons_labeling_image_bar(self.move_image.__name__)
        self.all_events(self.move_image.__name__)
        print("move_image")
        
    def reset_move_zoom_image(self):
        self.all_events(self.reset_move_zoom_image.__name__)
        print("reset_move_zoom_image")



        
