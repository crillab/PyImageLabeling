


from PyQt6.QtCore import Qt, QFileInfo
from PyQt6.QtWidgets import QFileDialog, QProgressDialog, QMessageBox

from PyImageLabeling.model.Base import Base
from PyImageLabeling.model.LabelItem import LabelItem
from PyImageLabeling.model.Masks import (KEYWORD_SAVE_LABEL,
                                        IMAGE_EXTENSIONS,
                                        image_base_from_mask_name)
from PyImageLabeling.model.Utils import Utils

import numpy as np
import os
import shutil

from PyImageLabeling.logging_setup import get_logger
log = get_logger("files")

# Subfolders listed in the "nothing to load" message, at most.
_MAX_SUBFOLDERS_LISTED = 10


def _is_image_name(name):
    return name.lower().endswith(IMAGE_EXTENSIONS) \
        and KEYWORD_SAVE_LABEL not in name


# Files that make a folder a project (besides images and masks).
PROJECT_FILES = ("labels.json", "Rectangles.json", "Ellipses.json",
                 "Polygons.json", "complete_state.json")


def _is_empty_json(path):
    """True for a readable JSON file holding {}: a project with no label
    yet (a new project saved before its first label)."""
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) == {}
    except (OSError, ValueError):
        return False


def _subfolders_with_images(folder):
    """Names of the direct subfolders of `folder` holding an image."""
    found = []
    try:
        entries = sorted(os.scandir(folder), key=lambda e: e.name.lower())
    except OSError:
        return found
    for entry in entries:
        try:
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            with os.scandir(entry.path) as children:
                if any(c.is_file() and _is_image_name(c.name)
                       for c in children):
                    found.append(entry.name)
        except OSError:
            continue
    return found


def nothing_to_load_message(folder):
    """Explain why `folder` cannot be opened: it holds no image.

    Points at the subfolders that do have images, since only the selected
    folder itself is scanned, not its subfolders.
    """
    folder = os.path.normpath(folder)
    message = f"No image found in this folder:\n{folder}"
    subfolders = _subfolders_with_images(folder)
    if subfolders:
        shown = subfolders[:_MAX_SUBFOLDERS_LISTED]
        message += ("\n\nSubfolders are not opened automatically, but "
                    "these ones contain images:\n"
                    + "\n".join(f"  • {name}" for name in shown))
        if len(subfolders) > len(shown):
            message += f"\n  … and {len(subfolders) - len(shown)} more"
        message += "\n\nOpen one of them instead."
    else:
        message += ("\n\nSupported formats: "
                    + ", ".join(e[1:] for e in IMAGE_EXTENSIONS) + ".")
    return message


