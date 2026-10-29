from PyImageLabeling.model.Base import Base

class Undo(Base):
    def __init__(self):
        super().__init__() 
    
    def undo(self):
        self.get_current_image_item().get_labeling_overlay().undo()
            
  