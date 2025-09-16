import os

# How to build, test and publish on pypi a new version:
# - Put the good version in the __init__.py file (variable __VERSION__).
# - This script get the last wheels and publish them on pypi

print("Type 'enter' to execute: 'python -m build ..'")
input()

os.system("python -m build ..")
os.system("mv ../dist/* .")

print("Type 'enter' to publish the wheels on pypi:")
input()
os.system("python3 -m twine upload --skip-existing *.whl")

print("Type 'enter' to delete the whell:")
os.system("rm -rf *.whl")
