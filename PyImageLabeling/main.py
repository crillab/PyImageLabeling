from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.View import View
from PyImageLabeling.utils.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 

def __main__():
    config = Utils.get_config()
    app = QApplication(sys.argv)
    
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, config)
    controller.set_model(model)

    
    sys.exit(app.exec())

__main__()