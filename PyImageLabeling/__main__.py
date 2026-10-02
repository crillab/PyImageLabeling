from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model

from PyQt6.QtWidgets import QApplication, QMessageBox
import sys

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

    try:
        from PyImageLabeling.model.SAM import crash_report
        has_new, n_new = crash_report.check_new_crashes()
        if has_new:
            answer = QMessageBox.question(
                view, "Crash recorded",
                f"{n_new} crash(es) were recorded since your last session.\n"
                "Open the crash report?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                controller.crash_report()
            crash_report.save_seen()
    except Exception:
        pass

    sys.exit(app.exec())

if __name__ == "__main__":
    __main__()