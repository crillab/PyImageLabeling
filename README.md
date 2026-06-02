# PyImageLabeling

[![PyPI version](https://img.shields.io/pypi/v/PyImageLabeling.svg?color=green)](https://pypi.org/project/PyImageLabeling/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/crillab/PyImageLabeling/tree/master?tab=MIT-1-ov-file#)

- **GitHub Repository**: [View codesource](https://github.com/crillab/PyImageLabeling).
- **PyPI**: [Install via pip](https://pypi.org/project/PyImageLabeling/).

PyImageLabeling is a powerful tool with a **user-friendly interface** based on PyQT6 for creating image masks. These **labeled images** are used in the creation of **machine learning models** dedicated to **computer vision tasks**. 

Two types of labeling are available: 
- **Pixel-by-Pixel**: allows to use the pixel-level precision (paintbrush, magic pen, contour filling).
- **Geometric shapes**: allows to use different geometric shapes (polygon, rectangle, ellipse) for labeling.

<figure>
  <img src="https://i.postimg.cc/VsxcS6Jg/screenshot1.png" alt="PyImageLabeling Interface" width="800"/>
  <figcaption>Overview of PyImageLabeling in the context of an application related to pancreatic cancer.</figcaption>
</figure>

<br><br>
<figure>
  <img src="https://i.postimg.cc/gJhN1YGc/screenshot2.png" alt="PyImageLabeling Interface" width="800"/>
  <figcaption>Overview of PyImageLabeling with the <a href="https://www.kaggle.com/datasets/faizalkarim/flood-area-segmentation">Flood Area Segmentation</a> dataset.</figcaption>
</figure>

## Installation and Run

Note that you need first Python 3 (version 3.12, or later) to be installed. You can do it, for example, from [Python.org](www.python.org).

### PyPi installation (Windows, Mac and Linux)

Check whether you have the last version of PyPi:

```bash
python3 -m pip install -U pip
```

Install PyImageLabeling: 

```bash
python3 -m pip install -U PyImageLabeling
```

To launch PyImageLabeling:

```bash
python3 -m PyImageLabeling
```

### Executable ".exe" (Windows)

You can download the [Windows executable](https://github.com/crillab/PyImageLabeling/releases/tag/exec). 
Just double-click on the executable file to launch PyImageLabeling.   


### Github Installation (Windows, Mac and Linux)

Here is an illustration for Linux. We assume that Python 3 is installed, and consequently ‘pip3’ is also installed. In a console, type:

```bash
git clone https://github.com/crillab/PyImageLabeling.git
```

You may need to update the environment variable ‘PYTHONPATH’, by typing for example:
```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/.."
```

Get the last version of pip:
```bash
python3 -m pip install --upgrade pip
```

Executes the pyproject.toml inside the PyImageLabeling directory and installs dependencies ("numpy", "pyqt6", "opencv-python", "pillow", "matplotlib").
```bash
python3 -m pip install -e .
```

To launch PyImageLabeling:

```bash
python3 -m PyImageLabeling
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/crillab/PyImageLabeling/tree/master?tab=MIT-1-ov-file#) file for details.

## Use Cases

- **Computer Vision**: Create training datasets for object detection and segmentation
- **Medical Imaging**: Annotate medical scans and diagnostic images
- **Autonomous Vehicles**: Label road scenes and traffic elements
- **Agriculture**: Mark crop areas and plant health indicators
- **Quality Control**: Identify defects and areas of interest in industrial applications

---
