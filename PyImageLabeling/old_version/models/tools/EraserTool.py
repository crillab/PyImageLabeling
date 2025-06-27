from PyQt6.QtCore import QRectF, QPointF, QTimer, Qt
from PyQt6.QtGui import QPainter

class EraserTool:
    def erase_point(self, scene_pos):
        """
        Highly optimized erase function that minimizes redraws for improved performance
        with enhanced smoothness.
        """
        # Check if there are any points to erase or if we're in absolute erase mode
        if not self.points and not (self.absolute_erase_mode and self.overlay_pixmap_item):
            return
        
        # Calculate the eraser's squared radius (faster comparison)
        eraser_size_squared = self.eraser_size ** 2
        
        # Track if we've made changes that require updates
        needs_update = False
        
        # OPTIMIZATION: Batch erase operations without updating the display for each point
        # Store the current eraser position for batch processing
        if not hasattr(self, 'erase_positions'):
            self.erase_positions = []
        
        # Add this position to the batch
        self.erase_positions.append(scene_pos)
        
        # Create the current eraser rectangle for update tracking
        eraser_rect = QRectF(
            scene_pos.x() - self.eraser_size, 
            scene_pos.y() - self.eraser_size,
            self.eraser_size * 2, 
            self.eraser_size * 2
        )
        
        # Initialize or update the cumulative erase area
        if not hasattr(self, 'current_erase_update_rect') or self.current_erase_update_rect is None:
            self.current_erase_update_rect = QRectF(eraser_rect)
        else:
            self.current_erase_update_rect = self.current_erase_update_rect.united(eraser_rect)
        
        # Handle absolute erase mode immediately for better visual feedback
        if self.absolute_erase_mode and self.overlay_pixmap_item:
            overlay_pixmap = self.overlay_pixmap_item.pixmap()
            painter = QPainter(overlay_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.GlobalColor.black)
            
            # Draw with softer edges for smoother erasing
            painter.drawEllipse(scene_pos, self.eraser_size, self.eraser_size)
            painter.end()
            
            self.overlay_pixmap_item.setPixmap(overlay_pixmap)
            self.scene.update(eraser_rect)
        
        # Process points immediately for normal mode as well
        if not self.absolute_erase_mode:
            if self.overlay_pixmap_item is not None:
                overlay_pixmap = self.overlay_pixmap_item.pixmap()
                painter = QPainter(overlay_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(Qt.GlobalColor.black)
                
                # Draw with softer edges for smoother erasing
                painter.drawEllipse(scene_pos, self.eraser_size, self.eraser_size)
                painter.end()
                
                self.overlay_pixmap_item.setPixmap(overlay_pixmap)
                self.scene.update(eraser_rect)
        
        # IMPROVEMENT: Process points in smaller batches for more responsive updates
        # Only process points when we have enough positions or timer triggers
        batch_size = 3  # Reduced from 5 for more frequent updates
        if len(self.erase_positions) < batch_size:
            # Start the erase timer if it's not active
            if not self.erase_timer.isActive():
                self.erase_timer.start(50)  # Reduced timer for smoother updates
                
            # Provide immediate visual feedback by updating the area
            self.scene.update(eraser_rect)
            return  # Skip point processing until we have a batch
        
        # IMPROVEMENT: Use interpolation for smoother erasing between points
        interpolated_positions = []
        if len(self.erase_positions) >= 2:
            for i in range(len(self.erase_positions) - 1):
                start_pos = self.erase_positions[i]
                end_pos = self.erase_positions[i + 1]
                
                # Calculate distance between points
                dx = end_pos.x() - start_pos.x()
                dy = end_pos.y() - start_pos.y()
                distance = (dx**2 + dy**2)**0.5
                
                # Only interpolate if points are far enough apart
                if distance > self.eraser_size / 2:
                    # Number of interpolation steps based on distance
                    steps = max(2, min(10, int(distance / (self.eraser_size / 3))))
                    
                    for step in range(1, steps):
                        t = step / steps
                        interp_x = start_pos.x() + dx * t
                        interp_y = start_pos.y() + dy * t
                        interpolated_positions.append(QPointF(interp_x, interp_y))
        
        # Combine original and interpolated positions
        positions_to_check = self.erase_positions.copy() + interpolated_positions
        
        # Create a single large update rect covering all erase positions
        full_update_rect = None
        for pos in positions_to_check:
            current_rect = QRectF(
                pos.x() - self.eraser_size, 
                pos.y() - self.eraser_size,
                self.eraser_size * 2, 
                self.eraser_size * 2
            )
            
            if full_update_rect is None:
                full_update_rect = QRectF(current_rect)
            else:
                full_update_rect = full_update_rect.united(current_rect)
        
        # Reset the batch
        self.erase_positions = []
        
        # Process the accumulated erase positions
        all_erased_points = []
        
        # OPTIMIZATION: Create a fast lookup for points to be removed
        points_to_remove = set()
        
        # OPTIMIZATION: Use spatial partitioning approach for large point sets
        if len(self.points) > 1000:
            # Only check points that could be within the eraser area
            for index, point_item in enumerate(self.points):
                try:
                    # Get point position using the most likely method
                    if hasattr(point_item, 'get_position'):
                        point_center = point_item.get_position()
                    elif hasattr(point_item, '_pos'):
                        point_center = point_item._pos
                    elif hasattr(point_item, 'x') and hasattr(point_item, 'y'):
                        point_center = QPointF(point_item.x(), point_item.y())
                    elif hasattr(point_item, 'scenePos'):
                        point_center = point_item.scenePos()
                    else:
                        continue
                    
                    # Quick bounding box test first (much faster than distance calculation)
                    if (point_center.x() >= full_update_rect.left() and 
                        point_center.x() <= full_update_rect.right() and
                        point_center.y() >= full_update_rect.top() and
                        point_center.y() <= full_update_rect.bottom()):
                        
                        # Now check actual distance to any erase position
                        for pos in positions_to_check:
                            distance_squared = (point_center.x() - pos.x())**2 + (point_center.y() - pos.y())**2
                            if distance_squared <= eraser_size_squared:
                                points_to_remove.add(index)
                                all_erased_points.append(point_item)
                                break
                except Exception:
                    pass
        else:
            # For smaller point sets, just check each point against all positions
            for index, point_item in enumerate(self.points):
                try:
                    if hasattr(point_item, 'get_position'):
                        point_center = point_item.get_position()
                    elif hasattr(point_item, '_pos'):
                        point_center = point_item._pos
                    elif hasattr(point_item, 'x') and hasattr(point_item, 'y'):
                        point_center = QPointF(point_item.x(), point_item.y())
                    elif hasattr(point_item, 'scenePos'):
                        point_center = point_item.scenePos()
                    else:
                        continue
                    
                    # Check against all erase positions
                    for pos in positions_to_check:
                        distance_squared = (point_center.x() - pos.x())**2 + (point_center.y() - pos.y())**2
                        if distance_squared <= eraser_size_squared:
                            points_to_remove.add(index)
                            all_erased_points.append(point_item)
                            break
                except Exception:
                    pass
        
        # OPTIMIZATION: Remove points in reverse order to avoid index shifting
        if points_to_remove:
            # Sort indices in descending order
            indices_list = sorted(points_to_remove, reverse=True)
            
            # Remove points from the scene
            for point_item in all_erased_points:
                try:
                    self.scene.removeItem(point_item)
                except Exception:
                    pass
            
            # Remove from the points list (in reverse order)
            for index in indices_list:
                if 0 <= index < len(self.points):
                    del self.points[index]
            
            # Store erased points for undo functionality
            if all_erased_points:
                self.erased_points_history.append(all_erased_points)
                self.current_stroke.extend([('erase', point) for point in all_erased_points])
                needs_update = True
        
        # OPTIMIZATION: Force a full redraw of the points overlay after batch erasing
        # This is more efficient than incremental updates for large erasing operations
        if needs_update:
            # Signal that we need a complete redraw
            if hasattr(self, 'last_rendered_points_count'):
                self.last_rendered_points_count = 0
                
            # Set the current update rect to the full area affected
            if full_update_rect is not None:
                self.current_erase_update_rect = full_update_rect
            
            # Flag that we need to update the points overlay
            self.points_overlay_needs_update = True
            
            # IMPROVEMENT: Progressive rendering for smoother updates
            # Set up timer for delayed overlay update with progressive timing
            if not hasattr(self, 'batch_update_timer'):
                self.batch_update_timer = QTimer()
                self.batch_update_timer.timeout.connect(self.process_erase_batch_update)
                self.batch_update_timer.setSingleShot(True)
            
            # Immediate visual feedback with a shorter delay for better responsiveness
            if full_update_rect is not None:
                self.scene.update(full_update_rect)
            
            # IMPROVEMENT: Adjust delay based on the number of points for smoother experience
            point_count = len(self.points)
            if point_count > 20000:
                delay = 16  
            elif point_count > 10000:
                delay = 10  
            elif point_count > 5000:
                delay = 8 
            else:
                delay = 4  
            
            # Reset the timer for batched updates
            self.batch_update_timer.start(delay)
        
        self.scene.update()

    def process_erase_batch_update(self):
        """Process batched updates from erasing operations"""
        # Update the scene for the entire affected area if needed
        if hasattr(self, 'current_erase_update_rect') and self.current_erase_update_rect is not None:
            # Add a small margin
            update_rect = QRectF(self.current_erase_update_rect)
            update_rect.adjust(-2, -2, 2, 2)
            self.scene.update(update_rect)
            self.current_erase_update_rect = None
        
        # Check if we need to update the points overlay
        if hasattr(self, 'points_overlay_needs_update') and self.points_overlay_needs_update:
            # Reset the points pixmap to force a full redraw
            if hasattr(self, 'points_pixmap'):
                self.points_pixmap = None
            if hasattr(self, 'last_rendered_points_count'):
                self.last_rendered_points_count = 0
            self.update_points_overlay()
            self.points_overlay_needs_update = False
            
    def end_erase_operation(self):
        self.process_erase_batch_update()

    def toggle_erase_mode(self, enabled):
        self.erase_mode = enabled
        if enabled:
            self.paint_mode = False
            self.magic_pen_mode = False
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(self.DragMode.NoDrag)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(self.DragMode.ScrollHandDrag)