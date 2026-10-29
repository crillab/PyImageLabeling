
from PyQt6.QtGui import (
    QPainter,
    QImage,
    QPixmap,
    QColor,
    QPainter,
    QBrush,
    QPen,
)
from PyQt6.QtCore import Qt, QSize, QTimer, QDateTime
from PyImageLabeling.view.QBackgroundItem import QBackgroundItem

from PIL import Image
import numpy
from collections import deque

from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model import Autosave
from PyImageLabeling.model.Labeling.RectangleItem import RectangleItem
from PyImageLabeling.model.Labeling.EllipseItem import EllipseItem
from PyImageLabeling.model.Labeling.PolygonItem import PolygonItem
import numpy as np
import os
import json
import re
import hashlib
import shutil

from PyImageLabeling.logging_setup import get_logger
from PyImageLabeling.model.Masks import (
    KEYWORD_SAVE_LABEL,
    PATH_HASH_LEN,
    DEFAULT_KEEP_LOADED_IMAGES,
    path_hash,
    mask_image_base,
    mask_file_name,
    image_base_from_mask_name,
)

from PyImageLabeling.logging_setup import get_logger
log = get_logger("core")
from PyImageLabeling.model.GeometryUpdater import GeometryUpdaterMixin

from PyImageLabeling.model.Undo import CompactUndoEntry

from PyImageLabeling.model.LabelingOverlay import LabelingOverlay
from PyImageLabeling.model.ImageItem import ImageItem
from PyImageLabeling.model.LabelItem import LabelItem
from PyImageLabeling.model.ImageCatalog import ImageCatalog

