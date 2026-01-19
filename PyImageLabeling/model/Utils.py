
# import os
# import json

# class Utils():

#     def __init__(self):
#         pass

#     def get_icon_path(icon_name):
#         # Assuming icons are stored in an 'icons' folder next to the script
#         icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'+os.sep+'icons')
#         icon_path = os.path.join(icon_dir, f"{icon_name}.png")
#         if not os.path.exists(icon_path):
#             raise FileNotFoundError("The icon is not found: ", icon_path)
#         return icon_path
    
#     def get_style_css():
#         return open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"style.css").read()
    
#     def get_config():
#         with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"config.json", 'r', encoding='utf-8') as file:
#             data = json.load(file)
#         return data
    
#     def load_parameters():
#         with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"parameters.json", 'r', encoding='utf-8') as file:
#             data = json.load(file)
#         return data
    
#     def save_parameters(data):
#         with open(os.path.dirname(os.path.abspath(__file__))+os.sep+".."+os.sep+"parameters.json", 'w') as fp:
#             json.dump(data, fp)


#     def color_to_stylesheet(color):
#         return f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); color: {'white' if color.lightness() < 128 else 'black'};"
        
#     def compute_diagonal(x_1, y_1, x_2, y_2):
#         return ((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) ** 0.5


### set like this to create the exe ###
import os
import json
import sys
import shutil

class Utils:

    __version__ = "1.0.6"

    @staticmethod
    def get_base_dir():
        """Return project root, compatible with PyInstaller."""
        if getattr(sys, "_MEIPASS", None):
            # Running in PyInstaller bundle
            return sys._MEIPASS
        else:
            # Running normally from source
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def get_icon_path(icon_name):
        icon_dir = os.path.join(Utils.get_base_dir(), "icons")
        icon_path = os.path.join(icon_dir, f"{icon_name}.png")
        if not os.path.exists(icon_path):
            raise FileNotFoundError("The icon is not found:", icon_path)
        return icon_path

    @staticmethod
    def get_style_css():
        css_path = os.path.join(Utils.get_base_dir(), "style.css")
        with open(css_path, 'r', encoding='utf-8') as file:
            return file.read()

    @staticmethod
    def get_config():
        config_path = os.path.join(Utils.get_base_dir(), "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config not found at {config_path}")
        with open(config_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    
    @staticmethod
    def save_parameters(data):
        param_path = os.path.join(Utils.get_base_dir(), "parameters.json")
        with open(param_path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, indent=4)
            
    @staticmethod
    def load_parameters():
        default_param_path = os.path.join(Utils.get_base_dir(), "default_parameters.json")
        param_path = os.path.join(Utils.get_base_dir(), "parameters.json")

        # If parameters.json does not exist, copy from default
        if not os.path.exists(param_path):
            if not os.path.exists(default_param_path):
                raise FileNotFoundError(f"Default parameters not found at {default_param_path}")
            shutil.copyfile(default_param_path, param_path)

        # Load both files
        with open(default_param_path, 'r', encoding='utf-8') as default_file:
            default_data = json.load(default_file)
        with open(param_path, 'r', encoding='utf-8') as param_file:
            user_data = json.load(param_file)

        # Recursively update missing keys in user_data from default_data
        def update_missing_keys(default, user):
            for key, value in default.items():
                if key not in user:
                    user[key] = value
                elif isinstance(value, dict) and isinstance(user[key], dict):
                    update_missing_keys(value, user[key])
            return user

        updated_data = update_missing_keys(default_data, user_data)

        # Save the updated data back to parameters.json
        with open(param_path, 'w', encoding='utf-8') as fp:
            json.dump(updated_data, fp, indent=4)

        return updated_data

    @staticmethod
    def color_to_stylesheet(color):
        return f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); " \
               f"color: {'white' if color.lightness() < 128 else 'black'};"

    @staticmethod
    def compute_diagonal(x_1, y_1, x_2, y_2):
        return ((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) ** 0.5
    
    @staticmethod
    def get_version():
        return Utils.__version__
    
    @staticmethod
    def update_version():
        major, minor, patch = map(int, Utils.__version__.split("."))
        patch += 1
        Utils.__version__ = f"{major}.{minor}.{patch}"
        return Utils.__version__