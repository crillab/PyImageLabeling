
import os

class Utils():

    def __init__(self):
        pass

    def get_icon_path(icon_name):
        # Assuming icons are stored in an 'icons' folder next to the script
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'+os.sep+'icon')
        return os.path.join(icon_dir, f"{icon_name}.png")
    
    def get_style_css():
        return open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"style.css").read()
    
