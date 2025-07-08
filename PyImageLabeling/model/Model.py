# Model


from PyImageLabeling.model.File.LoadImage import LoadImage
from PyImageLabeling.model.File.SaveLayer import SaveLayer



from PyImageLabeling.model.Labeling.ContourFilling import ContourFilling
from PyImageLabeling.model.Labeling.MagicPen import MagicPen
from PyImageLabeling.model.Labeling.PaintBrush import PaintBrush
from PyImageLabeling.model.Labeling.Polygon import Polygon
from PyImageLabeling.model.Labeling.Rectangle import Rectangle
from PyImageLabeling.model.Labeling.ClearAll import ClearAll
from PyImageLabeling.model.Labeling.Eraser import Eraser
from PyImageLabeling.model.Labeling.Undo import Undo

from PyImageLabeling.model.Image.MoveImage import MoveImage
from PyImageLabeling.model.Image.ResetMoveZoomImage import ResetMoveZoomImage
from PyImageLabeling.model.Image.ZoomMinus import ZoomMinus
from PyImageLabeling.model.Image.ZoomPlus import ZoomPlus

from PyImageLabeling.model.Labels.LoadLabels import LoadLabels
from PyImageLabeling.model.Labels.Opacity import Opacity

class Model(LoadImage, SaveLayer, ClearAll, Eraser, Opacity, Undo, ContourFilling, MagicPen, PaintBrush, Polygon, Rectangle, MoveImage, ResetMoveZoomImage, ZoomMinus, ZoomPlus, LoadLabels):
    def __init__(self, view, config):
        super().__init__()
        self.config = config
        self.set_view(view)

    def set_view(self, view):
        super().set_view(view)
        self.view = view
        

