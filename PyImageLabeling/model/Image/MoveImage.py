

from PyImageLabeling.model.Core import Core

class MoveImage(Core):
    def __init__(self):
        super().__init__() 
    
    def move_image(self):
        self.checked_button = self.move_image.__name__

    def apply_move_image(self):
        print("apply_move_image")