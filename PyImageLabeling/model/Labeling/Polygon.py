from model.Core import Core
from PyQt6.QtWidgets import QGraphicsPolygonItem
from PyQt6.QtGui import QPen, QPolygonF
from PyQt6.QtCore import Qt, QPointF, QRectF, QSizeF

HANDLE_SIZE = 8

class PolygonItem(QGraphicsPolygonItem):
    def __init__(self, points, color=Qt.GlobalColor.red):
        super().__init__(QPolygonF(points))
        
        self.pen = QPen(color, 2)
        self.pen.setStyle(Qt.PenStyle.SolidLine)
        self.setPen(self.pen)

        self.setFlags(
            QGraphicsPolygonItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsPolygonItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsPolygonItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.handles = {}
        self.handle_selected = None
        self.update_handles()

    def update_handles(self):
        polygon = self.polygon()
        self.handles = {}
        for i, point in enumerate(polygon):
            self.handles[i] = QRectF(point - QPointF(HANDLE_SIZE/2, HANDLE_SIZE/2), QSizeF(HANDLE_SIZE, HANDLE_SIZE))

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.transparent, 1))
            for handle_rect in self.handles.values():
                painter.drawRect(handle_rect)

    def mousePressEvent(self, event):
        self.handle_selected = None
        for idx, rect in self.handles.items():
            if rect.contains(event.pos()):
                self.handle_selected = idx
                break
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected is not None:
            polygon = self.polygon()
            polygon[self.handle_selected] = event.pos()
            self.setPolygon(polygon)
            self.update_handles()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.handle_selected = None
        super().mouseReleaseEvent(event)


class Polygon(Core):
    def __init__(self):
        super().__init__()
        self.points = []
        self.current_polygon = None
        self.is_drawing = False
        self.color = Qt.GlobalColor.red

    def polygon(self):
        self.checked_button = self.polygon.__name__

    def start_polygon_tool(self, click_position):
        self.view.zoomable_graphics_view.change_cursor("polygon")
        self.color = self.labels[self.current_label]["color"]
        click_point = QPointF(click_position.x(), click_position.y())

        if not self.is_drawing:
            # Start new polygon
            self.is_drawing = True
            self.points = [click_point]

            self.current_polygon = QGraphicsPolygonItem(QPolygonF(self.points))
            pen = QPen(self.color, 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            self.current_polygon.setPen(pen)
            self.current_polygon.setZValue(2)
            self.zoomable_graphics_view.scene.addItem(self.current_polygon)
        else:
            # Add a new point
            self.points.append(click_point)
            self.current_polygon.setPolygon(QPolygonF(self.points))

    def end_polygon_tool(self):
        if self.is_drawing and len(self.points) >= 3:
            self.zoomable_graphics_view.scene.removeItem(self.current_polygon)
            final_polygon = PolygonItem(self.points, self.color)
            final_polygon.setZValue(2)
            self.zoomable_graphics_view.scene.addItem(final_polygon)

        # Reset for next polygon
        self.points = []
        self.current_polygon = None
        self.is_drawing = False
