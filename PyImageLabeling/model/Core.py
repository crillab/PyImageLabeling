
class Core():

    def __init__(self):
        self.labels = dict()
        self.current_label = None

    def set_view(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut
    
    def new_label(self, data_new_label):
        self.labels[data_new_label["name"]] = data_new_label
        self.set_current_label(data_new_label["name"])

    def set_current_label(self, name):
        self.current_label = name
        print("current_label:", self.current_label)
        
        