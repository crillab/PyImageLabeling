"""Reading image files with OpenCV the way the view shows them."""
import cv2


def imread(path, flags=cv2.IMREAD_COLOR):
    """cv2.imread, without applying the EXIF orientation of the file.

    The view shows the images through Qt, which does not apply that tag:
    the masks are painted on the pixels as they are stored in the file.
    OpenCV applies it by default, so an image saved with an orientation
    tag (a photo, or an image turned in a viewer that only sets the tag)
    was trained on and predicted rotated against its own masks.
    """
    if flags >= 0:   # IMREAD_UNCHANGED (-1) never applies it
        flags |= cv2.IMREAD_IGNORE_ORIENTATION
    return cv2.imread(path, flags)
