import os
import platform
from PyImageLabeling.model.Utils import Utils

print("Do you want to update the version? (Y/N): ", end="")
response = input().strip().upper()

if response == 'Y' or response == 'YES':
    Utils.update_version()
    print("Version updated!")
elif response == 'N' or response == 'NO':
    print("Version not updated.")
else:
    print("Invalid input. Version not updated.")

print("\nPress Enter to build executable:")
input()

version = Utils.get_version()
exe_name = f"PyImageLabeling_v{version}"

# Use the correct separator based on the OS
separator = ';' if platform.system() == 'Windows' else ':'

command = (
    f'pyinstaller --onefile --noconsole '
    f'--name "{exe_name}" '
    f'--add-data "PyImageLabeling/config.json{separator}." '
    f'--add-data "PyImageLabeling/default_parameters.json{separator}." '
    f'--add-data "PyImageLabeling/style.css{separator}." '
    f'--add-data "PyImageLabeling/icons/*.png{separator}icons" '
    f'--icon "PyImageLabeling/icons/maia3.ico" '
    f'--strip '  
    f'PyImageLabeling/__main__.py'
)

print(f"\nExecuting: {command}\n")
os.system(command)