import os
import platform
from PyImageLabeling.model.Utils import Utils
import shutil

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

if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists(f'{exe_name}.spec'):
    os.remove(f'{exe_name}.spec')

# Use the correct separator based on the OS
separator = ';' if platform.system() == 'Windows' else ':'

script_dir = os.path.dirname(os.path.abspath(__file__))
upx_path = os.path.join(script_dir, 'upx-5.1.0-win64', 'upx-5.1.0-win64')

command = (
    f'pyinstaller --onefile --noconsole '
    f'--optimize 2 '
    f'--strip '
    f'--upx-dir="{upx_path}" '
    f'--upx-exclude "vcruntime140.dll" '
    f'--name "{exe_name}" '
    f'--add-data "PyImageLabeling/config.json{separator}." '
    f'--add-data "PyImageLabeling/default_parameters.json{separator}." '
    f'--add-data "PyImageLabeling/version.json{separator}." '
    f'--add-data "PyImageLabeling/style.css{separator}." '
    f'--add-data "PyImageLabeling/icons/*.png{separator}icons" '
    f'--icon "PyImageLabeling/icons/maia3.ico" '
    f'PyImageLabeling/__main__.py'
)

os.system(command)