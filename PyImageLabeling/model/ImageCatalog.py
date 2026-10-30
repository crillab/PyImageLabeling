class ImageCatalog:
    """Owns the image index: ordered paths, loaded items, icon buttons.

    Base delegates to it through properties, keeping all call-sites unchanged.
    """

    def __init__(self):
        self.file_paths = []
        self.image_items = {}
        self.icon_button_files = {}