class Files(Base):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def select_image(self, path_image):
        #remove all overlays#
        super().select_image(path_image)
        
    def save(self):
        if self.save_directory == "":
            # Open a directory        
            self.default_path_save = Utils.load_parameters()["save"]["path"]
            
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
            dialog.setOption(QFileDialog.Option.ReadOnly, False)  
            dialog.setDirectory(self.default_path_save)
            
            def check_selection(path):
                info = QFileInfo(path)
                if info.isFile():
                    self.default_path = info.absolutePath()
                    data = Utils.load_parameters()
                    data["save"]["path"] = self.default_path
                    Utils.save_parameters(data)
                    dialog.done(0)  
                    self.controller.error_message("Load Error", "You can not select a file, chose a folder !")
                    self.load()
                    
            dialog.currentChanged.connect(check_selection)
            dialog.setModal(True)
            if dialog.exec() == 0: return 
            
            self.default_path_save = dialog.selectedFiles()[0]
            current_file_path = self.default_path_save
            
            if len(current_file_path) == 0: return

            data = Utils.load_parameters()
            data["save"]["path"] = current_file_path
            Utils.save_parameters(data)
            self.save_directory = current_file_path
            self.show_project_in_title()

        super().save()

    def save_copy(self):
        if not self.save_directory or not os.path.exists(self.save_directory):
            self.controller.error_message("Save Copy Error", "No save directory found. Please save your project first.")
            return
        
        default_path_save_copy = Utils.load_parameters()["save"]["path"]
        
        # Open directory selection dialog
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
        dialog.setOption(QFileDialog.Option.ReadOnly, False)  
        dialog.setDirectory(default_path_save_copy)
        dialog.setWindowTitle("Select Directory to Save Copy")
        
        def check_selection(path):
            info = QFileInfo(path)
            if info.isFile():
                dialog.done(0)  
                self.controller.error_message("Save Copy Error", "You cannot select a file, choose a folder!")
                self.save_copy()  # Retry
                
        dialog.currentChanged.connect(check_selection)
        dialog.setModal(True)
        
        if dialog.exec() == 0: 
            return 
        
        # Get the selected directory
        selected_directories = dialog.selectedFiles()
        if len(selected_directories) == 0 or len(selected_directories[0]) == 0:
            return
        
        copy_directory = selected_directories[0]
        
        # Call the parent class save_copy method with the target directory
        super().save_copy(copy_directory)

    def import_external_masks(self, folder_path, mask_candidates,
                                plain_images):
        """Offer binary/indexed/RGB import for mask-like files.

        Returns the labels.json path to continue the native load, or None
        if the user declined (candidates then load as plain images).
        """
        import json
        from PyQt6.QtWidgets import QDialog
        from PyImageLabeling.controller.settings.LabelSetting import (
            ImportFormatDialog)
        from PyImageLabeling.model.File.MaskImport import (
            normalize_binary_mask, indexed_to_binary, rgb_to_binary,
            rgb_colors_present, palette_color)

        fmt_dialog = ImportFormatDialog(self.view.zoomable_graphics_view)
        fmt_dialog.setWindowTitle(
            f"Import masks — {len(mask_candidates)} file(s) look like "
            f"annotations")
        if fmt_dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        fmt = fmt_dialog.selected_format

        # ── label specs: (kind, payload, name, QColor) ──
        specs = []
        if fmt == ImportFormatDialog.FORMAT_INDEXED:
            values = list(dict.fromkeys(fmt_dialog.index_values)) or [1]
            for i, v in enumerate(values):
                specs.append(("indexed", int(v), f"class_{v}",
                              palette_color(i)))
        elif fmt == ImportFormatDialog.FORMAT_RGB:
            seen, union = set(), []
            for mask_path, _ in mask_candidates:
                try:
                    for c in rgb_colors_present(mask_path):
                        if c not in seen:
                            seen.add(c)
                            union.append(c)
                        if len(union) >= 12:
                            break
                except Exception as e:
                    log.error(f"cannot read '{mask_path}': {e}")
                if len(union) >= 12:
                    break
            if not union:
                self.controller.error_message(
                    "Import", "No non-black colours found in RGB masks.")
                return None
            for i, (r, g, b) in enumerate(union):
                from PyQt6.QtGui import QColor as _QC
                specs.append(("rgb", (r, g, b), f"class_{r}_{g}_{b}",
                              _QC(r, g, b)))
        else:
            specs.append(("binary", None, "imported_mask", palette_color(0)))

        # ── allocate label ids + names (items/bars are built later by the
        # native labels.json loader; reuses same-named labels) ──
        from PyImageLabeling.model.LabelItem import LabelItem
        pixel_mode = self.view.config["labeling_bar"]["pixel"]["name_view"]
        existing_by_name = {item.get_name(): lid
                            for lid, item in self.label_items.items()}
        label_ids = {}  # specs index -> label_id
        label_defs = {}  # specs index -> (name, QColor)
        for i, (kind, payload, name, color) in enumerate(specs):
            if name in existing_by_name:
                lid = existing_by_name[name]
            else:
                while (LabelItem.static_label_id in LabelItem.used_ids):
                    LabelItem.static_label_id += 1
                lid = LabelItem.static_label_id
                LabelItem.static_label_id += 1
                existing_by_name[name] = lid
            label_ids[i] = lid
            label_defs[i] = (name, color)

        # ── convert + write native files ──
        progress = QProgressDialog("Importing masks…", "Cancel",
                                   0, len(mask_candidates), self.view)
        progress.setWindowTitle("Importing Masks")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        try:
            for j, (mask_path, image_path) in enumerate(mask_candidates):
                if progress.wasCanceled():
                    break
                progress.setLabelText(
                    f"Importing '{os.path.basename(mask_path)}'…  "
                    f"({j + 1} / {len(mask_candidates)})")
                progress.setValue(j)
                base = os.path.splitext(os.path.basename(image_path))[0]
                for i, (kind, payload, _name, _c) in enumerate(specs):
                    try:
                        if kind == "indexed":
                            m = indexed_to_binary(mask_path, [payload])
                        elif kind == "rgb":
                            m = rgb_to_binary(mask_path, payload)
                        else:
                            m = normalize_binary_mask(mask_path)
                    except Exception as e:
                        log.error(f"cannot convert "
                                  f"'{mask_path}': {e}")
                        continue
                    if np.any(np.array(m)):
                        dest = os.path.join(
                            folder_path,
                            f"{base}.label.{label_ids[i]}.png")
                        m.save(dest)
                        # written after the folder scan: register it so
                        # overlays pick it up like native label files
                        self.load_labels_images(dest)
                progress.setValue(j + 1)
        finally:
            progress.setValue(len(mask_candidates))

        # ── merge labels.json (native loader takes over afterwards) ──
        labels_path = os.path.join(folder_path, "labels.json")
        data = {}
        if os.path.isfile(labels_path):
            try:
                with open(labels_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                data = {}
        for _i, (_kind, _p, _n, _c) in enumerate(specs):
            lid = label_ids[_i]
            name, color = label_defs[_i]
            data[str(lid)] = {
                "name": name,
                "labeling_mode": pixel_mode,
                "color": [color.red(), color.green(), color.blue()],
            }
        Utils.write_json_atomic(labels_path, data)
        try:
            self.view.statusBar().showMessage(
                f"Imported {len(mask_candidates)} mask(s) → "
                f"{len(specs)} label(s)")
        except (AttributeError, RuntimeError):
            pass
        return labels_path

    def confirm_close_project(self, before="opening the new folder"):
        """Offer to save unsaved annotations before the project is closed.

        `before` ends the question ("Save them before <before>?"): the
        project is closed when another folder is opened and when the
        window is closed.

        Returns False when the project must stay open as it is: the user
        cancelled, or chose to save and the save did not go through (save
        dialog cancelled, failed mask write).
        """
        if not self.get_edited():
            return True
        Button = QMessageBox.StandardButton
        answer = QMessageBox.question(
            self.view, "Unsaved annotations",
            "The current project has unsaved annotations.\n\n"
            f"Save them before {before}?",
            Button.Save | Button.Discard | Button.Cancel, Button.Save)
        if answer == Button.Discard:
            return True
        if answer != Button.Save:
            return False
        self.save()
        return not self.get_edited()

    def close_project(self):
        """Forget the open folder: images, overlays, labels, file list.

        One project = one folder: opening a folder replaces the project
        instead of appending to it. The trained ML model is kept (it is
        not tied to a folder); per-image ML bookkeeping is not.
        """
        # transient tool graphics live in the scene that is about to go
        if getattr(self, "checked_button", None) == "contour_filling":
            try:
                self.remove_contour()
            except Exception:
                pass
        if hasattr(self, "_sam_reset_prompts"):
            try:
                self._sam_reset_prompts()
            except Exception:
                pass
            self.sam_session_image_path = None
        try:
            self.zoomable_graphics_view.scene.clear()
        except (AttributeError, RuntimeError):
            pass
        self.current_image_item = None

        # deterministic teardown of every loaded image (painters, pixmaps)
        for path in list(self.image_items):
            if self.image_items[path] is not None:
                self._unload_image(path)
        self._image_lru.clear()
        # cleared in place: the file bar's remove buttons hold these objects
        self.file_paths.clear()
        self.image_items.clear()
        self.icon_button_files.clear()
        file_bar = self.view.file_bar_list
        was_blocked = file_bar.blockSignals(True)
        try:
            file_bar.clear()
        finally:
            file_bar.blockSignals(was_blocked)

        self.labeling_overview_was_loaded.clear()
        self.labeling_overview_file_paths.clear()
        self.left_rectangles.clear()
        self.left_ellipses.clear()
        self.left_polygons.clear()

        self._clear_label_bar()
        self.label_items.clear()
        self.current_label_item = None
        LabelItem.static_label_id = 0
        LabelItem.used_ids.clear()

        for name in ("_ml_annotated", "_ml_disk_annotated",
                     "_ml_painted_cache", "_ml_label_count_cache"):
            cache = getattr(self, name, None)
            if isinstance(cache, dict):
                cache.clear()
        self._last_batch = []
        self._last_batch_idx = -1
        controller = self.controller
        controller._al_ranking = None
        controller._al_pos = -1

        self.save_directory = ""
        self.show_project_in_title()

    def show_project_in_title(self):
        """Window title: the path of the open project, if any."""
        try:
            self.view.set_project_title(self.project_directory())
        except (AttributeError, RuntimeError):
            pass

    def project_directory(self):
        """Folder of the open project, '' when none (one project = one
        folder)."""
        if self.save_directory:
            return os.path.normpath(self.save_directory)
        if self.file_paths:
            return os.path.normpath(os.path.dirname(self.file_paths[0]))
        return ""

    def new_project(self, folder=None):
        """Start an empty project in a folder, to fill with File > Add
        Images and File > Import Labels. Returns True once it is open.

        The folder must hold no image and no project file: an existing
        project is opened with Open Project, never mixed into a new one.
        """
        if folder is None:
            last = (Utils.load_parameters().get("load") or {}).get("path", "")
            folder = QFileDialog.getExistingDirectory(
                self.view, "New project: choose or create an empty folder",
                os.path.dirname(os.path.normpath(last)) if last else "",
                QFileDialog.Option.ShowDirsOnly
                | QFileDialog.Option.DontUseNativeDialog)
            if not folder:
                return False
        folder = os.path.normpath(folder)
        try:
            names = os.listdir(folder)
        except OSError as e:
            QMessageBox.warning(self.view, "New Project",
                                f"This folder cannot be used:\n{e}")
            return False
        if any(_is_image_name(n) or KEYWORD_SAVE_LABEL in n
               or n in PROJECT_FILES for n in names):
            QMessageBox.information(
                self.view, "New Project",
                "This folder already holds images or a project.\n\n"
                "Open it with Open Project, or choose an empty folder (the "
                "dialog can create one).")
            return False
        if not self.confirm_close_project(before="creating a new project"):
            return False
        self.close_project()
        self.save_directory = folder
        # an empty labels.json makes the folder a project: reopening it
        # before anything was saved finds it again
        try:
            Utils.write_json_atomic(os.path.join(folder, "labels.json"), {})
        except OSError as e:
            QMessageBox.warning(self.view, "New Project",
                                f"The project could not be created:\n{e}")
            self.save_directory = ""
            return False
        data = Utils.load_parameters()
        data.setdefault("load", {})["path"] = folder
        Utils.save_parameters(data)
        self.show_project_in_title()
        try:
            self.view.statusBar().showMessage(
                "New project: add images with File > Add Images, then "
                "create labels or import them (File > Import Labels)")
        except (AttributeError, RuntimeError):
            pass
        return True

    def add_images(self, image_paths=None):
        """Bring images from another folder into the open project.

        One project = one folder: an image joins the project by being
        copied into the project folder, so reopening the folder finds it
        again. The project stays open, unsaved strokes included. Masks are
        not copied: their label ids belong to the other project, and File >
        Import Labels brings them in under a label of this one.

        `image_paths` is asked with a file dialog when None. Returns the
        paths of the images added to the project.
        """
        project_dir = self.project_directory()
        if not project_dir:
            QMessageBox.information(
                self.view, "No project open",
                "Create or open a project first, then add images to it.")
            return []
        if image_paths is None:
            image_paths, _ = QFileDialog.getOpenFileNames(
                self.view, "Add images to the project",
                os.path.dirname(project_dir),
                "Images (" + " ".join("*" + e for e in IMAGE_EXTENSIONS)
                + ")",
                options=QFileDialog.Option.DontUseNativeDialog)
        if not image_paths:
            return []

        def key(path):
            return os.path.normcase(os.path.abspath(path))

        listed = {key(p) for p in self.file_paths}
        added, skipped = [], []
        progress = QProgressDialog("Copying images…", "Cancel", 0,
                                   len(image_paths), self.view)
        progress.setWindowTitle("Add Images")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(400)
        for i, source in enumerate(image_paths):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            name = os.path.basename(source)
            target = os.path.join(project_dir, name)
            if not _is_image_name(name):
                skipped.append(f"{name}: not an image, or a mask file "
                               "(masks: File > Import Labels)")
            elif key(target) in listed:
                skipped.append(f"{name}: already in the project")
            elif os.path.exists(target) and \
                    not os.path.samefile(source, target):
                skipped.append(f"{name}: another file with this name is "
                               "already in the project folder")
            else:
                if not os.path.exists(target):
                    try:
                        shutil.copy2(source, target)
                    except OSError as e:
                        skipped.append(f"{name}: could not be copied ({e})")
                        continue
                added.append(target)
                listed.add(key(target))
        progress.setValue(len(image_paths))

        if added:
            first_row = self.view.file_bar_list.count()
            for path in added:
                self.file_paths.append(path)
                self.image_items[path] = None
            self.view.file_bar_add(added)
            # an empty project had them disabled (previous, next, save)
            for button in self.view.buttons_file_bar.values():
                button.setEnabled(True)
            self.view.file_bar_list.setCurrentRow(first_row)
        if skipped:
            QMessageBox.information(
                self.view, "Add Images",
                f"{len(added)} image(s) added to the project.\n\n"
                "Not added:\n" + "\n".join(skipped))
        else:
            try:
                self.view.statusBar().showMessage(
                    f"{len(added)} image(s) added to the project")
            except (AttributeError, RuntimeError):
                pass
        return added

    def _clear_label_bar(self):
        """Remove every label row from the label bar."""
        view = self.view
        for label_id in list(view.container_label_bar_temporary):
            widget, separator = view.container_label_bar_temporary.pop(label_id)
            widget.hide()
            view.label_bar_layout.removeWidget(widget)
            separator.hide()
            view.label_bar_layout.removeWidget(separator)
            view.buttons_label_bar_temporary.pop(label_id, None)

    def load(self, default_path=None):
        if default_path is None:
            self.default_path = Utils.load_parameters()["load"]["path"]
            
            
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
            dialog.setOption(QFileDialog.Option.ReadOnly, False)  
            dialog.setDirectory(self.default_path)
            
            def check_selection(path):
                info = QFileInfo(path)
                if info.isFile():
                    self.default_path = info.absolutePath()
                    current_file_path = self.default_path + os.sep
                    data = Utils.load_parameters()
                    data["load"]["path"] = os.path.dirname(current_file_path)
                    Utils.save_parameters(data)
                    dialog.done(0)  
                    self.controller.error_message("Load Error", "You can not select a file, chose a folder !")
                    self.load()
                    
            dialog.currentChanged.connect(check_selection)
            dialog.setModal(True)

            if dialog.exec() == 0: return 
            
            self.default_path = dialog.selectedFiles()[0]
            current_file_path = self.default_path
            
            if len(current_file_path) == 0: return
            current_file_path = current_file_path + os.sep
            data = Utils.load_parameters()
            data["load"]["path"] = os.path.dirname(current_file_path)
            Utils.save_parameters(data)
            
        else:
            self.default_path = default_path
            current_file_path = self.default_path 

        # Update the model with the good images
        # The model variables is update in this method: file_paths and image_items
        current_files = [current_file_path+os.sep+f for f in sorted(os.listdir(current_file_path))]
        current_files_to_add = []

        labels_json = None
        rectangle_json = None
        ellipse_json = None
        polygon_json = None
        labels_images = []
        raw_images = []  # non-native image files (plain images or ext. masks)
        for file in current_files:
            if file.lower().endswith(IMAGE_EXTENSIONS):
                if KEYWORD_SAVE_LABEL in file:
                    # It is a label file
                    labels_images.append(file)
                else:
                    raw_images.append(file)
            elif file.endswith("labels.json"):
                labels_json = file # Load it later
            elif file.endswith("Rectangles.json"):
                rectangle_json = file # Load it later
            elif file.endswith("Ellipses.json"):
                ellipse_json = file # Load it later
            elif file.endswith("Polygons.json"):
                polygon_json = file # Load it later

        if not raw_images and not labels_images and labels_json is None \
                and rectangle_json is None and ellipse_json is None \
                and polygon_json is None:
            # Nothing to do here. Returning silently left the user staring
            # at an unchanged window, wondering whether the open had even
            # happened (typically: a parent folder whose images live in
            # subfolders, which are not scanned).
            if not _subfolders_with_images(current_file_path):
                # an empty folder: most likely a new project to start
                Button = QMessageBox.StandardButton
                answer = QMessageBox.question(
                    self.view, "Empty folder",
                    "This folder holds no image and no project.\n\n"
                    "Create a new project in it? (then File > Add Images "
                    "and File > Import Labels fill it)",
                    Button.Yes | Button.No, Button.Yes)
                if answer == Button.Yes:
                    self.new_project(current_file_path)
                return
            QMessageBox.information(
                self.view, "Nothing to load",
                nothing_to_load_message(current_file_path))
            return

        # ── One project = one folder: opening a folder replaces the project ──
        # Opening used to *append* the new images to the list while resetting
        # the overlays of the previous ones and redirecting every save to the
        # new folder: the old images stayed listed but showed no annotation,
        # and strokes made on them were saved into the wrong folder.
        if not self.confirm_close_project():
            return
        self.close_project()
        # one project = one folder: saving goes into it, also when it has no
        # labels.json yet (Save used to ask where to save, which split the
        # project between two folders)
        self.save_directory = current_file_path
        self.show_project_in_title()

        # ── External masks? (binary / indexed / RGB next to the images) ──
        # Files like "img_mask.png" next to "img.png" are probably masks,
        # not images: offer the import modes instead of loading them as
        # images.
        from PyImageLabeling.model.File.MaskImport import (
            find_mask_candidates)
        mask_candidates, plain_images = find_mask_candidates(
            raw_images, raw_images)
        for file in plain_images:
            self.file_paths.append(file)
            self.image_items[file] = None
            current_files_to_add.append(file)
        if mask_candidates:
            imported_json = self.import_external_masks(
                current_file_path, mask_candidates, plain_images)
            if imported_json is not None:
                labels_json = imported_json
            else:
                # user declined: load them as plain images (legacy behaviour)
                for mask_path, _ in mask_candidates:
                    self.file_paths.append(mask_path)
                    self.image_items[mask_path] = None
                    current_files_to_add.append(mask_path)
                try:
                    self.view.statusBar().showMessage(
                        f"{len(mask_candidates)} file(s) loaded as plain "
                        f"images (mask import declined)")
                except (AttributeError, RuntimeError):
                    pass
        # ── Progress bar ─────────────────────────────────────────────────────
        # Compute an approximate step count so the bar fills evenly:
        #   • 1 step per image added to the file bar
        #   • 1 step per label PNG indexed
        #   • a few fixed steps for reset / JSON loading / finalising
        n_images = len(current_files_to_add)
        n_labels = len(labels_images)
        n_json   = sum(1 for j in [labels_json, rectangle_json,
                                    ellipse_json, polygon_json] if j is not None)
        _FIXED   = 3  # reset + select_label + complete_state
        total_steps = n_images + n_labels + n_json + _FIXED

        progress = QProgressDialog("", None, 0, max(total_steps, 1), self.view)
        progress.setWindowTitle("Loading Images and Labels")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(400)   # only appears if loading takes > 400 ms
        progress.setValue(0)

        # ── Add images to the file bar (heaviest step for large datasets) ──
        canceled = self.view.file_bar_add(current_files_to_add,
                                          progress=progress,
                                          progress_offset=0)
        if canceled:
            for f in current_files_to_add:
                self.file_paths.remove(f)
                del self.image_items[f]
            return

        for file_path in current_files_to_add:
            fp_basename = ".".join(os.path.basename(file_path).split(".")[:-1])

            # Check pixel-mask overlays
            has_label = any(
                image_base_from_mask_name(k) == fp_basename
                for k in self.labeling_overview_was_loaded
            )

            # Check geometric shapes
            if not has_label:
                image_name = os.path.basename(file_path)
                has_label = (
                    image_name in self.left_rectangles or
                    image_name in self.left_ellipses or
                    image_name in self.left_polygons
                )

            if has_label:
                icons = self.icon_button_files.get(file_path)
                if icons is not None:
                    icons["label_tag"].setPixmap(self.view.label_tag)

        # Activate previous and next buttons
        for button_name in self.view.buttons_file_bar:
            self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list if we have some images and no image selected
        if self.view.file_bar_list.count() > 0 and self.view.file_bar_list.currentRow() == -1:
            self.view.file_bar_list.setCurrentRow(0) 

        if len(labels_images) != 0 and labels_json is None:
            progress.setValue(total_steps)   # dismiss the progress bar
            self.controller.error_message("Load Error", "The labeling image or the `labels.json` file is missing !")
            return

        if len(labels_images) == 0 and labels_json is None and \
            rectangle_json is None and ellipse_json is None and polygon_json is None:
            progress.setValue(total_steps)   # dismiss the progress bar
            return

        # ── Step counter resumes after the file-bar phase ────────────────
        step = n_images

        # (the previous project was fully closed by close_project() above)
        step += 1
        progress.setValue(step)

        # ── Index label PNG files ─────────────────────────────────────────
        if labels_images is not None:
            # Drop entries whose file disappeared (deleted mask, moved
            # folder): a stale entry made the overlay load a null pixmap and
            # every stroke on that image was silently lost.
            try:
                for key in list(self.labeling_overview_file_paths):
                    if not os.path.isfile(self.labeling_overview_file_paths[key]):
                        self.labeling_overview_file_paths.pop(key, None)
                        self.labeling_overview_was_loaded.pop(key, None)
            except Exception:
                pass
            _upd = max(1, n_labels // 100)   # same throttle: ~100 updates max
            for i, file in enumerate(labels_images):
                self.load_labels_images(file)
                if i % _upd == 0 or i == n_labels - 1:
                    progress.setLabelText(f"Indexing label files… ({i + 1} / {n_labels})")
                    step_now = n_images + 1 + i + 1
                    progress.setValue(step_now)
            step = n_images + 1 + n_labels

        # ── Load JSON metadata ────────────────────────────────────────────
        if labels_json is not None:
            progress.setLabelText("Loading label definitions…")
            self.load_labels_json(labels_json)
            if self.get_label_items():
                first_id = list(self.get_label_items().keys())[0]
                self.controller.select_label(first_id)
            elif _is_empty_json(labels_json):
                pass   # a project with no label yet (new project)
            else:
                # labels.json was missing or unreadable: load_labels_json
                # already reported it. Selecting label 0 of an empty dict
                # used to raise IndexError here and kill the whole open.
                self.controller.error_message(
                    "Load Error",
                    "No label definition could be read from this project.\n\n"
                    "Create the labels you need, or use File > Recover "
                    "Unsaved Annotations if auto-save was enabled.")
            step += 1
            progress.setValue(step)

        if rectangle_json is not None:
            progress.setLabelText("Loading rectangle annotations…")
            self.load_rectangles_json(rectangle_json)
            step += 1
            progress.setValue(step)
        
        if ellipse_json is not None:
            progress.setLabelText("Loading ellipse annotations…")
            self.load_ellipses_json(ellipse_json)
            step += 1
            progress.setValue(step)

        if polygon_json is not None:
            progress.setLabelText("Loading polygon annotations…")
            self.load_polygons_json(polygon_json)
            step += 1
            progress.setValue(step)

        # ── Finalise ──────────────────────────────────────────────────────
        progress.setLabelText("Finalising…")
        self.save_directory = current_file_path
        self.load_complete_state()
        progress.setValue(total_steps)   # reaches maximum → auto-hides

        
            
            


    
