from PyQt6.QtGui import QColor
from PyImageLabeling.logging_setup import get_logger

log = get_logger("core.labelitem")


class LabelItem():

    static_label_id = 0
    used_ids = set()

    def __init__(self, name, labeling_mode, color, id = None):
        if id is None:
            while LabelItem.static_label_id in LabelItem.used_ids:
                LabelItem.static_label_id += 1 
            self.label_id = LabelItem.static_label_id
            LabelItem.used_ids.add(self.label_id)
            LabelItem.static_label_id += 1
        else:
            self.label_id = id
            LabelItem.used_ids.add(self.label_id)
            if id >= LabelItem.static_label_id:
                LabelItem.static_label_id = id + 1
        self.name = name
        self.labeling_mode = labeling_mode
        self.color = QColor(color) # The color of labels in the Labeling Overlay
        self.is_visible = True 
        

    def to_dict(self):
        return {"name": self.name, "labeling_mode": self.labeling_mode, "color": [self.color.red(), self.color.green(), self.color.blue()]}

    def get_label_id(self):
        return self.label_id
    
    def get_color(self):
        return self.color
    
    def set_color(self, color):
        self.color = color

    def get_name(self):
       return self.name
    
    def set_name(self, name):
        self.name = name

    def get_labeling_mode(self):
        return self.labeling_mode
    
    def set_labeling_mode(self, labeling_mode):
        self.labeling_mode = labeling_mode

    def set_visible(self, is_visible):
        self.is_visible = is_visible
    
    def get_visible(self):
        return self.is_visible
    
    
