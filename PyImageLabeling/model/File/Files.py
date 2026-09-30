


from PyQt6.QtCore import Qt, QFileInfo
from PyQt6.QtWidgets import QFileDialog, QProgressDialog, QMessageBox

from PyImageLabeling.model.Core import Core, KEYWORD_SAVE_LABEL
from PyImageLabeling.model.Utils import Utils

import numpy as np
import os

        
class Files(Core):
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
                    print(f"[import] cannot read '{mask_path}': {e}")
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
        from PyImageLabeling.model.Core import LabelItem
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
                        print(f"[import] cannot convert "
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
            except Exception:
                data = {}
        for _i, (_kind, _p, _n, _c) in enumerate(specs):
            lid = label_ids[_i]
            name, color = label_defs[_i]
            data[str(lid)] = {
                "name": name,
                "labeling_mode": pixel_mode,
                "color": [color.red(), color.green(), color.blue()],
            }
        with open(labels_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        try:
            self.view.statusBar().showMessage(
                f"Imported {len(mask_candidates)} mask(s) → "
                f"{len(specs)} label(s)")
        except Exception:
            pass
        return labels_path

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
            if file in self.file_paths:
                continue
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif",
                                       ".bmp", ".tiff", ".tif")):
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
                except Exception:
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
                k.split(KEYWORD_SAVE_LABEL)[0] == fp_basename
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

        if labels_json is not None and self.get_edited():
            msgBox = QMessageBox(self.view.zoomable_graphics_view)
            msgBox.setWindowTitle("Load")
            msgBox.setText("Are you sure you want to load the new labeling overview without save our previous works ?")
            msgBox.setInformativeText("All previous works not saved will be reset.")
            msgBox.setStandardButtons(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
            msgBox.setDefaultButton(QMessageBox.StandardButton.No)
            msgBox.setModal(True)
            result = msgBox.exec()

            if result == QMessageBox.StandardButton.No:
                progress.setValue(total_steps)   # dismiss the progress bar
                return

        # ── Step counter resumes after the file-bar phase ────────────────
        step = n_images

        # ── Reset all labeling overlays in the model ─────────────────────
        progress.setLabelText("Resetting previous annotations…")
        progress.setValue(step)
        self.reset()
        self.labeling_overview_was_loaded.clear()
        self.labeling_overview_file_paths.clear()

        # Reset the view
        to_delete = []
        for label_id in self.view.container_label_bar_temporary:
            widget, separator = self.view.container_label_bar_temporary[label_id]

            widget.hide()
            self.view.label_bar_layout.removeWidget(widget)
            separator.hide()
            self.view.label_bar_layout.removeWidget(separator)

            # Clean up the view dictionaries
            to_delete.append(label_id)
            if label_id in self.view.buttons_label_bar_temporary:
                del self.view.buttons_label_bar_temporary[label_id]

        for label_id in to_delete:
            del self.view.container_label_bar_temporary[label_id]

        # Clear the labels in the model
        self.label_items.clear()

        # Reset the icon file
        self.update_icon_file()
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
            first_id = list(self.get_label_items().keys())[0]
            self.controller.select_label(first_id)
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

        
            
            


    
