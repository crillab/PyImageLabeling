
from PyImageLabeling.utils.FileEvents import FileEvents
from PyImageLabeling.utils.LabelingEvents import LabelingEvents
from PyImageLabeling.utils.ImageEvents import ImageEvents
from PyImageLabeling.utils.LabelEvents import LabelEvents


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
        