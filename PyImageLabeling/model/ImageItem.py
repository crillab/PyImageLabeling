from PyQt6.QtGui import (QPainter, QImage, QPixmap, QColor, QBrush, QPen)
from PyQt6.QtCore import Qt, QSize
from PyImageLabeling.view.QBackgroundItem import QBackgroundItem
import numpy as np
import os
from collections import deque

from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.LabelingOverlay import LabelingOverlay
from PyImageLabeling.logging_setup import get_logger

import numpy
from PIL import Image

log = get_logger("core.imageitem")


class ImageItem():

    def __init__(self, view, controller, path_image, icon_button, labeling_overview_was_loaded, labeling_overview_file_paths):
        self.view = view
        self.controller = controller
        self.path_image = path_image
        self.icon_button = icon_button
        self.labeling_overview_was_loaded = labeling_overview_was_loaded
        self.labeling_overview_file_paths = labeling_overview_file_paths
        
        self.zoomable_graphics_view = view.zoomable_graphics_view

        self.image_pixmap = QPixmap(path_image) # The current pixmap of the image
        self.image_item = None # The current pixmap item of the image in the scene
        self.image_numpy_pixels_rgb = None # The current RGB numpy matrix of the image  

        self.backgroung_item = None # The QBackgroundItem behind the images

        self.labeling_overlays = dict() # dict of LabelingOverlay instance 

        self.current_labeling_overlay = None # The current selected LabelingOverlay

        self.image_qrect = self.image_pixmap.rect() # Integer size in Qrect
        self.image_qrectf = self.image_qrect.toRectF() # Float size in QRectF
        
        # the background item
        self.alpha_color = Utils.load_parameters()["load"]["alpha_color"] 
        
        #save a numpy matrix of colors

        self.is_displayed_in_scene = False

        #list to store the rectangle of my image
        self.image_rectangles = []
        self.image_ellipses = []
        self.image_polygons = []

    def get_edited(self):
        for label_id in self.labeling_overlays:
            if self.labeling_overlays[label_id].get_is_edited() is True:
                return True
        return False

    def get_image_pixmap(self):
        return self.image_pixmap
    
    def get_qrectf(self):
        return self.image_qrectf
    
    def get_labeling_overlays(self):
        return list(self.labeling_overlays.values())
    
    def update_scene(self):
        if self.is_displayed_in_scene is False:
            # Add the backgroung_item in the scene
            self.backgroung_item = QBackgroundItem(self.image_qrectf, self.controller, self.alpha_color)
            self.view.zoomable_graphics_view.scene.addItem(self.backgroung_item)
            self.backgroung_item.setZValue(0) # Base layer
            
            # Add the image in the scene
            self.image_item = self.zoomable_graphics_view.scene.addPixmap(self.image_pixmap)
            self.image_item.setZValue(1) # Image layer 
            
            # Set the Event listener in the background item to the image item 
            self.image_item.installSceneEventFilter(self.backgroung_item)

            # Set the good visual parameters for the scene
            self.zoomable_graphics_view.setSceneRect(self.image_qrectf)
            self.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.zoomable_graphics_view.centerOn(self.image_qrect.width()/2,self.image_qrect.height()/2)

            self.initialyse_zoom_factor()
            self.is_displayed_in_scene = True
                
            #     # Apply the label's visibility state using existing change_visible logic
                    
            #         # Only change if current visibility doesn't match desired state

        # Update the labeling overlays
        for label_id in self.labeling_overlays:
            self.labeling_overlays[label_id].update_scene()

    def clear_scene(self):
        self.is_displayed_in_scene = False
        for label_id in self.labeling_overlays:
            self.labeling_overlays[label_id].set_is_displayed_in_scene(False)
       
    def initialyse_zoom_factor(self):
        self.view.min_zoom = self.view.zoomable_graphics_view.data_parameters["zoom"]["min_zoom"]
        self.view.max_zoom = self.view.zoomable_graphics_view.data_parameters["zoom"]["max_zoom"]

        viewport_width = self.view.zoomable_graphics_view.viewport().width()
        viewport_height = self.view.zoomable_graphics_view.viewport().height()
        diagonal_viewport = numpy.sqrt(viewport_width**2 + viewport_height**2)
        diagonal_pixmap = numpy.sqrt(self.image_qrect.width()**2 + self.image_qrect.height()**2)

        self.view.zoom_factor = diagonal_pixmap / diagonal_viewport
        if self.view.zoom_factor < self.view.min_zoom: self.view.min_zoom = self.view.zoom_factor
        self.view.max_zoom = diagonal_pixmap/self.view.max_zoom        
        self.view.initial_zoom_factor = self.view.zoom_factor

    def _mask_key_candidates(self, label_id):
        from PyImageLabeling.model.Masks import KEYWORD_SAVE_LABEL, path_hash
        """Possible on-disk mask keys of (this image, label_id), most
        specific first: the current hashed form, then the legacy
        basename-only form (projects saved before the collision fix)."""
        stem = os.path.basename(self.path_image)
        if "." in stem:
            stem = stem.rsplit(".", 1)[0]
        hashed = f"{stem}.{path_hash(self.path_image)}{KEYWORD_SAVE_LABEL}{label_id}.png"
        legacy = f"{stem}{KEYWORD_SAVE_LABEL}{label_id}.png"
        return hashed, legacy

    def _indexed_mask_key(self, label_id):
        """Key under which this image's disk mask was indexed, or None if
        no disk mask exists for it in this project."""
        was_loaded = self.labeling_overview_was_loaded
        hashed, legacy = self._mask_key_candidates(label_id)
        if was_loaded.get(hashed) is False:
            return hashed
        if was_loaded.get(legacy) is False:
            return legacy
        return None

    def update_labeling_overlays(self, label_items, selected_label_id):
        # Ensure all existing labels have an overlay
        for label_id in label_items:
            if label_id not in self.labeling_overlays:
                basename_key = self._indexed_mask_key(label_id)
                if basename_key is not None:
                    self.labeling_overlays[label_id] = LabelingOverlay(
                        label_items[label_id],
                        self.view.zoomable_graphics_view.scene,
                        self.image_qrect.width(),
                        self.image_qrect.height(),
                        self.labeling_overview_file_paths[basename_key],
                        image_item = self
                    )
                    self.labeling_overview_was_loaded[basename_key] = True
                else:
                    self.labeling_overlays[label_id] = LabelingOverlay(
                        label_items[label_id],
                        self.view.zoomable_graphics_view.scene,
                        self.image_qrect.width(),
                        self.image_qrect.height(),
                        image_item = self

                    )
        self.current_labeling_overlay = self.labeling_overlays[selected_label_id]
        self.current_label_id = selected_label_id
    
    def foreground_current_labeling_overlay(self):        
        for label_id in self.labeling_overlays:
            if label_id == self.current_label_id:
                self.labeling_overlays[label_id].set_zvalue(3)
            else:
                self.labeling_overlays[label_id].set_zvalue(2)
        # Force the visibility 
        
       

    #     # Add a new labeling overlay 
        
    #     # Add the data of this new label in the label dictionnary

    #     # Set the current label
        
    #     # Put at the first plan the current label

    # # Change the current labeling overlay
    def get_labeling_overlay(self):
        return self.current_labeling_overlay
    
    def _overlay_has_content(self, overlay):
        # If undo_none is False, user has painted on this overlay
        if not overlay.get_is_undo_none():
            return True
        # Fallback: check if the single deque entry has pixels (e.g. loaded from file)
        if len(overlay.undo_deque) == 1:
            return overlay.undo_deque[0].has_painted_pixels()
        return False

    def update_icon_file(self):
        icons = self.view.controller.model.icon_button_files.get(self.path_image)
        if icons is None:
            return

        icons["asterisk"].setPixmap(
            self.view.icon_asterisk_red if self.get_edited() else self.view.icon_asterisk_green
        )

        icons["loaded"].setPixmap(self.view.loaded)              # ← was setVisible(True)

        has_labels = (
            bool(self.image_rectangles) or
            bool(self.image_ellipses) or
            bool(self.image_polygons) or
            any(self._overlay_has_content(ov) for ov in self.labeling_overlays.values())
        )
        icons["label_tag"].setPixmap(
            self.view.label_tag if has_labels else self.view.empty   # ← was setVisible(has_labels)
        )
            
    # Update the current labeling overlay 
    def update_labeling_overlay(self):
        self.current_labeling_overlay.update()
        self.update_icon_file()
        # paint mask changed: the cached counts and the "is it painted?"
        # scan for this image are now stale. Both live on the model
