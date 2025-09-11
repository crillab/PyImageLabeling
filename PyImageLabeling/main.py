from model.Utils import Utils
from view.View import View
from controller.Controller import Controller
from model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 

def __main__():
    config = Utils.get_config()
    app = QApplication(sys.argv)
    
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, controller, config)
    controller.set_model(model)


    
    sys.exit(app.exec())

__main__()