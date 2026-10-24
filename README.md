<p align="center">
  <img src="https://raw.githubusercontent.com/crillab/PyImageLabeling/master/assets/logo.svg" alt="PyImageLabeling logo" width="300"/>
</p>

<div align="center">

[![PyPI downloads](https://img.shields.io/pypi/dm/pyimagelabeling?label=PyPI%20downloads&color=brightgreen)](https://pypistats.org/packages/pyimagelabeling)
[![Exe downloads](https://img.shields.io/github/downloads/crillab/PyImageLabeling/total?label=exe%20downloads&color=brightgreen)](https://github.com/crillab/PyImageLabeling/releases/latest)
[![PyPI version](https://img.shields.io/pypi/v/pyimagelabeling?label=pypi)](https://pypi.org/project/PyImageLabeling/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://pypi.org/project/PyImageLabeling/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](https://github.com/crillab/PyImageLabeling/tree/master?tab=MIT-1-ov-file#)

[![Build Linux](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/build-linux.yml?branch=master&label=Build%20Linux&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/build-linux.yml)
[![Build MacOS](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/build-macos.yml?branch=master&label=Build%20MacOS&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/build-macos.yml)
[![Build Windows](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/build-windows.yml?branch=master&label=Build%20Windows&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/build-windows.yml)
[![Windows exe](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/exe.yml?branch=master&label=Windows%20exe&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/exe.yml)

[![Linux tests](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/tests-linux.yml?branch=master&label=Linux%20tests&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/tests-linux.yml)
[![MacOS tests](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/tests-macos.yml?branch=master&label=MacOS%20tests&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/tests-macos.yml)
[![Windows tests](https://img.shields.io/github/actions/workflow/status/crillab/PyImageLabeling/tests-windows.yml?branch=master&label=Windows%20tests&logo=github)](https://github.com/crillab/PyImageLabeling/actions/workflows/tests-windows.yml)

</div>

# PyImageLabeling

- **Documentation**: [Read the documentation](https://www.cril.univ-artois.fr/pyimagelabeling/).
- **GitHub Repository**: [View codesource](https://github.com/crillab/PyImageLabeling).
- **PyPI**: [Install via pip](https://pypi.org/project/PyImageLabeling/).

PyImageLabeling is a powerful tool with a **user-friendly interface** based on PyQT6 for creating image masks. These **labeled images** are used in the creation of **machine learning models** dedicated to **computer vision tasks**. 

## Features

**Labeling**
- **Pixel-by-pixel**: paintbrush, magic pen (selects similar colors, RGB or HSV tolerance) and contour filling.
- **Geometric shapes**: polygon, rectangle and ellipse.
- **Several labels per image**, each with its own color, opacity and visibility.

**Editing**
- **Smart eraser**: erase freely, or only a color range with an adjustable tolerance.
- **Change labeled area**: move an annotated region to another label.
- **Undo** with a configurable depth, and **Clear All**.

**AI assistance** (optional: models are downloaded from Hugging Face on first use, and the GPU is used when available)
- **SAM Assist**: click to add (+) or remove (−) points, or drag a box, and Segment Anything draws the mask. Presets range from fast to precise, plus a medical model (MedSAM).
- **Text-to-mask**: describe the object in English or French (colors, shapes, position); Grounding DINO finds it and SAM draws the mask.
- **One-shot propagation**: annotate one image and propagate the label to all the others (DINOv2 + SAM, no training), then step through the batch to review and fix it.
- **Train a model on your annotations**: segmentation (ResNet or DINOv2 backbone) and detection; predict the current image, then accept or clear the predictions.
- **Active learning**: *Suggest next to label* jumps to the image the model is least sure about.

**Images and workflow**
- **Image options**: brightness, contrast, gamma, saturation, hue, sharpness, grayscale, color inversion and color replacement, saved as reusable presets.
- **Import existing masks** as labels.
- **Never lose your work**: auto-save, recovery after a crash, and saves that cannot be left half-written; *Help > Crash Report & Logs* shows what happened.
- Menu bar and keyboard shortcuts.

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
pyimagelabeling
```

(`python3 -m PyImageLabeling` works too.)

### Without installing Python yourself: uv (Windows, Mac and Linux)

[uv](https://docs.astral.sh/uv/getting-started/installation/) downloads a suitable Python by itself and installs PyImageLabeling in its own environment:

```bash
uv tool install PyImageLabeling
pyimagelabeling
```

Update later with `uv tool upgrade PyImageLabeling`.

### Executable ".exe" (Windows)

Download `PyImageLabeling_vX.Y.Z.exe` from the [latest release](https://github.com/crillab/PyImageLabeling/releases/latest).
Just double-click on the executable file to launch PyImageLabeling (no Python needed; machine learning runs on the CPU).


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