class Base(GeometryUpdaterMixin):
    @property
    def file_paths(self):
        return self._image_catalog.file_paths

    @file_paths.setter
    def file_paths(self, value):
        self._image_catalog.file_paths = value

    @property
    def image_items(self):
        return self._image_catalog.image_items

    @image_items.setter
    def image_items(self, value):
        self._image_catalog.image_items = value

    @property
    def icon_button_files(self):
        return self._image_catalog.icon_button_files

    @icon_button_files.setter
    def icon_button_files(self, value):
        self._image_catalog.icon_button_files = value


    def __init__(self):
        
        
        self.checked_button = None # The current button checked => usefull to know the labelinf tool to use
        
        # LRU of selected images: ImageItem objects carry the full pixmap,
        # numpy buffers and per-label overlay pixmaps (~50 MB each for big
        # images) and used to stay forever, so merely *browsing* hundreds
        # of images grew the process to tens of GB. Old entries beyond
        # keep_loaded_images are unloaded (select_image / _evict_images).
        self._image_lru = []
        
        self.__dict__["_image_catalog"] = ImageCatalog()
        self.file_paths = [] # List of file paths of images (in the good order)

        self.image_items = dict() # Dictionnary: (key: file_path) -> (value: ImageItem or None)
        self.label_items = dict() # Dictionnary: (key: label_id) -> (value: LabelItem)
        
        self.current_label_item = None # The current label selected
        self.current_image_item = None # The current ImageItem that is display 

        self.icon_button_files = dict()

        self.save_directory = ""

        # For a file_path, say if a labeling overview was loaded or not   
        self.labeling_overview_was_loaded = dict() # Dictionnary: (key: basename) -> (value: True or False)
        
        # To obtain the file path 
        self.labeling_overview_file_paths = dict() # Dictionnary: (key: basename) -> (value: file_path)

        
        self.left_rectangles= {}
        self.left_ellipses = {}
        self.left_polygons = {}

        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.auto_save)
        self.autosave_interval = Utils.load_parameters().get("autosave_interval", 300000)  # Default 5 minutes in ms
        self.autosave_enabled = Utils.load_parameters().get("autosave_enabled", True)
        
        if self.autosave_enabled:
            self.autosave_timer.start(self.autosave_interval)

    def auto_save(self):
        if not self.save_directory:
            return

        auto_save_path = Autosave.autosave_dir(self.save_directory)

        if not os.path.exists(auto_save_path):
            os.makedirs(auto_save_path)

        self._save_all(auto_save_path, reset_edited=False)

        log.debug(f"Auto-saved at {QDateTime.currentDateTime().toString('hh:mm:ss')}")

    def set_autosave_enabled(self, enabled):
        """Enable or disable auto-save"""
        self.autosave_enabled = enabled
        if enabled and not self.autosave_timer.isActive():
            self.autosave_timer.start(self.autosave_interval)
        elif not enabled and self.autosave_timer.isActive():
            self.autosave_timer.stop()

    def set_autosave_interval(self, interval_ms):
        """Set auto-save interval in milliseconds"""
        self.autosave_interval = interval_ms
        if self.autosave_timer.isActive():
            self.autosave_timer.start(self.autosave_interval)

    def reset(self):
        
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is not None:
                to_delete = []
                for labeling_overlay_key in image_item.labeling_overlays:
                    image_item.labeling_overlays[labeling_overlay_key].reset()
                    image_item.labeling_overlays[labeling_overlay_key].remove()
                    to_delete.append(labeling_overlay_key)
                    self.update_icon_file()
                
                for labeling_overlay_key in to_delete:
                    del image_item.labeling_overlays[labeling_overlay_key]
                    self.update_icon_file()

        if hasattr(self, 'autosave_timer'):
            self.autosave_timer.stop()
            if self.autosave_enabled:
                self.autosave_timer.start(self.autosave_interval)
            
        
    def get_edited(self):
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is not None and image_item.get_edited() is True:
                return True
        return False

    def resize_all_undo_deques(self, new_depth):
        """Apply a new undo depth to every overlay of every loaded image.

        New overlays already read parameters["undo"]["depth"] at creation;
        without this, changing the depth in the settings only ever reached
        the current overlay of the current image.
        Returns the number of overlays resized.
        """
        try:
            new_depth = int(new_depth)
        except (TypeError, ValueError):
            return 0
        if new_depth < 0:
            new_depth = 0
        count = 0
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is None:
                continue
            for overlay in image_item.labeling_overlays.values():
                try:
                    overlay.memory_depth = new_depth
                    overlay.resize_undo_deque(new_depth)
                    count += 1
                except Exception:
                    pass
        return count

    def get_label_items(self):
        return self.label_items
    
    def get_image_items(self):
        return self.image_items
    
    def get_current_label_item(self):
        return self.current_label_item
    
    def set_current_label_item(self, current_label_item):
        self.current_label_item = current_label_item
    
    def get_current_image_item(self):
        return self.current_image_item

    def get_static_label_id(self):
        return LabelItem.static_label_id
    
    def set_view(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut

    def set_controller(self, controller):
        self.controller = controller

    def set_opacity(self, opacity):
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is not None:
                image_item.set_opacity(opacity)

    def update_icon_file(self):
        for file in self.file_paths:
            image_item = self.image_items.get(file) 
            icons = self.icon_button_files.get(file)
            if icons is None:
                continue
            if image_item is not None:
                image_item.update_icon_file()
            else:
                # Not loaded yet: empty loaded icon, keep asterisk green
                icons["loaded"].setPixmap(self.view.empty)        # ← was setVisible(False)
                icons["asterisk"].setPixmap(self.view.icon_asterisk_green)

    def name_already_exists(self, name):
        for label_id, label_item in self.label_items.items():
            if label_item.get_name() == name:
                return True
        return False
    
    def save_labels(self, current_file_path):
        # Get the dictionnary of labels
        labels_dict = {}
        for label_id, label_item in self.label_items.items():
            labels_dict[label_id] = label_item.to_dict()

        # Save it
        if current_file_path != "":
            Utils.write_json_atomic(
                os.path.join(current_file_path, "labels.json"), labels_dict)

    def save_overlays(self, current_file_path, reset_edited=True):
        failed = 0
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is not None:
                try:
                    failed += image_item.save_overlays(current_file_path,
                                                       reset_edited)
                except Exception as e:
                    # one broken image must never prevent the others (nor
                    # the project jsons) from being written
                    failed += 1
                    log.error(f"overlays save failed for "
                              f"{os.path.basename(file)}: {e}")
        if failed and reset_edited:
            try:
                self.controller.error_message(
                    "Save Error",
                    f"{failed} annotation(es) could not be written to disk. "
                    "The rest of the project was saved.\n"
                    "The unreadable image(s) stay marked as edited: "
                    "try saving again after closing the files that use "
                    "them.")
            except Exception:
                pass
        return failed

    def save_labels_geometric_shape(self, current_file_path):
        rectangles_save = {}
        ellipses_save = {}
        polygons_save = {}

        for file in self.file_paths:
            image_item = self.image_items.get(file)

            if image_item is None:
                continue

            rects = image_item.image_rectangles or []
            ellipses = image_item.image_ellipses or []
            polys = image_item.image_polygons or []

            if rects:
                rectangles_save[os.path.basename(file)] = rects

            if ellipses:
                ellipses_save[os.path.basename(file)] = ellipses

            if polys:
                polygons_save[os.path.basename(file)] = polys

        os.makedirs(current_file_path, exist_ok=True)

        self._save_or_delete_json(
            rectangles_save,
            os.path.join(current_file_path, "Rectangles.json")
        )

        self._save_or_delete_json(
            ellipses_save,
            os.path.join(current_file_path, "Ellipses.json")
        )

        self._save_or_delete_json(
            polygons_save,
            os.path.join(current_file_path, "Polygons.json")
        )
    
    def _save_or_delete_json(self, data, path):
        if data:
            Utils.write_json_atomic(path, data)
        else:
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    log.debug(f"Removed empty file: {os.path.basename(path)}")
                except OSError as e:
                    log.error(f"Error removing {path}: {e}")

    def save(self):
        self._save_all(self.save_directory, reset_edited=True)

    def _save_all(self, path, reset_edited):
        self.save_labels(path)
        self.save_overlays(path, reset_edited=reset_edited)
        self.save_labels_geometric_shape(path)
        self.save_complete_state(path)

        if reset_edited and self.save_directory:
            # A real save supersedes the snapshot: leaving it behind would
            # make the next startup offer to "recover" work that is already
            # on disk. Autosave itself passes reset_edited=False, so it keeps
            # its own copy.
            try:
                Autosave.close(self.save_directory)
            except Exception as e:
                log.warning(f"could not clear snapshot: {e}")

    def save_copy(self, copy_directory):
        if not self.save_directory or not os.path.exists(self.save_directory):
            return
        
        if os.path.normpath(copy_directory) == os.path.normpath(self.save_directory):
            copy_directory = os.path.join(copy_directory, "copy")
            log.info(f"file created: {copy_directory}")
        
        os.makedirs(copy_directory, exist_ok=True)
        
        files_to_copy = [
            "labels.json",
            "Rectangles.json",
            "Ellipses.json",
            "Polygons.json",
            "complete_state.json"
        ]
        
        for filename in files_to_copy:
            src = os.path.join(self.save_directory, filename)
            if os.path.exists(src):
                dst = os.path.join(copy_directory, filename)
                try:
                    shutil.copy2(src, dst)
                except PermissionError:
                    log.warning(f"copy impossible {filename} (file used)")
        
        for file in os.listdir(self.save_directory):
            if KEYWORD_SAVE_LABEL in file and file.endswith('.png'):
                src = os.path.join(self.save_directory, file)
                dst = os.path.join(copy_directory, file)
                try:
                    shutil.copy2(src, dst)
                except PermissionError:
                    log.warning(f"copy impossible {file} (file used)")
        
        log.info("Save Copy done : %s", copy_directory)

    def _read_annotation_json(self, file, what):
        """Read a project JSON, tolerating a truncated/corrupt file.

        Every project file used to be read with a bare json.load, so a file
        left half-written by a crash took the whole project down with a
        traceback at open time. Now the readable part is loaded, the file is
        set aside as *.corrupt (nothing is destroyed) and the user is told
        which annotations are missing.
        """
        try:
            with open(file, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as e:
            try:
                os.replace(file, file + ".corrupt")
                where = os.path.basename(file) + ".corrupt"
            except OSError:
                where = os.path.basename(file)
            log.warning(f"{what} file unreadable ({e}); moved aside as {where}")
            self._warn_corrupt_project_file(what, os.path.basename(file))
            return None
        if not isinstance(data, dict):
            log.warning(f"{what} file has an unexpected shape; ignored")
            return None
        return data

    def _warn_corrupt_project_file(self, what, name):
        try:
            self.controller.error_message(
                "Load Error",
                f"{name} is corrupted ({what} annotations).\n"
                f"It was moved aside as {name}.corrupt and the rest of the "
                f"project was loaded.\n\nIf auto-save was enabled, File > "
                f"Recover Unsaved Annotations may bring the lost work back.")
        except Exception:
            pass

    def load_labels_json(self, file):
        labels_dict = self._read_annotation_json(file, "label")
        if labels_dict is None:
            return

        basename = os.path.basename(file)
        if file not in self.labeling_overview_was_loaded:
            self.labeling_overview_was_loaded[basename] = False
            self.labeling_overview_file_paths[basename] = file
        image_basename = image_base_from_mask_name(basename)  # "image"
        
        for file_path in self.file_paths:
            fp_basename = ".".join(os.path.basename(file_path).split(".")[:-1])  # "image"
            if fp_basename == image_basename:
                icons = self.icon_button_files.get(file_path)
                if icons is not None:
                    icons["label_tag"].setPixmap(self.view.label_tag)
                break
        
        for lid_str, info in labels_dict.items():
            label_id = int(lid_str)
            name = info.get("name")
            labeling_mode = info.get("labeling_mode")
            color_list = info.get("color")
            color = QColor(*color_list[:3]) if isinstance(color_list, list) else QColor(255, 0, 0)

            if self.name_already_exists(name) or label_id in self.label_items:
                continue

            self.label_items[label_id] = LabelItem(name, labeling_mode, color, id =  label_id)
            self.view.builder.build_new_layer_label_bar(
                label_id, name, labeling_mode, color
            )
            
    def load_rectangles_json(self, file):
        rectangles_dict = self._read_annotation_json(file, "rectangle")
        if rectangles_dict is None:
            return
        for image_name, rectangles in rectangles_dict.items():
            # Find the corresponding image path
            image_path = None
            for file_path in self.file_paths:
                if os.path.basename(file_path) == image_name:
                    image_path = file_path
            
            if image_path is not None and self.image_items.get(image_path) is not None:
                # Restore rectangles for this image
                self.image_items[image_path].image_rectangles = rectangles
            else:
                self.left_rectangles[image_name] = rectangles

        if self.get_current_image_item() is not None:
            current_path = self.get_current_image_item().path_image
            if current_path in self.image_items and self.image_items[current_path] is not None:
                if self.image_items[current_path].image_rectangles is not None:
                    self.restore_rectangles_for_image(current_path)

        for image_name in rectangles_dict:
            for file_path in self.file_paths:
                if os.path.basename(file_path) == image_name:
                    if self.image_items.get(file_path) is None:
                        icons = self.icon_button_files.get(file_path)
                        if icons is not None:
                            icons["label_tag"].setPixmap(self.view.label_tag)
                    break

    def reload_rectangle(self, path_image):
            if os.path.basename(path_image) in self.left_rectangles:
                self.image_items[path_image].image_rectangles =  self.left_rectangles[os.path.basename(path_image)]
                del self.left_rectangles[os.path.basename(path_image)]
            else :
                pass

    def load_ellipses_json(self, file):
        ellipses_dict = self._read_annotation_json(file, "ellipse")
        if ellipses_dict is None:
            return
        for image_name, ellipses in ellipses_dict.items():
            # Find the corresponding image path
            image_path = None
            for file_path in self.file_paths:
                if os.path.basename(file_path) == image_name:
                    image_path = file_path
            
            if image_path is not None and self.image_items.get(image_path) is not None:
                self.image_items[image_path].image_ellipses = ellipses
            else:
                self.left_ellipses[image_name] = ellipses

        if self.get_current_image_item() is not None:
            current_path = self.get_current_image_item().path_image
            if current_path in self.image_items and self.image_items[current_path] is not None:
                if self.image_items[current_path].image_ellipses is not None:
                    self.restore_ellipses_for_image(current_path)
        
        for image_name in ellipses_dict:
            for file_path in self.file_paths:
                if os.path.basename(file_path) == image_name:
                    if self.image_items.get(file_path) is None:
                        icons = self.icon_button_files.get(file_path)
                        if icons is not None:
                            icons["label_tag"].setPixmap(self.view.label_tag)
                    break

    def reload_ellipse(self, path_image):
            if os.path.basename(path_image) in self.left_ellipses:
                self.image_items[path_image].image_ellipses =  self.left_ellipses[os.path.basename(path_image)]
                del self.left_ellipses[os.path.basename(path_image)]
            else :
                pass

    def load_polygons_json(self, file):
        polygons_dict = self._read_annotation_json(file, "polygon")
        if polygons_dict is None:
            return
        for image_name, polygons in polygons_dict.items():
            # Find the corresponding image path
            image_path = None
            for file_path in self.file_paths:
                if os.path.basename(file_path) == image_name:
                    image_path = file_path
            
            if image_path is not None and self.image_items.get(image_path) is not None:
                self.image_items[image_path].image_polygons = polygons
            else:
                self.left_polygons[image_name] = polygons

        if self.get_current_image_item() is not None:
            current_path = self.get_current_image_item().path_image
            if current_path in self.image_items and self.image_items[current_path] is not None:
                if self.image_items[current_path].image_polygons is not None:
                    self.restore_polygons_for_image(current_path)

        for image_name in polygons_dict:
            for file_path in self.file_paths:
                if os.path.basename(file_path) == image_name:
                    if self.image_items.get(file_path) is None:
                        icons = self.icon_button_files.get(file_path)
                        if icons is not None:
                            icons["label_tag"].setPixmap(self.view.label_tag)
                    break

    def reload_polygon(self, path_image):
            if os.path.basename(path_image) in self.left_polygons:
                self.image_items[path_image].image_polygons =  self.left_polygons[os.path.basename(path_image)]
                del self.left_polygons[os.path.basename(path_image)]
            else :
                pass

    def load_labels_images(self, label_file_path):
        basename = os.path.basename(label_file_path)
        if label_file_path not in self.labeling_overview_was_loaded:
            self.labeling_overview_was_loaded[basename] = False
            self.labeling_overview_file_paths[basename] = label_file_path

        image_basename = image_base_from_mask_name(basename)
        for file_path in self.file_paths:
            fp_basename = ".".join(os.path.basename(file_path).split(".")[:-1])
            if fp_basename == image_basename:
                icons = self.icon_button_files.get(file_path)
                if icons is not None:
                    icons["label_tag"].setPixmap(self.view.label_tag)
                break

    def new_label(self, name, labeling_mode, color):
        label = LabelItem(name, labeling_mode, color)
        self.label_items[label.get_label_id()] = label
        return label

    def update_labeling_overlays(self, selected_label_id):
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is not None:
                image_item.update_labeling_overlays(self.label_items, selected_label_id)
        self.current_label_item = self.label_items[selected_label_id]
        if self.current_image_item is not None:
            self.current_image_item.update_scene()
            self.current_image_item.foreground_current_labeling_overlay()

    def select_image(self, path_image):
        try:
            from PyImageLabeling.model.SAM.debug_log import log_state
            log_state(f"select_image: {os.path.basename(path_image)}")
        except Exception:
            pass
        if self.checked_button == "contour_filling":
            self.remove_contour()

        self.zoomable_graphics_view.scene.clear()
        self.zoomable_graphics_view.resetTransform()
        for file in self.file_paths:
            image_item = self.image_items.get(file)
            if image_item is not None:
                image_item.clear_scene()

        if self.image_items.get(path_image) is None:
            # We have to load image and theses labels
            self.image_items[path_image] = ImageItem(self.view, 
                                                     self.controller, 
                                                     path_image, 
                                                     self.icon_button_files[path_image],
                                                     self.labeling_overview_was_loaded,
                                                     self.labeling_overview_file_paths)
            self.current_image_item = self.image_items[path_image]
            self.reload_rectangle(path_image)
            self.reload_ellipse(path_image)
            self.reload_polygon(path_image)
            self.image_items[path_image].update_scene()
            if len(self.label_items) != 0:
                self.image_items[path_image].update_labeling_overlays(
                    self.label_items, 
                    self.current_label_item.get_label_id())
            
        else:
            # Image and these labels are already loaded, display it 
            self.image_items[path_image].update_scene()
            self.current_image_item = self.image_items[path_image]

        # nothing is kept in memory forever: recent-first order + eviction
        if path_image in self._image_lru:
            self._image_lru.remove(path_image)
        self._image_lru.append(path_image)
        self._evict_loaded_images()

        if self.get_current_image_item().image_rectangles is not None:
            self.restore_rectangles_for_image(path_image)
        if self.get_current_image_item().image_ellipses is not None:
            self.restore_ellipses_for_image(path_image)
        if self.get_current_image_item().image_polygons is not None:
            self.restore_polygons_for_image(path_image)

        if self.checked_button == "contour_filling":
            self.controller.model.apply_contour()

    def _keep_loaded_images(self):
        """How many ImageItems stay loaded around the current one.

        Read from parameters (load.memory_keep_images); 0 disables any
        unloading, a negative/absent value falls back to the default.
        Loading a default at every selection is cheap compared to the
        50 MB an ImageItem can hold.
        """
        try:
            keep = int(Utils.load_parameters().get("load", {}).get(
                "memory_keep_images", DEFAULT_KEEP_LOADED_IMAGES))
        except Exception:
            keep = DEFAULT_KEEP_LOADED_IMAGES
        if keep < 0:
            keep = DEFAULT_KEEP_LOADED_IMAGES
        return keep

    def _evict_loaded_images(self):
        """Unload images that drift far from the current selection.

        An ImageItem is evictable only when nothing in it is unsaved
        (get_edited() false): its annotations live on disk, so a later
        re-selection rebuilds the identical ImageItem from the files.
        Images holding unsaved strokes are never evicted.
        """
        keep = self._keep_loaded_images()
        if keep == 0:
            return
        current = self.current_image_item.path_image \
            if self.current_image_item is not None else None
        loaded = sum(1 for item in self.image_items.values()
                     if item is not None)
        if loaded <= keep:
            return
        for path in list(self._image_lru):
            if loaded <= keep:
                return
            if path == current:
                continue
            item = self.image_items.get(path)
            if item is None:
                self._image_lru.remove(path)   # stale bookkeeping
                continue
            if item.get_edited():
                continue   # unsaved work: keep it alive
            self._image_lru.remove(path)
            self._unload_image(path)
            loaded -= 1

    def _unload_image(self, path_image):
        """Free an ImageItem's memory, with a clean re-selection contract.

        Teardown is DETERMINISTIC, done right here: QImage/QPixmap hold
        native memory, and letting an arbitrary GC cycle destroy them --
        which can fire in the middle of unrelated code, e.g. a lazy
        module import much later in the session -- was the
        use-after-free family behind the native aborts. Every painter is
        finished, every copy detached, so the object graph becomes
        acyclic and refcounting frees the C++ side immediately.

        A mask written to disk AFTER the image was first selected is not
        in the overlays index (there was no mask to load back then): if
        eviction left that unindexed, re-selecting the image built a
        BLANK overlay and the user's strokes "came back erased". So for
        every (image, label) pair whose mask file now exists, reset the
        index flag and register the file path, exactly as the load path
        would have.
        """
        item = self.image_items.get(path_image)
        if item is None:
            return
        for label_id in list(item.labeling_overlays.keys()):
            overlay = item.labeling_overlays.get(label_id)
            if overlay is not None:
                timer = getattr(overlay, "_undo_compact_timer", None)
                if timer is not None:
                    try:
                        timer.stop()
                    except Exception:
                        pass
                    overlay._undo_compact_timer = None
                # A QPainter must be finished before its device is destroyed.
                for attr in ("labeling_overlay_painter",
                             "labeling_overlay_opacity_painter",
                             "labeling_overlay_color_painter"):
                    painter = getattr(overlay, attr, None)
                    if painter is not None:
                        try:
                            if painter.isActive():
                                painter.end()
                        except Exception:
                            pass
                try:
                    overlay.undo_deque.clear()
                except Exception:
                    pass
                overlay.previous_labeling_overlay_pixmap = None
                overlay.labeling_overlay_color_pixmap = None
                overlay.labeling_overlay_item = None
                overlay.image_item = None      # break the ImageItem cycle
                overlay.scene = None
                overlay.labeling_overlay_pixmap = None
            for key in item._mask_key_candidates(label_id):
                mask_path = os.path.join(self.save_directory, key) \
                    if self.save_directory else ""
                if mask_path and os.path.isfile(mask_path):
                    self.labeling_overview_was_loaded[key] = False
                    self.labeling_overview_file_paths.setdefault(
                        key, mask_path)
            item.labeling_overlays[label_id] = None
        item.labeling_overlays.clear()
        item.current_labeling_overlay = None
        # scene.clear() already deleted the C++ scene items on the switch
        # away; these are dangling wrappers and only ever get dereferenced
        # if is_displayed_in_scene is (wrongly) True, so just drop them.
        item.backgroung_item = None
        item.image_item = None
        item.image_pixmap = None
        item.image_numpy_pixels_rgb = None
        item.view = None
        item.controller = None
        item.icon_button = None
        item.zoomable_graphics_view = None
        self.image_items[path_image] = None
        log.debug(f"unloaded {os.path.basename(path_image)} (LRU eviction)")

    def save_complete_state(self, directory=None):
        # directory defaults to the project itself, but the auto-save
        # snapshot must get its own copy: writing the real project's file
        # every 5 min both corrupted the "last real save" timestamp and left
        # the snapshot unable to restore the tick state.
        target = directory if directory else self.save_directory
        if not target:
            return
        path = os.path.join(target, "complete_state.json")
        complete_state = {}
        if os.path.isfile(path):
            # Merge with what is already there: another instance working
            # on the same save_directory keeps its own images' ticks --
            # overwriting wholesale used to make the first instance lose
            # its completion state silently (bugs from concurrent use).
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    existing = json.load(fp)
                if isinstance(existing, dict):
                    complete_state = existing
            except (json.JSONDecodeError, UnicodeDecodeError, OSError,
                    ValueError) as e:
                log.warning(f"unreliable complete_state.json ({e}); "
                            f"rewritten")
                complete_state = {}
        for file_path in self.file_paths:
            icons = self.icon_button_files.get(file_path)
            if icons is not None:
                complete_state[os.path.basename(file_path)] = icons["complete"].isChecked()
        Utils.write_json_atomic(path, complete_state)

    def load_complete_state(self):
        if not self.save_directory:
            return
        complete_state_path = os.path.join(self.save_directory, "complete_state.json")
        if not os.path.isfile(complete_state_path):
            return
        complete_state = self._read_annotation_json(
            complete_state_path, "completion state")
        if complete_state is None:
            return
        for file_path in self.file_paths:
            basename = os.path.basename(file_path)
            icons = self.icon_button_files.get(file_path)
            if icons is not None and basename in complete_state:
                icons["complete"].setChecked(complete_state[basename])
        
            
    
