from PyImageLabeling.model.Core import Core

class Undo(Core):
    def __init__(self):
        super().__init__() 
    
    def undo(self):
        self.get_current_image_item().get_labeling_overlay().undo()
            
  