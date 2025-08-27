from PyImageLabeling.controller.Events import Events
from PyImageLabeling.controller.settings.MagicPenSetting import MagicPenSetting
from PyImageLabeling.controller.settings.PaintBrushSetting import PaintBrushSetting
from PyImageLabeling.controller.settings.EraserSetting import EraserSetting
from PyImageLabeling.controller.settings.ContourFillinSetting import ContourFillingSetting
from PyQt6.QtWidgets import QDialog

class LabelingEvents(Events):
    def __init__(self):
        super().__init__()

    ### Buttons events

    def contour_filling(self):
        self.desactivate_buttons_labeling_image_bar(self.contour_filling.__name__)
        self.all_events(self.contour_filling.__name__)
        self.view.zoomable_graphics_view.change_cursor("filling")
        self.model.contour_filling()
        
    def paintbrush(self):
        self.desactivate_buttons_labeling_image_bar(self.paintbrush.__name__)
        self.all_events(self.paintbrush.__name__)
        self.view.zoomable_graphics_view.change_cursor("paint")
        self.model.paint_brush()
    
    def magic_pen(self):
        self.desactivate_buttons_labeling_image_bar(self.magic_pen.__name__)
        self.all_events(self.magic_pen.__name__)
        self.view.zoomable_graphics_view.change_cursor("magic")
        self.model.magic_pen()

    def ellipse(self):
        self.desactivate_buttons_labeling_image_bar(self.ellipse.__name__)
        self.all_events(self.ellipse.__name__)
        print("ellipse")

    def rectangle(self):
        self.desactivate_buttons_labeling_image_bar(self.rectangle.__name__)
        self.all_events(self.rectangle.__name__)
        print("rectangle")
    
    def polygon(self):
        self.desactivate_buttons_labeling_image_bar(self.polygon.__name__)
        self.all_events(self.polygon.__name__)
        print("polygon")

    def undo(self):
        self.all_events(self.undo.__name__)
        self.model.undo()
        
    def eraser(self):
        self.desactivate_buttons_labeling_image_bar(self.eraser.__name__)
        self.all_events(self.eraser.__name__)
        self.view.zoomable_graphics_view.change_cursor("eraser")
        self.model.eraser()
    
    def clear_all(self):
        self.all_events(self.clear_all.__name__)
        self.model.clear_all()

    ### Setting Buttons events

    def contour_filling_setting(self):
        self.all_events(self.contour_filling_setting.__name__)
        contourfillingsetting = ContourFillingSetting(self.view.zoomable_graphics_view, self.view.contour_tolerance)
        contourfillingsetting.open()
        if contourfillingsetting.exec() == QDialog.DialogCode.Accepted: 
            self.view.contour_tolerance = contourfillingsetting.get_settings()
        
    def paintbrush_setting(self):
        self.all_events(self.paintbrush_setting.__name__)
        paintbrushsetting = PaintBrushSetting(self.view.zoomable_graphics_view, self.model)
        paintbrushsetting.open()
    
    def magic_pen_setting(self):
        self.all_events(self.magic_pen_setting.__name__)
        magicpensetting = MagicPenSetting(self.view.zoomable_graphics_view)
        magicpensetting.open()
        
    def ellipse_setting(self):
        self.all_events(self.ellipse_setting.__name__)
        print("ellipse_setting")

    def rectangle_setting(self):
        self.all_events(self.rectangle_setting.__name__)
        print("rectangle_setting")
    
    def polygon_setting(self):
        self.all_events(self.polygon_setting.__name__)
        print("polygon_setting")
   
    def eraser_setting(self):
        self.all_events(self.eraser_setting.__name__)
        erasersetting = EraserSetting(self.view.zoomable_graphics_view)
        erasersetting.open()
   
