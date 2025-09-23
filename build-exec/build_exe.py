import os

# How to build, the executable PyImageLabeling:
# - set Utils and __init__ as saked in comment

print("Type 'enter' to execute:")
input()

os.system("pyinstaller --onefile --noconsole --name 'PyImageLabeling'"
"--add-data 'PyImageLabeling/config.json;.'"
" --add-data 'PyImageLabeling/parameters.json;.'"
" --add-data 'PyImageLabeling/style.css;.'"
" --add-data 'PyImageLabeling/icons/*.png;icons'"
" --icon 'PyImageLabeling/icons/maia3.ico' main.py")
