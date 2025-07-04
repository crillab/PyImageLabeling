# Model


from PyImageLabeling.model.File.LoadImage import LoadImage
from PyImageLabeling.model.File.SaveLayer import SaveLayer

from PyImageLabeling.model.Edit.ClearAll import ClearAll
from PyImageLabeling.model.Edit.Eraser import Eraser
from PyImageLabeling.model.Edit.HideShowLabelShortcut import HideShowLabelShortcut
from PyImageLabeling.model.Edit.Opacity import Opacity
from PyImageLabeling.model.Edit.Undo import Undo

from PyImageLabeling.model.Labeling.ContourFilling import ContourFilling
from PyImageLabeling.model.Labeling.MagicPen import MagicPen
from PyImageLabeling.model.Labeling.PaintBrush import PaintBrush
from PyImageLabeling.model.Labeling.Polygon import Polygon
from PyImageLabeling.model.Labeling.Rectangle import Rectangle

from PyImageLabeling.model.Tools.MoveImage import MoveImage
from PyImageLabeling.model.Tools.ResetMoveZoomImage import ResetMoveZoomImage
from PyImageLabeling.model.Tools.ZoomMinus import ZoomMinus
from PyImageLabeling.model.Tools.ZoomPlus import ZoomPlus

from PyImageLabeling.model.Layer.NewLayer import NewLayer
from PyImageLabeling.model.Layer.LoadLayers import LoadLayers

class Model(LoadImage, SaveLayer, ClearAll, Eraser, HideShowLabelShortcut, Opacity, Undo, ContourFilling, MagicPen, PaintBrush, Polygon, Rectangle, MoveImage, ResetMoveZoomImage, ZoomMinus, ZoomPlus, NewLayer, LoadLayers):
    def __init__(self, view, config):
        super().__init__()
        self.config = config
        self.set_view(view)

    def set_view(self, view):
        super().set_view(view)
        self.view = view
        

