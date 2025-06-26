
from PyImageLabeling.view.events.MainEvents import MainEvents
from PyImageLabeling.view.events.MoveToolsEvents import MoveToolsEvents
from PyImageLabeling.view.events.LayerToolsEvents import LayerToolsEvents

class ManagerEvents(MainEvents, MoveToolsEvents, LayerToolsEvents):

    def __init__(self):
        pass
