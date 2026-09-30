
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
    def _write_json_atomic(path, data):
        """Write JSON without ever leaving a truncated file behind.

        Opening the target with 'w' empties it first, so a crash (or a
        json.dump error) between that and the flush left a 0-byte
        parameters.json, which then made the app fail to start.
        """
        tmp_path = path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, indent=4)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp_path, path)

    @staticmethod
    def save_parameters(data):
        param_path = os.path.join(Utils.get_base_dir(), "parameters.json")
        Utils._write_json_atomic(param_path, data)

    @staticmethod
    def load_parameters():
        default_param_path = os.path.join(Utils.get_base_dir(), "default_parameters.json")
        param_path = os.path.join(Utils.get_base_dir(), "parameters.json")

        if not os.path.exists(default_param_path):
            raise FileNotFoundError(f"Default parameters not found at {default_param_path}")

        # If parameters.json does not exist, copy from default
        if not os.path.exists(param_path):
            shutil.copyfile(default_param_path, param_path)

        # Load both files
        with open(default_param_path, 'r', encoding='utf-8') as default_file:
            default_data = json.load(default_file)

        user_data = None
        try:
            with open(param_path, 'r', encoding='utf-8') as param_file:
                user_data = json.load(param_file)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            # A corrupt/truncated parameters.json must not make the app
            # unbootable: keep it aside and start from the defaults.
            print(f"[Utils] parameters.json unreadable ({e}); "
                  f"falling back to defaults")
            try:
                os.replace(param_path, param_path + ".corrupt")
            except OSError:
                pass
            user_data = {}

        if not isinstance(user_data, dict):
            user_data = {}

        # Recursively update missing keys in user_data from default_data.
        # The user's values must win: default_data is only the fallback.
        def update_missing_keys(default, user):
            changed = False
            for key, value in default.items():
                if key not in user:
                    user[key] = value
                    changed = True
                elif isinstance(value, dict) and isinstance(user[key], dict):
                    changed = update_missing_keys(value, user[key]) or changed
            return changed

        changed = update_missing_keys(default_data, user_data)

        # Only write when the merge really added something: load_parameters()
        # is called on every brush stroke, and rewriting the file each time
        # both wore the disk and widened the corruption window.
        if changed:
            try:
                Utils._write_json_atomic(param_path, user_data)
            except OSError as e:
                print(f"[Utils] could not save parameters.json: {e}")

        return user_data

    @staticmethod
    def color_to_stylesheet(color):
        return f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); " \
               f"color: {'white' if color.lightness() < 128 else 'black'};"

    @staticmethod
    def compute_diagonal(x_1, y_1, x_2, y_2):
        return ((x_1 - x_2) ** 2 + (y_1 - y_2) ** 2) ** 0.5
    
    @staticmethod
    def get_version():
        version_file = os.path.join(Utils.get_base_dir(), "version.json")
        with open(version_file, "r") as fichier:
            data = json.load(fichier)
        return data["version"]
    
    @staticmethod
    def update_version():
        version_file = os.path.join(Utils.get_base_dir(), "version.json")
        with open(version_file, "r") as fichier:
            data = json.load(fichier)
        
        major, minor, patch = map(int, data["version"].split("."))
        patch += 1
        data["version"] = f"{major}.{minor}.{patch}"
        with open(version_file, "w") as file:   
            json.dump(data, file, indent=2)  # indent=2 pour un affichage lisible

        return data["version"]
    