from PyQt6.QtCore import Qt, QPointF, QRectF, QRect
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QImage
from PyQt6.QtWidgets import QGraphicsItem, QDialog
from PyImageLabeling.model.Core import Core
from PyImageLabeling.model.Utils import Utils
import numpy as np
import cv2
from PyImageLabeling.controller.settings.EraserSetting import DynamicEraserDialog


class EraserBrushItem(QGraphicsItem):

    def __init__(self, core, x, y, color, size, absolute_mode):
        super().__init__()
        self.core = core
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.absolute_mode = absolute_mode
        self.labeling_overlay_painter = self.core.get_current_image_item().get_labeling_overlay().get_painter()
        self.image_pixmap = self.core.get_current_image_item().get_image_pixmap()

        # Compute the good qrect to avoid going beyond the painting area
        self.qrectf = QRectF(int(self.x)-(self.size/2)-5, int(self.y)-(self.size/2)-5, self.size+10, self.size+10)
        self.qrectf = self.qrectf.intersected(core.get_current_image_item().get_qrectf())
        alpha_color = Utils.load_parameters()["load"]["alpha_color"]

        # Create a fake texture with the good image inside
        self.eraser_texture = QPixmap(self.size, self.size)
        self.eraser_texture.fill(QColor(*alpha_color))

        painter = QPainter(self.eraser_texture)

        painter.drawPixmap(QRect(0, 0, self.size, self.size), self.image_pixmap, QRect(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.size, self.size))
        painter.setOpacity(self.core.get_current_image_item().get_labeling_overlay().get_opacity())
        for labeling_overlay in self.core.get_current_image_item().get_labeling_overlays():
            if labeling_overlay != self.core.get_current_image_item().get_labeling_overlay() and labeling_overlay.label.get_visible():
                painter.drawPixmap(QRect(0, 0, self.size, self.size), labeling_overlay.labeling_overlay_pixmap, QRect(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.size, self.size))

        painter.end()

        # Use the fake texture as a QBrush texture of a draw point
        self.eraser_pixmap = QPixmap(self.size, self.size)
        self.eraser_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(self.eraser_pixmap)
        self.qbrush = QBrush()
        self.qbrush.setTexture(self.eraser_texture)
        self.pen = QPen(self.qbrush, self.size)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(self.pen)
        painter.drawPoint(int(self.size/2), int(self.size/2))
        painter.end()

    def boundingRect(self):
        return self.qrectf

    def paint(self, painter, option, widget):
        painter.drawPixmap(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.eraser_pixmap)

        pen = QPen(Qt.GlobalColor.black, self.size)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        if self.absolute_mode == 1:
            # Apply eraser to all labeling overlays
            for labeling_overlay in self.core.get_current_image_item().get_labeling_overlays():
                overlay_painter = labeling_overlay.get_painter()
                overlay_painter.setPen(pen)
                overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                overlay_painter.drawPoint(int(self.x), int(self.y))
        else:
            # Apply eraser only to current labeling overlay
            self.labeling_overlay_painter.setPen(pen)
            self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            self.labeling_overlay_painter.drawPoint(int(self.x), int(self.y))


