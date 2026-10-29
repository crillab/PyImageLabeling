# refactor/model-decomposition — slice log

## Done
- Slice 1: `CompactUndoEntry` -> `model/Undo.py` (backward re-export kept).
- Slice 2: `LabelingOverlay` -> `model/LabelingOverlay.py`.
- Slice 3: `ImageItem` -> `model/ImageItem.py`.
- Slice 4: `LabelItem` -> `model/LabelItem.py`.
- `Core.py` shrank from 74 KB to ~38 KB (1 class + 4 helpers).

## Behaviour guarantees
- Backward-compat re-exports (`from PyImageLabeling.model.Core import ...`) kept, so
  `Tests/test_no_undefined_names`, `conftest.reset_overlay`, etc. unmodified.
- `tests/test_no_undefined_names.py` + suite green after every slice: 146 passed / 1 skipped.

## Pending slices
5. Move `path_hash`, `mask_image_base`, `mask_file_name`, `image_base_from_mask_name` to
   `Utils` (remove `Core`'s re-import friction; align with File/Manager callers).
6. Extract `ImageCatalog` from `Core` (file_paths, image_items, icon_button_files)
   to break `Core`'s dual responsibility.
7. Extract `LabelRegistry` (label_items, static IDs) — currently singleton state on `LabelItem`.
8. Extract `OverlaySaveOrchestrator` (update_color / update_thickness / overlays saving).
9. Remove the backward re-export shims + rename `Core.py` -> `Model.py`.
10. Promote `Shape` data from model to *ImageItem* persistence (decouple from process).

## How to continue
- Each slice: create module, re-export in Core for compat, run
  `check_undefined_names` + full suite, commit on `refactor/model-decomposition`.
- Only merge when slice tests green + behavior identical (visual checks if needed).