# Changelog

Each `## <version>` section becomes the text of the GitHub release of that
version: the Release workflow refuses to publish a version without one.

## Unreleased

### Changed
- All `print()` calls in the app have been routed through the new `logging`-based
  setup (`logging_setup.py`); the `ML_VERBOSE` log level now lands in the same
  stream (stdout → stderr). `PYIMAGELABELING_LOG_LEVEL` selects the level.
- `torch.load` now sets `weights_only=True`, freezing the safe default below
  torch 2.6.

### Fixed
- Basename-mask name collisions (`dirA/IMG_001.png` vs `dirB/IMG_001.png`, or
  `dup.png` vs `dup.jpg`) no longer overwrite annotations at save time: masks
  are now keyed by a digest of the absolute image path.
- A corrupted image (0-byte or garbage PNG) no longer crashes `save()` and takes
  every other image's annotations down with it.
- Mask writes are now isolated per overlay and per image; a failed write marks
  the image as still unsaved (`Save Error` dialog) so it can be retried.
- `complete_state.json` is merged rather than overwritten: completion ticks from
  another instance working in the same folder survive.
- `select_image` now keeps only the `load.memory_keep_images` most recent images
  in memory (default 8, 0 disables unloading), evicting unsaved work never.
- Settings on a read-only installation fall back to `~/.pyimagelabeling` instead
  of crashing on the first launch with `PermissionError`; unwritable everywhere,
  the app boots on in-memory defaults.

### Added
- `load.memory_keep_images` parameter in `default_parameters.json` (default 8).

## 1.0.14 (2026-10-24)

### New
- **SAM Assist**: click to add (+) or remove (−) points, or drag a box, and Segment Anything draws the mask. Presets range from fast to precise, plus a medical model (MedSAM).
- **Text-to-mask**: describe the object in English or French (colors, shapes, position); Grounding DINO finds it and SAM draws the mask.
- **One-shot propagation**: annotate one image and propagate the label to all the others (DINOv2 + SAM, no training), then *Review batch* to check and fix each one.
- **Active learning**: *Suggest next to label* jumps to the image the model is least sure about.
- **DINOv2 segmentation backbone** for model training, next to ResNet.
- **Import existing masks** into a label.
- **Never lose your work**: auto-save with recovery after a crash, and saves that can no longer be left half-written.
- **Crash report** listing the last actions before a crash (*Help > Crash Report & Logs*).
- **`pyimagelabeling` command** to start the app after `pip install PyImageLabeling`, or after `uv tool install PyImageLabeling` without installing Python yourself.
- Smoother painting.

### Fixed
- Importing existing masks into a label did nothing.
- The label dialog reported an import error that had not happened.
- A trained DINOv2 model never predicted.
- Text-to-mask crashed on the first object found.
- Without network, a failed model download broke every later DINO action until the app was restarted.
- The Windows executable forgot its settings at every launch.
- Deleting several selected polygons at once.
- *Clear All* and undo: undo no longer goes back past a *Clear All*, and the undo depth setting applies everywhere.
- The PyPI package shipped the maintainer's own `parameters.json` (local settings and folder paths) and the test files.

- `SAMEvents` / `SAM2Assistant` UI guards (59 silent catches) now log at
  `DEBUG` instead of swallowing failures quietly.
- Now built and checked automatically for each release, without UPX compression, which caused antivirus false alarms. 284 MB instead of 347 MB.
