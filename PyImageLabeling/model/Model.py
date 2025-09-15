# Model


from model.File.Files import Files
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
from model.Labeling.Ellipse import Ellipse

from model.Image.MoveImage import MoveImage
from model.Image.ZoomMinus import ZoomMinus
from model.Image.ZoomPlus import ZoomPlus
from model.Image.ResetMoveZoomImage import ResetMoveZoomImage


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
        

