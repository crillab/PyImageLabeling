from PyQt6.QtCore import Qt, QPointF, QRectF, QPoint, QRect
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItem, QDialog
from PyImageLabeling.model.Core import Core
import math
from PyImageLabeling.model.Utils import Utils
import numpy
from collections import deque
import numpy as np
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
        # for other_labeling_overlay_pixmap in self.core.get_current_image_item().get_labeling_overlay_pixmaps():
        #     painter.drawPixmap(QRect(0, 0, self.size, self.size), other_labeling_overlay_pixmap, QRect(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.size, self.size))
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

    def eraser(self):
        self.checked_button = self.eraser.__name__      

    def start_eraser(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("eraser")
        
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        self.size_eraser_brush = Utils.load_parameters()["eraser"]["size"] 
        self.absolute_mode = Utils.load_parameters()["eraser"]["absolute_mode"]
        self.eraser_mode = Utils.load_parameters()["eraser"].get("mode", "original")
        self.color = self.get_current_label_item().get_color()

        if self.eraser_mode == "intelligent":
            self.intelligent_erase(self.current_position_x, self.current_position_y)
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

    def intelligent_erase(self, x, y):

        overlay = self.get_current_image_item().get_labeling_overlay()
        pixmap = overlay.labeling_overlay_pixmap
        image_pixmap = self.get_current_image_item().get_image_pixmap()

        w, h = image_pixmap.width(), image_pixmap.height()
        if not (0 <= x < w and 0 <= y < h):
            return

        # --- Convert image to numpy ---
        image = image_pixmap.toImage()
        ptr = image.bits()
        ptr.setsize(w * h * 4)
        img_arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4))

        # --- Convert overlay to numpy ---
        overlay_img = pixmap.toImage()
        ptr_overlay = overlay_img.bits()
        ptr_overlay.setsize(w * h * 4)
        mask_arr = np.frombuffer(ptr_overlay, dtype=np.uint8).reshape((h, w, 4))

        # --- Params ---
        params = Utils.load_parameters()["eraser"]
        tolerance = params.get("tolerance", 10)
        dynamic_adjust = params.get("dynamic_adjust", False)

        keep_color = QColor(params.get("keep_color", "#0000FF"))
        keep_rgba = np.array([
            keep_color.red(),
            keep_color.green(),
            keep_color.blue(),
            keep_color.alpha()
        ])

        # --- Shape mask ---
        mask_alpha = mask_arr[..., 3] > 0
        shape_mask = np.zeros((h, w), dtype=bool)
        self.flood_fill_span(mask_alpha, shape_mask, x, y)

        if not np.any(shape_mask):
            return

        # ==============================
        # 🟢 NON-DYNAMIC (UNCHANGED)
        # ==============================
        if not dynamic_adjust:

            diff = np.abs(img_arr.astype(np.int16) - keep_rgba.astype(np.int16))
            match_mask = np.all(diff <= tolerance, axis=2)
            erase_mask = shape_mask & (~match_mask)

            overlay.recreate_painter()
            painter = overlay.get_painter()

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.setPen(QPen(Qt.GlobalColor.black, 1))

            path = QPainterPath()
            ys, xs = np.where(erase_mask)
            for y_pixel, x_pixel in zip(ys, xs):
                path.addRect(x_pixel, y_pixel, 1, 1)

            painter.drawPath(path)

            overlay.update()
            overlay.reset_pen()
            return

        # ==============================
        # 🔵 DYNAMIC MODE (SAFE)
        # ==============================

        original_pixmap = QPixmap(pixmap)

        dialog = DynamicEraserDialog(
            self.view,
            img_arr,
            shape_mask,
            keep_rgba,
            tolerance,
            original_pixmap
        )

        result = dialog.exec()

        if result != QDialog.DialogCode.Accepted:
            return

        erase_mask = dialog.get_final_erase_mask()

        # 🔥 CRITICAL FIX
        overlay.recreate_painter()

        painter = overlay.get_painter()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))

        path = QPainterPath()
        ys, xs = np.where(erase_mask)
        for y_pixel, x_pixel in zip(ys, xs):
            path.addRect(x_pixel, y_pixel, 1, 1)

        painter.drawPath(path)

        overlay.update()
        overlay.reset_pen()

    def flood_fill_span(self, mask, shape_mask, start_x, start_y):
        """Span-based flood fill to extract contiguous shape from mask."""
        h, w = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        stack = deque()
        stack.append((start_x, start_y))

        while stack:
            x, y = stack.pop()
            if x < 0 or x >= w or y < 0 or y >= h:
                continue
            if not mask[y, x] or visited[y, x]:
                continue

            # Expand left
            x_left = x
            while x_left - 1 >= 0 and mask[y, x_left - 1] and not visited[y, x_left - 1]:
                x_left -= 1

            # Expand right
            x_right = x
            while x_right + 1 < w and mask[y, x_right + 1] and not visited[y, x_right + 1]:
                x_right += 1

            # Mark visited and shape_mask
            visited[y, x_left:x_right+1] = True
            shape_mask[y, x_left:x_right+1] = True

            # Check line above and below
            for ny in (y-1, y+1):
                if 0 <= ny < h:
                    xi = x_left
                    while xi <= x_right:
                        if mask[ny, xi] and not visited[ny, xi]:
                            sx = xi
                            while sx + 1 <= x_right and mask[ny, sx + 1] and not visited[ny, sx + 1]:
                                sx += 1
                            stack.append((sx, ny))
                            xi = sx + 1
                        else:
                            xi += 1