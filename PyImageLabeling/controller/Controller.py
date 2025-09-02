
from controller.FileEvents import FileEvents
from controller.LabelingEvents import LabelingEvents
from controller.ImageEvents import ImageEvents
from controller.LabelEvents import LabelEvents


class Controller(FileEvents, LabelingEvents, ImageEvents, LabelEvents):
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        self.view = None
        self.model = None

    def set_view(self, view):
        super().set_view(view)
        self.view = view

    def set_model(self, model):
        super().set_model(model)
        self.model = model
        