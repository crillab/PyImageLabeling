from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 

__version__ = "1.0.1"

def __main__():
    config = Utils.get_config()
    app = QApplication(sys.argv)
    
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, controller, config)
    controller.set_model(model)
    
    sys.exit(app.exec())

__main__()