"""Build the app from the installed wheel, outside the source tree.

The test suite imports the sources; this catches what it cannot see: a data
file (config.json, icons, style.css, default_parameters.json) the wheel
forgot. Run it from a directory that does not contain PyImageLabeling/:

    cd /tmp && python /path/to/repo/.github/scripts/smoke_installed.py
"""
import os
import sys
from importlib.metadata import entry_points

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

import PyImageLabeling
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model
from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View

base = Utils.get_base_dir()
if "site-packages" not in base:
    sys.exit(f"PyImageLabeling imported from {base}, not from a wheel")

# same stack as __main__, without the event loop
app = QApplication([])
config = Utils.get_config()
controller = Controller(config)
view = View(controller, config)
model = Model(view, controller, config)
controller.set_model(model)
Utils.load_parameters()

# the `pyimagelabeling` command must point at a real function
entry_points(group="gui_scripts")["pyimagelabeling"].load()

print(f"PyImageLabeling {PyImageLabeling.__version__} builds from {base}")
