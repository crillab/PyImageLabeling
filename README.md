

PyImageLabeling is designed to assist in the creation of image masks (labeled images) that can be used to train Machine Learning models. 

## Principle

You load a study image and use a variety of tools to annotate key data points. 
Once your work is saved, a save directory will be automatically created in your working folder, containing the mask in PNG format.

## Navigation and control

| Movement          | Function                                     |
| ----------------- | -------------------------------------------- |
| Mouse wheel       | Zoom in/out                                  |
| Left-click + drag | Move the image (only when "Move" is enabled) |
| Arrow keys        | Pan the image in fixed steps                 |

## Tools

| Tool               | Functionality                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| **Load image**     | Load an image from your local system.                                                                  |
| **Load layer**     | Add a layer on top of the loaded image (useful for editing existing masks). Changes are irreversible.  |
| **Unload layer**   | Remove the currently loaded layer.                                                                     |
| **Save**           | Save the current layer with all modifications.                                                         |
| **Move**           | Activate image movement using the mouse. Enabled by default.                                           |
| **Reset**          | Reset zoom and pan to default.                                                                         |
| **Undo**           | Undo the last action.                                                                                  |
| **Opacity**        | Adjust the transparency of the active layer.                                                           |
| **Contour Filling**| Automatically detect and extract shapes from the image. Shapes can be filled by clicking.              |
| **Paintbrush**     | Draw on the image using a customizable brush (size, color). These points feed smart tools.             |
| **Magic Pen**      | Automatically fill shapes based on the clicked pixel's color and tolerance. Uses paint-defined points. |
| **Rectangle**      | Draw rectangles to select areas of interest and assign labels. Saved in the `save` folder.             |
| **Eraser**         | Remove drawn points. Adjustable size and "Absolute" mode allows erasing from loaded layers.            |
| **Clear all**      | Delete all drawn points from the canvas.                                                               |
