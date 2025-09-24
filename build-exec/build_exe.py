import os

# How to build, the executable PyImageLabeling

print("Type 'enter' to execute:")
input()

os.system("pyinstaller --onefile --noconsole --name 'PyImageLabeling'"
"--add-data 'config.json;.'"
" --add-data 'parameters.json;.'"
" --add-data 'style.css;.'"
" --add-data 'icons/*.png;icons'"
" --icon 'icons/maia3.ico' __init__.py")
