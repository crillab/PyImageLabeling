from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsScene, QGraphicsItem, QMessageBox
import cv2
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter, QPixmap, QColor, QRadialGradient
from PyQt6.QtCore import QPointF, Qt, QRectF, QRect
from collections import deque
from PyImageLabeling.model.Utils import Utils

class CompactBrushStroke:
    """
    Stockage compact du trait inspiré de CompactUndoEntry.
    Stocke uniquement les centres des stamps, pas tous les pixels.
    """
    def __init__(self, brush_stamp, color, size):
        self.brush_stamp = brush_stamp  # Le stamp du brush (créé une seule fois)
        self.color = color
        self.size = size
        self.half_size = size // 2
        
        # Stockage compact: seulement les positions des centres
        self.centers_x = []
        self.centers_y = []
        
        # Bounding box
        self.min_x = None
        self.max_x = None
        self.min_y = None
        self.max_y = None
    
    def add_point(self, x, y):
        """Ajoute un point au trait (stockage léger)"""
        self.centers_x.append(x)
        self.centers_y.append(y)
        
        # Update bounds
        if self.min_x is None:
            self.min_x = x - self.half_size
            self.max_x = x + self.half_size
            self.min_y = y - self.half_size
            self.max_y = y + self.half_size
        else:
            self.min_x = min(self.min_x, x - self.half_size)
            self.max_x = max(self.max_x, x + self.half_size)
            self.min_y = min(self.min_y, y - self.half_size)
            self.max_y = max(self.max_y, y + self.half_size)
    
    def get_bounds(self):
        """Retourne le bounding rect"""
        if self.min_x is None:
            return QRectF(0, 0, 1, 1)
        return QRectF(
            self.min_x, self.min_y,
            self.max_x - self.min_x,
            self.max_y - self.min_y
        )
    
    def render_full(self, painter, opacity=1.0):
        """Rend le trait complet (utilisé à la fin)"""
        painter.setOpacity(opacity)
        for x, y in zip(self.centers_x, self.centers_y):
            stamp_x = x - self.half_size
            stamp_y = y - self.half_size
            painter.drawPixmap(stamp_x, stamp_y, self.brush_stamp)
    
    def render_incremental(self, painter, from_index, opacity=1.0):
        """Rend seulement les nouveaux points depuis from_index"""
        painter.setOpacity(opacity)
        for i in range(from_index, len(self.centers_x)):
            x = self.centers_x[i]
            y = self.centers_y[i]
            stamp_x = x - self.half_size
            stamp_y = y - self.half_size
            painter.drawPixmap(stamp_x, stamp_y, self.brush_stamp)
    
    def get_point_count(self):
        return len(self.centers_x)


