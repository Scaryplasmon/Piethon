from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QSize
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QPainterPath, QTransform
from PySide6.QtWidgets import QWidget, QColorDialog, QScrollArea, QFrame
from PIL import Image
import numpy as np

class DrawingArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas_size = (512, 512)
        self.drawing_layer = QPixmap(*self.canvas_size)
        self.drawing_layer.fill(Qt.black)
        
        # Drawing properties
        self.last_point = None
        self.drawing = False
        self.brush_size = 5
        self.brush_color = QColor(Qt.white)
        self.brush_opacity = 255
        self.brush_hardness = 1.0
        self.eraser_mode = False
        self.drawing_shape = False
        self.temp_layer = None
        
        # Zoom properties
        self.scale = 1.0
        self.min_scale = 0.1
        self.max_scale = 5.0
        
        # Set minimum size to prevent collapse
        self.setMinimumSize(*self.canvas_size)
        
        # Enable mouse tracking for smooth drawing
        self.setMouseTracking(True)
        
    def wheelEvent(self, event):
        # Handle zoom with mouse wheel
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 0.9
            new_scale = self.scale * zoom_factor
            
            # Constrain scale within bounds
            self.scale = max(self.min_scale, min(self.max_scale, new_scale))
            
            # Update widget size
            self.updateGeometry()
            self.update()
            event.accept()
            
    def sizeHint(self):
        # Return scaled size
        return QSize(
            int(self.canvas_size[0] * self.scale),
            int(self.canvas_size[1] * self.scale)
        )
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Apply zoom transform
        painter.scale(self.scale, self.scale)
        
        # Draw the canvas
        painter.drawPixmap(0, 0, self.drawing_layer)
        if self.drawing_shape and self.temp_layer:
            painter.drawPixmap(0, 0, self.temp_layer)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            self.last_point = None

    def mouseMoveEvent(self, event):
        if self.drawing and self.last_point:
            painter = QPainter(self.drawing_layer)
            painter.setRenderHint(QPainter.Antialiasing)
            
            pen = QPen()
            color = QColor(Qt.black if self.eraser_mode else self.brush_color)
            color.setAlpha(self.brush_opacity)
            pen.setColor(color)
            pen.setWidth(self.brush_size)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            
            painter.setPen(pen)
            painter.drawLine(self.last_point / self.scale, event.pos() / self.scale)
            
            self.last_point = event.pos()
            self.update()

    def set_brush_size(self, size):
        self.brush_size = size

    def set_brush_opacity(self, opacity):
        self.brush_opacity = int(opacity * 255)

    def set_brush_hardness(self, hardness):
        self.brush_hardness = hardness

    def toggle_eraser(self):
        self.eraser_mode = not self.eraser_mode

    def toggle_shape_drawing(self):
        self.drawing_shape = not self.drawing_shape

    def pick_color(self):
        color = QColorDialog.getColor(self.brush_color)
        if color.isValid():
            self.brush_color = color

    def clear_canvas(self):
        self.drawing_layer.fill(Qt.black)
        self.update()

    def undo(self):
        # Implementation of undo method
        pass

    def redo(self):
        # Implementation of redo method
        pass

    def get_image(self):
        """Convert current drawing to PIL Image"""
        # Get the QImage from QPixmap
        qimage = self.drawing_layer.toImage()
        
        # Convert to RGB format
        qimage = qimage.convertToFormat(QImage.Format_RGB888)
        
        # Get the image data
        width = qimage.width()
        height = qimage.height()
        
        # Create numpy array directly from the bits
        ptr = qimage.constBits()
        arr = np.frombuffer(ptr, np.uint8).reshape((512, 512, 3))
        
        # Convert to PIL Image
        pil_image = Image.fromarray(arr, 'RGB')
        return pil_image

class DrawingHandler(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create drawing area
        self.drawing_area = DrawingArea()
        
        # Set up scroll area
        self.setWidget(self.drawing_area)
        self.setWidgetResizable(True)
        
        # Add frame/border
        self.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.setLineWidth(2)
        self.setStyleSheet("""
            QScrollArea {
                border: 2px solid #333333;
                background-color: #1a1a1a;
            }
        """)
        
        # Set fixed size for the scroll area
        self.setFixedSize(532, 532)  # 512 + 20 for scrollbars
        
    def get_image(self):
        return self.drawing_area.get_image()

    # Forward methods to drawing area
    def set_brush_size(self, size):
        self.drawing_area.set_brush_size(size)

    def set_brush_opacity(self, opacity):
        self.drawing_area.set_brush_opacity(opacity)

    def set_brush_hardness(self, hardness):
        self.drawing_area.set_brush_hardness(hardness)

    def toggle_eraser(self):
        self.drawing_area.toggle_eraser()

    def toggle_shape_drawing(self):
        self.drawing_area.toggle_shape_drawing()

    def pick_color(self):
        self.drawing_area.pick_color()

    def clear_canvas(self):
        self.drawing_area.clear_canvas()

    def undo(self):
        self.drawing_area.undo()

    def redo(self):
        self.drawing_area.redo()