# (ml_invalidate_stats_cache is relayed from the controller).
        try:
            self.view.controller.model.ml_invalidate_caches(self.path_image)
        except AttributeError:
            pass

    def set_opacity(self, opacity):
        for labeling_overlay in self.labeling_overlays.values():
            labeling_overlay.set_opacity(opacity)
    
    def update_color(self, label_id):
        self.labeling_overlays[label_id].update_color()
        
        self.update_icon_file()   

    def get_image_numpy_pixels_rgb(self):
        if self.image_numpy_pixels_rgb is None:
            self.image_numpy_pixels_rgb = numpy.array(
                Image.open(self.path_image).convert("RGB")
            )
        return self.image_numpy_pixels_rgb
    
    def get_width(self):
        return self.image_qrect.width()

    def get_height(self):
        return self.image_qrect.height()
    
    def save_overlays(self, current_file_path, reset_edited=True):
        failed = 0
        for label_id, labeling_overlay in list(self.labeling_overlays.items()):
            if labeling_overlay.get_is_edited():
                try:
                    labeling_overlay.save(current_file_path, self.path_image)
                except Exception as e:
                    # stay edited: another save() may still fix/write it
                    failed += 1
                    log.error(f"mask save failed for "
                              f"{os.path.basename(self.path_image)} "
                              f"(label {label_id}): {e}")
                else:
                    if reset_edited:
                        labeling_overlay.set_is_edited(False)

            self.update_icon_file()
        return failed