class Eraser(Core):
    def __init__(self):
        super().__init__()
        self.last_position_x, self.last_position_y = None, None
        self.point_spacing = 2
        self.eraser_brush_items = []
        self.eraser_mode = "original"
        # the keep-colour can be changed live from the interactive dialog
        self._last_keep_color = None

    def eraser(self):
        self.checked_button = self.eraser.__name__

    def eraser_params(self):
        try:
            params = Utils.load_parameters().get("eraser", {})
        except Exception:
            params = {}
        return {
            "size": int(params.get("size", 50)),
            "absolute_mode": int(params.get("absolute_mode", 0)),
            "mode": params.get("mode", "original"),
            "tolerance": int(params.get("tolerance", 10)),
            "dynamic_adjust": bool(params.get("dynamic_adjust", False)),
            "keep_color": params.get("keep_color", "#0000FF"),
            # colour criterion is optional: off = erase the closed shape as is
            "use_color": bool(params.get("use_color", True)),
        }

    def set_eraser_keep_color(self, rgba):
        """Remember the colour to keep (used by the interactive dialog)."""
        self._last_keep_color = tuple(int(v) for v in rgba)

    def _status(self, message):
        try:
            self.view.statusBar().showMessage(message)
        except Exception:
            pass

    def _warn(self, title, text):
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self.view, title, text)
        except Exception:
            self._status(f"{title}: {text}")

    def start_eraser(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("eraser")

        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        params = self.eraser_params()
        self.size_eraser_brush = params["size"]
        self.absolute_mode = params["absolute_mode"]
        self.eraser_mode = params["mode"]
        self.color = self.get_current_label_item().get_color()

        if self.eraser_mode == "intelligent":
            self.intelligent_erase(self.current_position_x,
                                   self.current_position_y)
            return

        eraser_brush_item = EraserBrushItem(self, self.current_position_x, self.current_position_y, self.color, self.size_eraser_brush, self.absolute_mode)
        eraser_brush_item.setZValue(4) # To place in the top of the item
        self.zoomable_graphics_view.scene.addItem(eraser_brush_item) # update is already call in this method
        self.eraser_brush_items.append(eraser_brush_item)

        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def safe_end(painter):
        if painter is not None and painter.isActive():
            painter.end()

    def safe_begin(painter, device):
        if painter is not None and not painter.isActive():
            painter.begin(device)

    def move_eraser(self, current_position):
        if self.eraser_mode == "intelligent":
            return

        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        if Utils.compute_diagonal(self.current_position_x, self.current_position_y, self.last_position_x, self.last_position_y) < self.point_spacing:
            return

        eraser_brush_item = EraserBrushItem(self, self.current_position_x, self.current_position_y, self.color, self.size_eraser_brush, self.absolute_mode)
        eraser_brush_item.setZValue(4) # To place in the top of the item
        self.zoomable_graphics_view.scene.addItem(eraser_brush_item) # update is already call in this method
        self.eraser_brush_items.append(eraser_brush_item)

        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def end_eraser(self):
        if self.eraser_mode == "intelligent":
            return

        # Remove the dislay of all these item
        for item in self.eraser_brush_items:
            self.zoomable_graphics_view.scene.removeItem(item)
        self.eraser_brush_items.clear()

        if self.absolute_mode == 1:
            # Update all labeling overlays
            for labeling_overlay in self.get_current_image_item().get_labeling_overlays():
                labeling_overlay.update()
                labeling_overlay.reset_pen()
        else:
            # Update only current labeling overlay
            self.get_current_image_item().update_labeling_overlay()
            self.get_current_image_item().get_labeling_overlay().reset_pen()

    # ------------------------------------------------------------------
    # intelligent erase
    # ------------------------------------------------------------------
    def intelligent_erase(self, x, y):
        image_item = self.get_current_image_item()
        if image_item is None:
            return
        overlay = image_item.get_labeling_overlay()
        width, height = image_item.get_width(), image_item.get_height()
        if not (0 <= x < width and 0 <= y < height):
            return

        params = self.eraser_params()
        rgb = image_item.get_image_numpy_pixels_rgb()  # original image
        use_color = params["use_color"]
        dynamic_adjust = params["dynamic_adjust"] and use_color
        tolerance = params["tolerance"]

        if use_color:
            if self._last_keep_color is not None:
                keep_rgba = np.array(self._last_keep_color[:3], dtype=np.int16)
            else:
                keep_color = QColor(params["keep_color"])
                # RGB only: the image has no alpha channel to compare
                keep_rgba = np.array([keep_color.red(), keep_color.green(),
                                      keep_color.blue()], dtype=np.int16)
        else:
            keep_rgba = None

        # the closed shape under the click (contiguous painted area)
        shape_mask = self._shape_under_click(overlay, x, y)
        if shape_mask is None or not shape_mask.any():
            self._status("Eraser: click inside a drawn shape, not on bare "
                         "image")
            return
        n_shape = int(shape_mask.sum())

        if dynamic_adjust:
            self._dynamic_erase(image_item, overlay, rgb, shape_mask,
                                keep_rgba, tolerance, x, y, n_shape)
            return

        erase_mask = self._erase_mask(rgb, shape_mask, keep_rgba, tolerance,
                                      use_color)
        if not erase_mask.any():
            self._status("Eraser: every pixel matched — nothing to erase. "
                         "Raise the tolerance, or switch off 'Match colour'.")
            return
        n = self._apply_erase(overlay, erase_mask)
        self._status(f"Eraser: {n} px erased from "
                     f"'{self.get_current_label_item().get_name()}' "
                     f"(shape {n_shape} px"
                     + ("" if use_color else ", no colour check") + ")")
        try:
            self.controller.ml_update_stats()
        except Exception:
            pass

    def _shape_under_click(self, overlay, x, y):
        """Contiguous painted area containing (x, y) -> bool array."""
        pixmap = overlay.labeling_overlay_pixmap
        if pixmap is None or pixmap.isNull():
            return None
        img = pixmap.toImage()
        ptr = img.bits()
        ptr.setsize(img.sizeInBytes())
        h, w = img.height(), img.width()
        arr = np.frombuffer(ptr, np.uint8).reshape((h, img.bytesPerLine()))
        arr = arr[:, :w * 4].reshape(h, w, 4)
        painted = (arr[:, :, 3] > 0).astype(np.uint8) * 255
        if not painted[y, x]:
            return None
        return self._flood_component(painted, x, y)

    @staticmethod
    def _flood_component(mask, x, y):
        """4-connected component of `mask` containing (x, y).

        cv2 does this in C; the previous pure-Python span fill cost ~40 us
        per pixel.
        """
        flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE
        ff_mask = np.zeros((mask.shape[0] + 2, mask.shape[1] + 2), np.uint8)
        cv2.floodFill(mask.copy(), ff_mask, (int(x), int(y)), 0, 0, 0, flags)
        return ff_mask[1:-1, 1:-1] > 0

    @staticmethod
    def _erase_mask(rgb, shape_mask, keep_rgba, tolerance, use_color):
        """Pixels of the shape to erase: everything not matching the colour
        (or the whole shape when the colour criterion is off)."""
        if not use_color:
            return shape_mask
        h, w = shape_mask.shape
        diff = np.abs(rgb[:h, :w].astype(np.int16) - keep_rgba)
        match = np.all(diff <= tolerance, axis=2)
        return shape_mask & ~match

    def _apply_erase(self, overlay, erase_mask):
        """Clear the masked pixels with a single blit (was one addRect per
        pixel, which is what made this crawl on big shapes)."""
        h, w = erase_mask.shape
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[erase_mask] = (0, 0, 0, 255)
        qimg = QImage(rgba.data, w, h, w * 4,
                      QImage.Format.Format_RGBA8888).copy()
        overlay.recreate_painter()
        painter = overlay.get_painter()
        # DestinationOut, not Clear: Clear wipes the whole destination
        # rect whatever the source alpha is, which erased the kept pixels
        # too. DestinationOut keeps dest where the source is transparent.
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.drawImage(0, 0, qimg)
        overlay.update()
        overlay.reset_pen()
        return int(np.count_nonzero(erase_mask))

    def _dynamic_erase(self, image_item, overlay, rgb, shape_mask, keep_rgba,
                       tolerance, x, y, n_shape):
        from PyQt6.QtGui import QPixmap as _QPixmap
        from PyQt6.QtWidgets import QDialog as _QDialog
        dialog = DynamicEraserDialog(
            self.view,
            rgb,
            shape_mask,
            keep_rgba,
            tolerance,
            _QPixmap(overlay.labeling_overlay_pixmap),
            _QPixmap(image_item.get_image_pixmap()),
            model=self,
        )
        if dialog.exec() != _QDialog.DialogCode.Accepted:
            self._status("Eraser: cancelled")
            return
        erase_mask = dialog.get_final_erase_mask()
        if erase_mask is None or not erase_mask.any():
            self._status("Eraser: nothing selected to erase")
            return
        n = self._apply_erase(overlay, erase_mask)
        self._status(f"Eraser: {n} px erased (shape {n_shape} px, "
                     f"tolerance {dialog.get_tolerance()})")
        try:
            self.controller.ml_update_stats()
        except Exception:
            pass
