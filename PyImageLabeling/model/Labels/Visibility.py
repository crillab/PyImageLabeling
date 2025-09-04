from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Core import Core

class Visibility(Core):
    def __init__(self):
        super().__init__()

    def visibility(self, label):
        """Set the visibility of all drawings and overlays on the canvas"""

        print("visibility mode:", label)
        self.labeling_overlays[label].change_visible()
