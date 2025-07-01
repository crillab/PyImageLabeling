
import os
import json

class Utils():

    def __init__(self):
        pass

    def get_icon_path(icon_name):
        # Assuming icons are stored in an 'icons' folder next to the script
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'+os.sep+'icons')
        return os.path.join(icon_dir, f"{icon_name}.png")
    
    def get_style_css():
        return open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"style.css").read()
    
    def get_config():
        with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"config.json", 'r', encoding='utf-8') as file:
            dictionnaire = json.load(file)
        return dictionnaire
