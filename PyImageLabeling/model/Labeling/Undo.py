from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap, QPen
from PyQt6.QtCore import Qt, QSize
from model.Core import Core

class Undo(Core):
    def __init__(self):
        super().__init__() 
    
    def undo(self):
        if len(self.undo_deque) > 0:
            print("len(self.undo_deque):", len(self.undo_deque))
            self.labeling_overlay_painter.end()
            
            
            self.labeling_overlay_pixmap = self.undo_deque.pop()
            
            self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()

            if len(self.undo_deque) == 0:
                self.undo_deque.append(self.labeling_overlay_pixmap.copy())
                #self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()
            print("deque: ", self.labeling_overlay_pixmap)
            #self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)
            #self.labeling_overlay_painter.end()
            #self.labeling_overlay_painter.begin(self.labeling_overlay_pixmap)
            
            self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)
            self.labeling_overlay_painter.begin(self.labeling_overlay_pixmap)

            #self.zoomable_graphics_view.scene.removeItem(self.labeling_overlay_item)

            #self.labeling_overlay_item = self.view.zoomable_graphics_view.scene.addPixmap(self.labeling_overlay_pixmap)
            #self.labeling_overlay_item.setZValue(3)  


            #self.labeling_overlay_item.setPixmap(element)


            #self.labeling_overlay_painter = QPainter(self.labeling_overlay_pixmap)        
            self.labeling_overlay_painter.setPen(QPen(self.labels[self.current_label]["color"], 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            self.labeling_overlay_painter.setBrush(self.labels[self.current_label]["color"])
            
            print("end deque")

  