from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 

def __main__():
    app = QApplication(sys.argv)
    view = View()
    model = Model()
    controller = Controller(model, view)
    view.show()
    sys.exit(app.exec())

__main__()