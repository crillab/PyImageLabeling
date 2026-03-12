import json
from setuptools import setup

# Lit la version depuis un fichier JSON
with open("PyImageLabeling/version.json", "r") as f:
    version = json.load(f)["version"]

setup(version=version)