# Model


from PyImageLabeling.model.File.LoadImage import LoadImage
from PyImageLabeling.model.Layer.NewLayer import NewLayer
class Model(LoadImage, NewLayer):
    def __init__(self, view, config):
        super().__init__()
        self.config = config
        self.set_view(view)

    def set_view(self, view):
        super().set_view(view)
        self.view = view
        

