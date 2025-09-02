# Model


from model.File.LoadImage import LoadImage
from model.File.NextImage import NextImage
from model.File.PreviousImage import PreviousImage

from model.Labeling.ContourFilling import ContourFilling
from model.Labeling.MagicPen import MagicPen
from model.Labeling.PaintBrush import PaintBrush
from model.Labeling.Polygon import Polygon
from model.Labeling.Rectangle import Rectangle
from model.Labeling.ClearAll import ClearAll
from model.Labeling.Eraser import Eraser
from model.Labeling.Undo import Undo

from model.Image.MoveImage import MoveImage
from model.Image.ZoomMinus import ZoomMinus
from model.Image.ZoomPlus import ZoomPlus
from model.Image.ResetMoveZoomImage import ResetMoveZoomImage

from model.Labels.LoadLabels import LoadLabels
from model.Labels.Opacity import Opacity
from model.Labels.Visibility import Visibility
from model.Labels.SaveLayer import SaveLayer

class Model(LoadImage, NextImage, PreviousImage, SaveLayer, ClearAll, Eraser, Opacity, Visibility, Undo, ContourFilling, MagicPen, PaintBrush, Polygon, Rectangle, MoveImage, ZoomMinus, ZoomPlus, ResetMoveZoomImage, LoadLabels):
    def __init__(self, view, controller, config):
        super().__init__()
        self.config = config
        self.set_view(view)
        self.set_controller(controller)
        

    def set_view(self, view):
        super().set_view(view)
        self.view = view

    def set_controller(self, controller):
        super().set_controller(controller)
        self.controller = controller
        

