from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPixmap, QBrush, QPainter, QColor
from models.OverlayOpacityDialog import OverlayOpacityDialog

class OverlayTool:
    def add_overlay(self, overlay_pixmap):
        """
        Add an overlay layer on top of the base image.
        
        Parameters:
        overlay_pixmap (QPixmap): The overlay image to be added
        """
        # Remove any existing overlay first
        self.remove_overlay()
        
        # Scale the overlay to match the base image size if needed
        if self.base_pixmap and overlay_pixmap.size() != self.base_pixmap.size():
            overlay_pixmap = overlay_pixmap.scaled(
                self.base_pixmap.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        
        # Create a pixmap item for the overlay and add it to the scene
        self.overlay_pixmap_item = self.scene.addPixmap(overlay_pixmap)
        
        # Position the overlay to align with the base image
        if self.pixmap_item:
            self.overlay_pixmap_item.setPos(self.pixmap_item.pos())
        
        # Set the overlay above the base image
        self.overlay_pixmap_item.setZValue(1)  # Base image is typically at Z=0
        
        # Set default overlay opacity (semi-transparent)
        self.overlay_opacity = 128  # 0-255 range, 128 is 50% opacity
        self.overlay_pixmap_item.setOpacity(self.overlay_opacity / 255.0)
        
        # Store a reference to the original overlay pixmap
        self.overlay_original_pixmap = overlay_pixmap
        
        # Update the scene
        self.scene.update()
        
        return True

    def remove_overlay(self):
        """Remove overlay if exists"""
        if self.overlay_pixmap_item:
            self.scene.removeItem(self.overlay_pixmap_item)
            self.overlay_pixmap_item = None
            return True
        return False

    def show_opacity_dialog(self):
        """Show or create the opacity dialog"""
        # Only show if there's an overlay or points
        if not (self.overlay_pixmap_item or self.points):
            return
                
        # Always create a fresh dialog with the current opacity value
        # This ensures the dialog always shows the current value
        current_opacity = self.points_opacity
        
        # Close any existing dialog
        if hasattr(self, "opacity_dialog") and self.opacity_dialog:
            self.opacity_dialog.close()
            
        # Create new dialog with current opacity value
        self.opacity_dialog = OverlayOpacityDialog(self, current_opacity)
        self.opacity_dialog.show()

    def update_overlay_opacity(self, value):
        """Updates the opacity for all points and overlay with consistent rendering for overlapping points"""
        
        self.points_opacity = value  # Store the opacity value
        
        # If there are no points, just update the overlay opacity if it exists
        if not self.points:
            if self.overlay_pixmap_item:
                self.overlay_opacity = value
                self.overlay_pixmap_item.setOpacity(value / 255.0)
            return
        
        # Update the unified point overlay
        self.update_points_overlay()

    def update_points_overlay(self):
        """Creates or updates the unified points overlay using batched rendering with improved synchronization"""
        # Skip if no base pixmap
        if not self.base_pixmap:
            return
        
        # Get the base image dimensions
        width = self.base_pixmap.width()
        height = self.base_pixmap.height()
        
        # Create a transparent pixmap for the points if it doesn't exist already
        if not hasattr(self, 'points_pixmap') or self.points_pixmap is None:
            self.points_pixmap = QPixmap(width, height)
            self.points_pixmap.fill(Qt.GlobalColor.transparent)
            self.last_rendered_points_count = 0
        
        # Handle undo operations - rebuild the pixmap if points were removed
        if hasattr(self, 'last_rendered_points_count') and self.last_rendered_points_count > len(self.points):
            # Reset the pixmap and force full redraw
            self.points_pixmap.fill(Qt.GlobalColor.transparent)
            self.last_rendered_points_count = 0
        
        # Always render all points when last_rendered_points_count is 0
        if self.last_rendered_points_count == 0:
            points_to_render = self.points
        else:
            # Only render the new points that haven't been rendered yet
            points_to_render = self.points[self.last_rendered_points_count:]
        
        # Create a painter even if there are no new points to render
        # This ensures the pixmap is properly updated when undoing to empty state
        painter = QPainter(self.points_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        
        # Store the last used color and brush to avoid unnecessary brush changes
        last_color = None
        
        # Draw only the new points onto the unified pixmap
        for point_item in points_to_render:
            pos = point_item.get_position()
            radius = point_item._fixed_radius  # Use the stored radius
            
            # Get the point's individual color (if points can have different colors)
            if hasattr(point_item, '_color'):
                current_color = point_item._color
            else:
                current_color = self.point_color
                
            # Only change the brush if the color changes
            if current_color != last_color:
                color = QColor(current_color)
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)  # No outline, just filled circles
                last_color = current_color
                
            painter.drawEllipse(pos, radius, radius)
            
            # Ensure point is properly hidden
            point_item.setVisible(False)
    
        painter.end()
        
        # Update our count of rendered points
        self.last_rendered_points_count = len(self.points)
        
        # Create or update the overlay item rather than removing and recreating
        if not hasattr(self, 'points_overlay_item') or self.points_overlay_item is None:
            # Create new overlay item with the unified points
            self.points_overlay_item = self.scene.addPixmap(self.points_pixmap)
            self.points_overlay_item.setZValue(1)  # Above base image, below any other overlays
        else:
            # Update existing overlay with new pixmap
            self.points_overlay_item.setPixmap(self.points_pixmap)
        
        # Apply current opacity
        self.points_overlay_item.setOpacity(self.points_opacity / 255.0)
        
        # Calculate the region that needs updating
        update_rect = QRectF()
        for point in points_to_render:
            pos = point.get_position()
            r = point._fixed_radius
            point_rect = QRectF(pos.x() - r, pos.y() - r, r * 2, r * 2)
            if update_rect.isEmpty():
                update_rect = point_rect
            else:
                update_rect = update_rect.united(point_rect)
        
        # Add a small margin and update only the changed area
        if not update_rect.isEmpty():
            update_rect.adjust(-2, -2, 2, 2)
            self.scene.update(update_rect)