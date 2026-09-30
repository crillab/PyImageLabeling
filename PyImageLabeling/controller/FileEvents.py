
from PyImageLabeling.controller.Events import Events



class FileEvents(Events):
    def __init__(self):
        super().__init__()
        
    def set_view(self, view):
        super().set_view(view)

    def set_model(self, model):
        super().set_model(model)
        
    def load(self):
        self.all_events(self.load.__name__)
        self.model.load()
        for button_names in self.view.buttons_image_bar:
            self.view.buttons_image_bar[button_names].setEnabled(True)
        for button_names in self.view.buttons_label_bar_permanent:
            self.view.buttons_label_bar_permanent[button_names].setEnabled(True)
        
        self.move_image() # we active the move button :) 
        self.model.update_icon_file()


    def save(self):
        self.model.save()

    def save_copy(self):
        self.model.save()
        self.model.save_copy()


    def select_image(self, item):
        self.model.select_image(item.file_path)

        if self.model.get_current_label_item() is not None:
            self.model.update_labeling_overlays(self.model.get_current_label_item().get_label_id())

        # avoid re-entrant selection signals (we may already be inside an
        # itemSelectionChanged emission from the file bar)
        try:
            if self.view.file_bar_list.currentItem() is not item:
                self.view.file_bar_list.setCurrentItem(item)
        except Exception:
            pass
        self.model.update_icon_file()

    def next_image(self):
        self.all_events(self.next_image.__name__)
        self.model.next_image()

    def previous_image(self):
        self.all_events(self.previous_image.__name__)
        self.model.previous_image()