class PaintBrushItem(QGraphicsItem):
    """
    Version optimisée avec:
    1. Rendu incrémental (ne redessine que les nouveaux points)
    2. Cache du rendu précédent
    3. Stockage compact des données
    """

    def __init__(self, core, x, y, color, size, brush_type="circle"):
        super().__init__()
        
        self.core = core
        self.color = color
        self.size = size
        self.brush_type = brush_type
        
        # Créer le brush stamp une seule fois
        self.brush_stamp = self._create_brush_stamp()
        
        # Stockage compact du trait
        self.stroke = CompactBrushStroke(self.brush_stamp, color, size)
        self.stroke.add_point(int(x), int(y))
        
        # Cache du rendu pour éviter de redessiner tout
        self.cached_render = None
        self.last_rendered_count = 0
        
        # Overlay painter pour le dessin final
        self.overlay_painter = self.core.get_current_image_item().get_labeling_overlay().get_painter()
        
        # Flags pour optimiser les updates
        self.needs_full_redraw = True
    
    def _create_brush_stamp(self):
        """Crée le stamp du brush (appelé une seule fois)"""
        stamp = QPixmap(self.size, self.size)
        stamp.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(stamp)
        center = int(self.size / 2)
        self._draw_brush_shape(painter, center, center)
        painter.end()
        
        return stamp
    
    def _draw_brush_shape(self, painter, center_x, center_y):
        """Dessine la forme du brush selon le type"""
        
        if self.brush_type == "circle":
            pen = QPen(self.color, self.size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPoint(center_x, center_y)
        
        elif self.brush_type == "square":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            half_size = self.size // 2
            painter.drawRect(center_x - half_size, center_y - half_size, self.size, self.size)
        
        elif self.brush_type == "diamond":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            half_size = self.size // 2
            path.moveTo(center_x, center_y - half_size)
            path.lineTo(center_x + half_size, center_y)
            path.lineTo(center_x, center_y + half_size)
            path.lineTo(center_x - half_size, center_y)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "star":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            outer_radius = self.size // 2
            inner_radius = outer_radius // 2
            
            for i in range(10):
                angle = (i * 36 - 90) * np.pi / 180
                radius = outer_radius if i % 2 == 0 else inner_radius
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "triangle":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            half_size = self.size // 2
            path.moveTo(center_x, center_y - half_size)
            path.lineTo(center_x + half_size, center_y + half_size)
            path.lineTo(center_x - half_size, center_y + half_size)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "cross":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            thickness = self.size // 3
            half_size = self.size // 2
            painter.drawRect(center_x - thickness//2, center_y - half_size, thickness, self.size)
            painter.drawRect(center_x - half_size, center_y - thickness//2, self.size, thickness)
        
        elif self.brush_type == "x":
            painter.setPen(QPen(self.color, max(2, self.size // 5), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            half_size = self.size // 2
            painter.drawLine(center_x - half_size, center_y - half_size, center_x + half_size, center_y + half_size)
            painter.drawLine(center_x + half_size, center_y - half_size, center_x - half_size, center_y + half_size)
        
        elif self.brush_type == "hexagon":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            radius = self.size // 2
            for i in range(6):
                angle = (i * 60) * np.pi / 180
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)
        
        elif self.brush_type == "spray":
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            np.random.seed(int(center_x + center_y))
            num_dots = max(10, self.size // 2)
            radius = self.size // 2
            for _ in range(num_dots):
                angle = np.random.uniform(0, 2 * np.pi)
                dist = np.random.uniform(0, radius)
                dot_x = center_x + dist * np.cos(angle)
                dot_y = center_y + dist * np.sin(angle)
                dot_size = max(1, self.size // 10)
                painter.drawEllipse(QPointF(dot_x, dot_y), dot_size, dot_size)
        
        elif self.brush_type == "soft":
            gradient = QRadialGradient(center_x, center_y, self.size // 2)
            gradient.setColorAt(0, self.color)
            transparent = QColor(self.color)
            transparent.setAlpha(0)
            gradient.setColorAt(1, transparent)
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(center_x, center_y), self.size // 2, self.size // 2)
        
        else:
            pen = QPen(self.color, self.size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPoint(center_x, center_y)
    
    def add_point(self, x, y):
        """
        Ajoute un point de manière ultra-légère.
        Stocke juste les coordonnées, pas de pixmap.
        """
        self.stroke.add_point(int(x), int(y))
        self.needs_full_redraw = False  # On fera juste un rendu incrémental
    
    def boundingRect(self):
        """Retourne le bounding rect du trait"""
        return self.stroke.get_bounds()
    
    def paint(self, painter, option, widget):
        """
        OPTIMISATION CLEF: Rendu incrémental.
        Ne redessine que les nouveaux points depuis le dernier paint.
        """
        bounds = self.stroke.get_bounds()
        current_count = self.stroke.get_point_count()
        
        if self.needs_full_redraw or self.cached_render is None:
            # Premier rendu ou besoin de redessiner tout
            self.cached_render = QPixmap(int(bounds.width()), int(bounds.height()))
            self.cached_render.fill(Qt.GlobalColor.transparent)
            
            cache_painter = QPainter(self.cached_render)
            # Translate pour dessiner dans le cache relatif à bounds
            cache_painter.translate(-bounds.x(), -bounds.y())
            self.stroke.render_full(cache_painter, self.core.get_current_image_item().get_labeling_overlay().get_opacity())
            cache_painter.end()
            
            self.last_rendered_count = current_count
            self.needs_full_redraw = False
            
        elif current_count > self.last_rendered_count:
            # Rendu incrémental: ajouter seulement les nouveaux points
            # On garde l'ancien cache et on ajoute les nouveaux points dessus
            new_bounds = self.stroke.get_bounds()
            
            if new_bounds != bounds:
                # Le bounding box a grandi, il faut agrandir le cache
                new_cache = QPixmap(int(new_bounds.width()), int(new_bounds.height()))
                new_cache.fill(Qt.GlobalColor.transparent)
                
                cache_painter = QPainter(new_cache)
                # Copier l'ancien cache
                cache_painter.drawPixmap(
                    int(bounds.x() - new_bounds.x()), 
                    int(bounds.y() - new_bounds.y()), 
                    self.cached_render
                )
                # Ajouter les nouveaux points
                cache_painter.translate(-new_bounds.x(), -new_bounds.y())
                self.stroke.render_incremental(
                    cache_painter, 
                    self.last_rendered_count,
                    self.core.get_current_image_item().get_labeling_overlay().get_opacity()
                )
                cache_painter.end()
                
                self.cached_render = new_cache
                bounds = new_bounds
            else:
                # Le bounding box n'a pas changé, on peut dessiner directement
                cache_painter = QPainter(self.cached_render)
                cache_painter.translate(-bounds.x(), -bounds.y())
                self.stroke.render_incremental(
                    cache_painter, 
                    self.last_rendered_count,
                    self.core.get_current_image_item().get_labeling_overlay().get_opacity()
                )
                cache_painter.end()
            
            self.last_rendered_count = current_count
        
        # Dessiner le cache complet (opération très rapide)
        painter.drawPixmap(int(bounds.x()), int(bounds.y()), self.cached_render)
    
    def commit_to_overlay(self):
        """
        Dessine le trait final sur l'overlay.
        Appelé à la fin du mouvement.
        """
        self.stroke.render_full(self.overlay_painter, opacity=1.0)


class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.last_position_x, self.last_position_y = None, None
        self.point_spacing = 2
        self.paint_brush_item = None
        
        # Optimisation: batch les updates de la scène
        self.update_batch_size = 5  # Update tous les 5 points
        self.points_since_update = 0

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__      

    def start_paint_brush(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("paint")
        
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        params = Utils.load_parameters()
        self.size_paint_brush = params["paint_brush"]["size"]
        self.brush_type = params["paint_brush"].get("brush_type", "circle")
        self.color = self.get_current_label_item().get_color()
        
        # Créer l'item de brush optimisé
        self.paint_brush_item = PaintBrushItem(
            self, 
            self.current_position_x, 
            self.current_position_y, 
            self.color, 
            self.size_paint_brush, 
            self.brush_type
        )
        self.paint_brush_item.setZValue(2)
        self.zoomable_graphics_view.scene.addItem(self.paint_brush_item)
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y
        self.drawn_points = [(self.current_position_x, self.current_position_y)]
        self.points_since_update = 0

    def move_paint_brush(self, current_position):
        if self.paint_brush_item is None:
            return
            
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        # Vérifier l'espacement minimal
        if Utils.compute_diagonal(self.current_position_x, self.current_position_y, 
                                   self.last_position_x, self.last_position_y) < self.point_spacing:
            return 
        
        # Ajouter le point (opération ultra-légère, juste stockage coordonnées)
        self.drawn_points.append((self.current_position_x, self.current_position_y))
        self.paint_brush_item.add_point(self.current_position_x, self.current_position_y)
        
        # Batch les updates pour réduire l'overhead
        self.points_since_update += 1
        if self.points_since_update >= self.update_batch_size:
            self.paint_brush_item.update()
            self.points_since_update = 0
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def _is_shape_closed(self, points, tolerance=10):
        """Vérifie si le trait forme une boucle fermée"""
        if len(points) < 10:
            return False
        first, last = points[0], points[-1]
        dist = np.hypot(first[0] - last[0], first[1] - last[1])
        adjusted_tolerance = tolerance + self.size_paint_brush
        return dist < adjusted_tolerance

    def _fill_closed_shape(self, points):
        """Remplit une forme fermée"""
        path = QPainterPath()
        if not points:
            return
        
        path.moveTo(QPointF(points[0][0], points[0][1]))
        
        for x, y in points[1:]:
            path.lineTo(QPointF(x, y))
        
        path.closeSubpath()
        
        painter = self.get_current_image_item().get_labeling_overlay().get_painter()
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        
        self.get_current_image_item().update_labeling_overlay()

    def end_paint_brush(self):
        if self.paint_brush_item is None:
            return
        
        # Update final pour afficher les derniers points
        self.paint_brush_item.update()
        
        # Commit le trait sur l'overlay (dessin final une seule fois)
        self.paint_brush_item.commit_to_overlay()

        # Mettre à jour l'overlay
        self.get_current_image_item().update_labeling_overlay()

        # Retirer l'item de preview de la scène
        self.zoomable_graphics_view.scene.removeItem(self.paint_brush_item)
        self.paint_brush_item = None

        # Vérifier si la forme est fermée
        if hasattr(self, "drawn_points") and self._is_shape_closed(self.drawn_points):
            reply = QMessageBox.question(
                self.view,
                "Fill Shape",
                "Detected a closed shape. Do you want to fill it automatically?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._fill_closed_shape(self.drawn_points)
        
        self.controller.ml_update_stats()