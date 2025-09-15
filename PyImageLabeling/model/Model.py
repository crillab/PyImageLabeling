# Model


from PyImageLabeling.model.File.Files import Files
from PyImageLabeling.model.File.NextImage import NextImage
from PyImageLabeling.model.File.PreviousImage import PreviousImage

from PyImageLabeling.model.Labeling.ContourFilling import ContourFilling
from PyImageLabeling.model.Labeling.MagicPen import MagicPen
from PyImageLabeling.model.Labeling.PaintBrush import PaintBrush
from PyImageLabeling.model.Labeling.Polygon import Polygon
from PyImageLabeling.model.Labeling.Rectangle import Rectangle
from PyImageLabeling.model.Labeling.ClearAll import ClearAll
from PyImageLabeling.model.Labeling.Eraser import Eraser
from PyImageLabeling.model.Labeling.Undo import Undo
from PyImageLabeling.model.Labeling.Ellipse import Ellipse

from PyImageLabeling.model.Image.MoveImage import MoveImage
from PyImageLabeling.model.Image.ZoomMinus import ZoomMinus
from PyImageLabeling.model.Image.ZoomPlus import ZoomPlus
from PyImageLabeling.model.Image.ResetMoveZoomImage import ResetMoveZoomImage


class Model(Files, NextImage, PreviousImage, ClearAll, Eraser, Undo, ContourFilling, MagicPen, PaintBrush, Polygon, Rectangle, Ellipse, MoveImage, ZoomMinus, ZoomPlus, ResetMoveZoomImage):
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
        

