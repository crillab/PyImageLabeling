from PyImageLabeling.logging_setup import get_logger
log = get_logger('core.overlay')

from PyQt6.QtGui import (QPainter, QImage, QPixmap, QColor, QBrush, QPen)
from PyQt6.QtCore import Qt, QSize
from PyImageLabeling.view.QBackgroundItem import QBackgroundItem
import numpy as np
import os, json
from collections import deque

from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.Undo import CompactUndoEntry


class LabelingOverlay():
    def __init__(self, label, scene, width, height, from_file=None, image_item=None):
        self.label = label
        
        self.scene = scene # The associated QGraphicScene of the QGraphicsView
        self.width = width # The width of the Labeling Overlay QPixmap 
        self.height = height # The height of the Labeling Overlay QPixmap
        self.zvalue = 3 # The default ZValue 
        self.opacity = Utils.load_parameters()["labeling_opacity"]/100 # To normalize
        self.memory_depth = Utils.load_parameters()["undo"]["depth"] 
        self.image_item = image_item 
        # Note: The color is in RGB, the alpha is set at only the end for the view part :)
       

        # Initialize the QPixmap
        self.labeling_overlay_pixmap = QPixmap(QSize(self.width, self.height))
        if from_file is None:
            self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        else:
            # Load the the file in the pixmap
            basename = os.path.basename(from_file)
            folder = os.path.dirname(from_file)
            json_path = os.path.join(folder, "labels.json")

            with open(json_path, "r", encoding="utf-8") as f:
                labels_data = json.load(f)

                id = basename.split('.')[-2]
                
                info = labels_data.get(id, {})
                color_list = info.get("color")
                color = QColor(*color_list[:3]) if isinstance(color_list, list) else QColor(255, 0, 0)

                label_pixmap = QPixmap(from_file)
                if label_pixmap.isNull():
                    # The registered label file no longer exists (deleted
                    # returns a null pixmap, which used to REPLACE the
                    # working overlay: every stroke drawn on that image was
                    # then silently dropped.
                    self.labeling_overlay_pixmap.fill(
                        Qt.GlobalColor.transparent)
                else:
                    image = label_pixmap.toImage()
                    image = image.convertToFormat(QImage.Format.Format_ARGB32)

                    # Create a mask for non-black pixels and fill with color
                    mask = image.createMaskFromColor(
                        QColor(0, 0, 0).rgb(), Qt.MaskMode.MaskOutColor)
                    image.fill(color)
                    image.setAlphaChannel(mask)

                    self.labeling_overlay_pixmap = QPixmap.fromImage(image)

        self.labeling_overlay_item = None

        # Initialize the deque for the `undo` feature
        self._undo_compact_timer = None
        # Set by reset(): the bottom entry is the pre-clear snapshot, to be
        # dropped on the first refresh after the clear (see update()).
        self._clear_barrier = False
        self.undo_deque = deque(maxlen=self.memory_depth)
        self.undo_deque.append(CompactUndoEntry(self.labeling_overlay_pixmap))
        
        # Initialize the associated QPainter
        self.labeling_overlay_painter = QPainter(self.labeling_overlay_pixmap)      
        self.reset_pen()

        # Initialize the previous pixmap for the `undo` feature
        self.previous_labeling_overlay_pixmap = None

        # Initialize others pixmaps and painters to change the color or opacity operations
        self.labeling_overlay_opacity_painter = QPainter()
        self.labeling_overlay_color_pixmap = QPixmap(self.width, self.height)
        self.labeling_overlay_color_painter = QPainter()

        self.is_displayed_in_scene = False
        self.is_edited = False
        self.is_undo_none = True
    
    def set_is_edited(self, is_edited):
        self.is_edited = is_edited
    
    def get_is_edited(self):
        return self.is_edited
    
    def set_is_undo_none(self, is_undo_none):
        self.is_undo_none = is_undo_none
    
    def get_is_undo_none(self):
        return self.is_undo_none
    
    def update_scene(self):
        if self.is_displayed_in_scene is False:
            self.labeling_overlay_item = self.scene.addPixmap(self.generate_opacity_pixmap())
            self.labeling_overlay_item.setZValue(self.zvalue)
            self.is_displayed_in_scene = True
        
        self.labeling_overlay_item.setVisible(self.label.get_visible())


    def reset(self):
        # Snapshot BEFORE clearing: an undo right after Clear All must
        # restore exactly what was just cleared (not deque[0], which can be
        # arbitrarily older content).
        try:
            pre_clear = CompactUndoEntry(self.labeling_overlay_pixmap,
                                         compact=False)
        except Exception:
            pre_clear = None

        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        if self.is_displayed_in_scene is True:
            if self.labeling_overlay_item is not None:
                self.labeling_overlay_item.setPixmap(
                    self.labeling_overlay_pixmap)

        self.undo_deque.clear()
        if pre_clear is not None:
            self.undo_deque.append(pre_clear)

        # Baseline for what comes next is the empty mask. The pre-clear
        # snapshot above stays reachable ONLY until the first refresh: once
        # the user paints something new, undos must stop at empty instead
        # of walking back past the clear (see update()).
        self.previous_labeling_overlay_pixmap = \
            self.labeling_overlay_pixmap.copy()
        self._clear_barrier = True

        if self.get_is_edited() is False:
            self.set_is_edited(True)

        if self.get_is_undo_none() is False:
            self.set_is_undo_none(True)

        self.image_item.update_icon_file()
        
    def recreate_painter(self):
        if hasattr(self, "labeling_overlay_painter"):
            try:
                if self.labeling_overlay_painter.isActive():
                    self.labeling_overlay_painter.end()
            except:
                pass

        self.labeling_overlay_painter = QPainter(self.labeling_overlay_pixmap)
    
    def remove(self):
        if self.is_displayed_in_scene is True:
            self.scene.removeItem(self.labeling_overlay_item)
            self.labeling_overlay_item = None
        
        self.labeling_overlay_painter.end()
        
    def set_opacity(self, opacity):
        self.opacity = opacity

        # Change and update the QPixmap 
        if self.is_displayed_in_scene is True:
            self.labeling_overlay_item.setPixmap(self.generate_opacity_pixmap())
        
    def get_opacity(self):
        return self.opacity
        
    def undo(self):
        if len(self.undo_deque) > 0:
            self.labeling_overlay_painter.end()

            # Reconstruct from CompactUndoEntry
            compact_entry = self.undo_deque.pop()
            self.labeling_overlay_pixmap = compact_entry.to_pixmap()
            self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()
            # If this consumed the pre-clear snapshot, the barrier is lifted:
            # history continues from the restored content.
            self._clear_barrier = False

        if len(self.undo_deque) == 0:
            # Store CompactUndoEntry
            self.undo_deque.append(
                CompactUndoEntry(self.labeling_overlay_pixmap, compact=False))
            self.set_is_undo_none(True)
            self.image_item.update_icon_file()

        # Update display (skip when never displayed, e.g. background batch)
        if self.labeling_overlay_item is not None:
            self.labeling_overlay_item.setPixmap(
                self.generate_opacity_pixmap())
        self.labeling_overlay_painter.begin(self.labeling_overlay_pixmap)
        self.reset_pen()
    
    def resize_undo_deque(self, new_depth):
        if new_depth <= 0:
            self.undo_deque.clear()
            self.undo_deque = deque(maxlen=0)
            return

        # Copy existing entries (keep newest)
        old_entries = list(self.undo_deque)

        # Trim oldest entries if needed
        if len(old_entries) > new_depth:
            old_entries = old_entries[-new_depth:]

        # Rebuild deque with new maxlen
        self.undo_deque = deque(old_entries, maxlen=new_depth)

    def generate_opacity_pixmap(self):
        opacity_pixmap = QPixmap(self.width, self.height)
        opacity_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(opacity_pixmap)
        painter.setOpacity(self.get_opacity())
        painter.drawPixmap(0, 0, self.labeling_overlay_pixmap)
        painter.end()
        
        return opacity_pixmap

    def update_color(self):
        # We change this labeling overlay
        if self.get_is_edited() is False:
            self.set_is_edited(True)

        # Apply Color
        self.labeling_overlay_color_pixmap.fill(self.label.get_color())
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        self.labeling_overlay_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Update
        if self.is_displayed_in_scene is True:
            self.labeling_overlay_item.setPixmap(self.generate_opacity_pixmap())

        # Apply the color on the undo pixmaps
        new_undo_deque = deque(maxlen=self.memory_depth)
        for compact_entry in self.undo_deque:
            # Reconstruct pixmap
            pixmap = compact_entry.to_pixmap()
            
            # Apply color change
            self.labeling_overlay_color_painter.begin(pixmap)
            self.labeling_overlay_color_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            self.labeling_overlay_color_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
            self.labeling_overlay_color_painter.end()
            
            # Store back as compact
            new_undo_deque.append(CompactUndoEntry(pixmap))
        
        self.undo_deque = new_undo_deque

        # Do not forget the previous undo pixmap :) 
        if self.previous_labeling_overlay_pixmap is not None:
            self.labeling_overlay_color_painter.begin(self.previous_labeling_overlay_pixmap)
            self.labeling_overlay_color_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            self.labeling_overlay_color_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
            self.labeling_overlay_color_painter.end()

        
    def update(self):
        # We change this labeling overlay
        if self.get_is_edited() is False:
            self.set_is_edited(True)

        if self.get_is_undo_none() is True:
            self.set_is_undo_none(False)
        
        # Change and update the QPixmap
        # (item is None when the image was loaded in background and never
        # displayed — e.g. batch propagation: data update still applies,
        # only the scene refresh is skipped)
        if self.labeling_overlay_item is not None:
            self.labeling_overlay_item.setPixmap(
                self.generate_opacity_pixmap())
        
        # For the `undo` feature, if we have a previous, add it in the deque.
        # The entry is stored as a plain copy here (one memcpy) and compacted
        # later by compact_undo(): encoding it now costs 4-20 ms depending on
        # how much is painted, which is what used to make a long painting
        # session stutter more and more.
        if getattr(self, "_clear_barrier", False):
            # First refresh after a Clear All: the pre-clear snapshot has
            # served its purpose (an immediate undo still restores it, see
            # undo()). Drop it now, so later undos stop at the empty mask
            # instead of walking back past the clear.
            self._clear_barrier = False
            if len(self.undo_deque) > 0:
                try:
                    self.undo_deque.popleft()
                except IndexError:
                    pass
        if self.previous_labeling_overlay_pixmap is not None:
            self.undo_deque.append(
                CompactUndoEntry(self.previous_labeling_overlay_pixmap,
                                 compact=False))

        # Create a copy to keep it in the previous pixmap variable
        self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()

        self._schedule_undo_compaction()

        if self.image_item is not None:
            self.image_item.update_icon_file()

    def pending_undo_entries(self):
        """Number of undo entries still stored as plain copies."""
        return sum(1 for e in self.undo_deque if e.is_pending())

    def compact_undo(self, max_entries=1):
        """Compact up to max_entries pending undo entries (oldest first).

        Called from an idle timer so the memory win happens without costing
        the user a stutter mid-stroke. Returns the number left pending.
        """
        done = 0
        for entry in self.undo_deque:
            if done >= max_entries:
                break
            if entry.is_pending():
                entry.compact()
                done += 1
        return self.pending_undo_entries()

    def _schedule_undo_compaction(self):
        """Compact pending undo entries once the user stops painting."""
        if self._undo_compact_timer is not None:
            return
        try:
            from PyQt6.QtCore import QTimer
            timer = QTimer()
            timer.setSingleShot(True)
            timer.setInterval(400)
            timer.timeout.connect(self._on_compact_undo_timeout)
            self._undo_compact_timer = timer
            timer.start()
        except Exception:
            self._undo_compact_timer = None

    def _on_compact_undo_timeout(self):
        """Compact one pending entry per idle tick, newest ones last."""
        try:
            remaining = self.compact_undo(max_entries=1)
            if remaining:
                self._undo_compact_timer.start()
        except Exception:
            pass
        finally:
            if getattr(self, "_undo_compact_timer", None) is None:
                return
            if self.pending_undo_entries() == 0:
                try:
                    self._undo_compact_timer.stop()
                except Exception:
                    pass

    

    

    

    
    def get_painter(self):
        return self.labeling_overlay_painter

    def set_zvalue(self, zvalue):
        self.zvalue = zvalue
        self.labeling_overlay_item.setZValue(self.zvalue)

    def reset_pen(self):
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self.labeling_overlay_painter.setPen(QPen(self.label.color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.labeling_overlay_painter.setBrush(self.label.color)
    
    def set_is_displayed_in_scene(self, is_displayed_in_scene):
        self.is_displayed_in_scene = is_displayed_in_scene

    def set_visible(self, is_visible):
        if self.labeling_overlay_item is not None:
            self.labeling_overlay_item.setVisible(is_visible)


    def save(self, current_file_path, path_image):
        # Late-import helpers to avoid circular import with Core (where
        # KEYWORD_SAVE_LABEL / path_hash currently live).  Resolve after
        # imports are complete – by call time both modules are defined.
        from PyImageLabeling.model.Masks import (
            KEYWORD_SAVE_LABEL,
            path_hash)
        name = os.path.basename(path_image)
        if "." in name:
            name, format = name.rsplit(".", 1)
        else:
            format = "png"
        format = "png"
        h = path_hash(path_image)
        save_file = current_file_path + os.sep + f"{name}.{h}" + KEYWORD_SAVE_LABEL + str(self.label.get_label_id()) + "." + format

        def _unmask_stale():
            """A mask that became all-black means the user erased it: the
            file must disappear, otherwise the stale mask would come back
            (older format sibling included) on the next reload."""
            stale_prefixes = (f"{name}.{h}{KEYWORD_SAVE_LABEL}",
                              f"{name}{KEYWORD_SAVE_LABEL}")
            try:
                for file in os.listdir(current_file_path):
                    if any(file.startswith(p)
                           for p in stale_prefixes) \
                            and file.endswith(
                                KEYWORD_SAVE_LABEL
                                + str(self.label.get_label_id()) + ".png"):
                        os.remove(os.path.join(current_file_path, file))
                        log.debug(f"removed erased mask {file}")
            except OSError as e:
                log.warning(f"could not remove stale mask for {name}: {e}")

        # Get original image
        image = self.labeling_overlay_pixmap.toImage()

        # Create binary mask directly from alpha channel
        mask = image.createAlphaMask() if not image.isNull() else QImage()
        if mask.isNull() or mask.width() == 0 or mask.height() == 0:
            log.error(f"could not rasterise mask for {name} "
                      f"(unreadable image); mask not saved")
            return
        try:
            mask.invertPixels()
            ptr = mask.bits()
            packed = ptr.asstring(mask.sizeInBytes())
        except Exception as e:
            log.error(f"could not rasterise mask for {name}: {e}; "
                      f"mask not saved")
            return

        # In a packed 1-bit image: 0x00 = eight black pixels, 0xFF = eight white pixels.
        if all(b == 0xFF for b in packed):
            _unmask_stale()
        else:
            # Write to a scratch file and rename: mask.save() used to target
            # the final name directly and its False return was ignored, so a
            # failed write (disk full, file locked by a viewer) looked like a
            # successful save and the mask was simply lost.
            tmp_file = Utils.tmp_path(save_file)
            if mask.save(tmp_file, format.upper()):
                Utils.commit_tmp(tmp_file, save_file)
            else:
                Utils.discard_tmp(tmp_file)
                log.error(f"could not write mask {os.path.basename(save_file)}")

