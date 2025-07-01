# Model


from PyImageLabeling.model.File.LoadImage import LoadImage

class Model(LoadImage):
    def __init__(self, view, config):
        super().__init__(view)
        self.view = view
        self.config = config

    
        

