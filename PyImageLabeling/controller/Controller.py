
from PyImageLabeling.controller.FileEvents import FileEvents
from PyImageLabeling.controller.EditEvents import EditEvents
from PyImageLabeling.controller.LabelingEvents import LabelingEvents
from PyImageLabeling.controller.ToolsEvents import ToolsEvents


class Controller(FileEvents, EditEvents, LabelingEvents, ToolsEvents):
    def __init__(self, config):
        super().__init__()
        
        self.config = config
        self.view = None
    
    def set_view(self, view):
        super().set_view(view)
        self.view = view