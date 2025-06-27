
from view.events.MainEvents import MainEvents
from view.events.MoveToolsEvents import MoveToolsEvents
from view.events.LayerToolsEvents import LayerToolsEvents

class ManagerEvents(MainEvents, MoveToolsEvents, LayerToolsEvents):

    def __init__(self):
        pass
