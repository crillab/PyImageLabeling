# refactor/model-decomposition — slice log

Base: `master` @ `08d6f88`. Working branch for the `Model` decomposition.

## Done
- Slice 1: `CompactUndoEntry` -> `model/Undo.py` (backward re-export kept).
- Slice 2: `LabelingOverlay` -> `model/LabelingOverlay.py`.
- Slice 3: `ImageItem` -> `model/ImageItem.py`.
- Slice 4: `LabelItem` -> `model/LabelItem.py`.
- Slice 5: mask-name helpers (`path_hash`, `mask_image_base`, `mask_file_name`,
  `image_base_from_mask_name`, `KEYWORD_SAVE_LABEL`, `PATH_HASH_LEN`,
  `DEFAULT_KEEP_LOADED_IMAGES`) -> `model/Masks.py`.
- Slice 6: geometry tools -> `model/GeometryUpdater.py` (`GeometryUpdaterMixin`).
- Slice 7: `ImageCatalog` -> `model/ImageCatalog.py`; Core's image index
  (`file_paths`, `image_items`, `icon_button_files`) is now a property seam over
  the catalog (zero call-site changes).
- Imports of all consumers migrated to the new modules (no behavior change).
- Slice 9: `Core` -> `Base` (class + module rename, `model/Base.py`);
  `model/Core.py` kept as a backward-compat shim (`Base` +
  re-exports). All internal callers import `Base` directly.
- After every slice: `tests/check_undefined_names.py` = 0 and full suite
  green (146 passed / 1 skipped).

## Pending slices
- `LabelRegistry` (label_items, static IDs) — currently singleton state on `LabelItem`.
- `OverlaySaveOrchestrator` (save / autosave orchestration from `Base`).
- Promote `Shape` data from model to *ImageItem* persistence (decouple from process).
- Optional: drop the `model/Core.py` compat shim once every external consumer
  (scripts, third-party code) is confirmed migrated.

## How to continue
- Each slice: create module, keep re-exports for compat, run
  `python -u tests/check_undefined_names.py PyImageLabeling` + `pytest -q`,
  commit on `refactor/model-decomposition`.
- Only merge when slice tests green + behavior identical (visual checks if needed).
