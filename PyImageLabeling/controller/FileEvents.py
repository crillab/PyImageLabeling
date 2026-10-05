
from PyQt6.QtWidgets import QMessageBox

from PyImageLabeling.controller.Events import Events
from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model import Autosave



class FileEvents(Events):
    def __init__(self):
        super().__init__()
        
    def set_view(self, view):
        super().set_view(view)

    def set_model(self, model):
        super().set_model(model)
        
    def load(self):
        self.all_events(self.load.__name__)
        self.model.load()
        for button_names in self.view.buttons_image_bar:
            self.view.buttons_image_bar[button_names].setEnabled(True)
        for button_names in self.view.buttons_label_bar_permanent:
            self.view.buttons_label_bar_permanent[button_names].setEnabled(True)
        
        self.move_image() # we active the move button :) 
        self.model.update_icon_file()


    def save(self):
        self.model.save()

    def save_copy(self):
        self.model.save()
        self.model.save_copy()

    def recover_annotations(self, info=None):
        """Restore the auto-save snapshot when it is newer than the project.

        File > Recover Unsaved Annotations. Without this the snapshot
        written every few minutes was dead weight: after a native crash the
        only way back was to copy <project>/auto_save/ by hand.
        """
        project_dir = ""
        if info is None:
            project_dir = getattr(self.model, "save_directory", "") or ""
            if not project_dir:
                data = Utils.load_parameters()
                project_dir = (data.get("save", {}) or {}).get("path", "") or ""
        else:
            project_dir = info.get("project_dir", "")

        if not project_dir or not Autosave.needs_recovery(project_dir):
            QMessageBox.information(
                self.view, "Nothing to recover",
                "No auto-save snapshot newer than the project files was "
                "found.\n\nAuto-save writes a snapshot every few minutes; "
                "it is offered here and at startup only when it holds work "
                "the project files do not have yet.")
            return False

        answer = QMessageBox.question(
            self.view, "Recover unsaved annotations?",
            Autosave.describe(project_dir) +
            "\n\nRestore it over the project files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return False

        restored = Autosave.restore(project_dir)
        QMessageBox.information(
            self.view, "Annotations recovered",
            f"{len(restored)} file(s) restored from the auto-save "
            f"snapshot.\n\nReopen your project (File > Load) to see them.")
        return True


    def select_image(self, item):
        self.model.select_image(item.file_path)

        if self.model.get_current_label_item() is not None:
            self.model.update_labeling_overlays(self.model.get_current_label_item().get_label_id())

        # avoid re-entrant selection signals (we may already be inside an
        # itemSelectionChanged emission from the file bar)
        try:
            if self.view.file_bar_list.currentItem() is not item:
                self.view.file_bar_list.setCurrentItem(item)
        except Exception:
            pass
        self.model.update_icon_file()

    def next_image(self):
        self.all_events(self.next_image.__name__)
        self.model.next_image()

    def previous_image(self):
        self.all_events(self.previous_image.__name__)
        self.model.previous_image()
