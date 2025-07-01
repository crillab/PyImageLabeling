from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 

def __main__():
    config = Utils.get_config()
    app = QApplication(sys.argv)
    view = View(config)
    model = Model(config)
    controller = Controller(model, view, config)
    
    sys.exit(app.exec())

__main__()