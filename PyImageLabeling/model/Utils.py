
import os
import json

class Utils():

    def __init__(self):
        pass

    def get_icon_path(icon_name):
        # Assuming icons are stored in an 'icons' folder next to the script
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'+os.sep+'icons')
        icon_path = os.path.join(icon_dir, f"{icon_name}.png")
        if not os.path.exists(icon_path):
            raise FileNotFoundError("The icon is not found: ", icon_path)
        return icon_path
    
    def get_style_css():
        return open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"style.css").read()
    
    def get_config():
        with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"config.json", 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    
    def load_parameters():
        with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"parameters.json", 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    
    def save_parameters(data):
        with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"parameters.json", 'w') as fp:
            json.dump(data, fp)


    def color_to_stylesheet(color):
        return f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); color: {'white' if color.lightness() < 128 else 'black'};"
        
    def compute_diagonal(x_1, y_1, x_2, y_2):
        return ((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) ** 0.5


### set like this to create the exe ###
# import os
# import json
# import sys

# class Utils:

#     @staticmethod
#     def get_base_dir():
#         """Return project root, compatible with PyInstaller."""
#         if getattr(sys, "_MEIPASS", None):
#             # Running in PyInstaller bundle
#             return sys._MEIPASS
#         else:
#             # Running normally from source
#             return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#     @staticmethod
#     def get_icon_path(icon_name):
#         icon_dir = os.path.join(Utils.get_base_dir(), "icons")
#         icon_path = os.path.join(icon_dir, f"{icon_name}.png")
#         if not os.path.exists(icon_path):
#             raise FileNotFoundError("The icon is not found:", icon_path)
#         return icon_path

#     @staticmethod
#     def get_style_css():
#         css_path = os.path.join(Utils.get_base_dir(), "style.css")
#         with open(css_path, 'r', encoding='utf-8') as file:
#             return file.read()

#     @staticmethod
#     def get_config():
#         config_path = os.path.join(Utils.get_base_dir(), "config.json")
#         if not os.path.exists(config_path):
#             raise FileNotFoundError(f"Config not found at {config_path}")
#         with open(config_path, 'r', encoding='utf-8') as file:
#             return json.load(file)

#     @staticmethod
#     def load_parameters():
#         param_path = os.path.join(Utils.get_base_dir(), "parameters.json")
#         if not os.path.exists(param_path):
#             raise FileNotFoundError(f"Parameters not found at {param_path}")
#         with open(param_path, 'r', encoding='utf-8') as file:
#             return json.load(file)

#     @staticmethod
#     def save_parameters(data):
#         param_path = os.path.join(Utils.get_base_dir(), "parameters.json")
#         with open(param_path, 'w', encoding='utf-8') as fp:
#             json.dump(data, fp, indent=4)

#     @staticmethod
#     def color_to_stylesheet(color):
#         return f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); " \
#                f"color: {'white' if color.lightness() < 128 else 'black'};"

#     @staticmethod
#     def compute_diagonal(x_1, y_1, x_2, y_2):
#         return ((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) ** 0.5
