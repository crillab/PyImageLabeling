from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 
import os
import PyImageLabeling

__version__ = Utils.get_version()
__python_version__ = str(sys.version).split(os.linesep)[0].split(' ')[0]
__location__ = os.sep.join(PyImageLabeling.__file__.split(os.sep)[:-1])

try:
    from PyImageLabeling.model.SAM.debug_log import install_excepthook
    install_excepthook()
except Exception:
    pass

def __main__():
    config = Utils.get_config()
    app = QApplication(sys.argv)
    
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, controller, config)
    controller.set_model(model)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    __main__()