from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication
import sys 
import os
import PyImageLabeling

__version__ = "1.0.5"
__python_version__ = str(sys.version).split(os.linesep)[0].split(' ')[0]
__location__ = os.sep.join(PyImageLabeling.__file__.split(os.sep)[:-1])

def __main__():
    config = Utils.get_config()
    app = QApplication(sys.argv)
    
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, controller, config)
    controller.set_model(model)
    
    sys.exit(app.exec())

if sys.argv:
    if  (len(sys.argv) != 0 and sys.argv[0] == "-m"):
            print("Python version: ", __python_version__)
            print("PyImageLabeling version: ", __version__)
            print("PyImageLabeling location: ", __location__)

    if  (len(sys.argv) == 2 and sys.argv[0] == "-m" and sys.argv[1] == "-tests"):         
        #config = Utils.get_config()
        #app = QApplication(sys.argv)
        print("Tests ...")
        #controller = Controller(config)
        #view = View(controller, config)
        #model = Model(, controller, config)
        #controller.set_model(model)    
    else:
        __main__()


### Set like this to build the exec ###
# import sys
# # In PyImageLabeling/__init__.py
# def __main__():
#     # Your main application code here
#     sys.exit(app.exec())

# # Only run if this module is executed directly, not when imported
# if __name__ == "__main__":
#     __main__()