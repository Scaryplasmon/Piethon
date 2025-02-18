import sys
import os
from pathlib import Path
import json
from PIL import Image, ImageDraw
from PySide6.QtCore import Qt, Signal, Slot, QObject, QSize, QTimer, QEvent
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QIcon, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QScrollArea,
    QGraphicsView, QGraphicsScene, QFrame, QTextEdit, QInputDialog, QColorDialog, QCheckBox
)
import random
import re

class DrawingCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize all state variables first
        self.drawing = False
        self.last_point = None
        self.brush_size = 5
        self.brush_intensity = 1.0
        self.layer_opacity = 0.5
        self.color_picking = False  # Added this initialization
        self.picked_color = None    # Added this initialization
        self.shape_points = []      # Added this initialization
        self.is_drawing_shape = False
        self.eraser_mode = False  # Add eraser state
        
        # Get main window reference
        self.main_window = parent
        
        # Initialize all layers
        self.base_layer = None
        self.drawing_layer = QPixmap(512, 512)
        self.drawing_layer.fill(Qt.transparent)
        self.black_overlay = QPixmap(512, 512)
        self.black_overlay.fill(QColor(0, 0, 0, 50))
        self.temp_layer = QPixmap(512, 512)
        self.temp_layer.fill(Qt.transparent)
        self.black_bg = None
        
        # Initialize undo history
        self.history = []
        self.redo_stack = []  # Add redo stack
        self.max_history = 50
        
        self.setMinimumSize(512, 512)
        
        # Add black background and buttons only for main drawing canvas
        if isinstance(parent, QMainWindow):
            self.black_bg = QPixmap(512, 512)
            self.black_bg.fill(QColor(0, 0, 0))
            
            # Add eraser button with emoji icon
            self.eraser_btn = QPushButton("✏️", self)  # White circle for eraser
            self.eraser_btn.setToolTip("Toggle Eraser Mode (Draw/Erase)")
            self.eraser_btn.setFixedSize(30, 30)
            self.eraser_btn.setCheckable(True)
            self.eraser_btn.clicked.connect(self.toggle_eraser)
            self.eraser_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffb3b3;
                    border: none;
                    border-radius: 15px;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton:checked {
                    background-color: #ff8080;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #ffc6c6;
                }
            """)
            self.eraser_btn.move(10, 10)
            
            # Add color picker button with emoji icon
            self.color_picker_btn = QPushButton("🎯", self)  # Changed to target emoji
            self.color_picker_btn.setToolTip("Pick color and draw shape")
            self.color_picker_btn.setFixedSize(30, 30)
            self.color_picker_btn.clicked.connect(self.start_color_picker)
            self.color_picker_btn.setStyleSheet("""
                QPushButton {
                    background-color: #b3ffb3;
                    border: none;
                    border-radius: 15px;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #c6ffc6;
                }
            """)
            self.color_picker_btn.move(50, 10)

            # ===== New HEX picker button =====
            self.hex_picker_btn = QPushButton("🎨", self)
            self.hex_picker_btn.setToolTip("Pick a color and add its HEX code to text")
            self.hex_picker_btn.setFixedSize(30, 30)
            self.hex_picker_btn.setStyleSheet("""
                QPushButton {
                    background-color: #73eafa;
                    border: none;
                    border-radius: 15px;
                    font-size: 16px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #c6e3ff;
                }
            """)
            self.hex_picker_btn.move(90, 10)
            self.hex_picker_btn.clicked.connect(self.open_hex_color_picker)
            # ===== End of new HEX picker button =====
            
    def set_base_image(self, image_path):
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.base_layer = pixmap.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.update()
            
    def clear_drawing(self):
        """Clear the drawing layer"""
        self.drawing_layer = QPixmap(512, 512)
        self.drawing_layer.fill(Qt.transparent)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw base image first if exists
        if self.base_layer:
            painter.drawPixmap(0, 0, self.base_layer)
        
        # Draw black background with opacity only for drawing canvas
        if self.black_bg:
            painter.setOpacity(self.layer_opacity)
            painter.drawPixmap(0, 0, self.black_bg)
        
        # Draw white lines and shapes on top
        painter.setOpacity(1.0)  # Full opacity for drawing
        painter.drawPixmap(0, 0, self.drawing_layer)
        
        # Draw temporary shape preview
        if self.color_picking and len(self.shape_points) > 0:
            painter.drawPixmap(0, 0, self.temp_layer)
            
    def start_color_picker(self):
        """Start color picker mode"""
        self.color_picking = True
        self.setCursor(Qt.CrossCursor)
        if hasattr(self.main_window, 'status_label'):
            self.main_window.status_label.setText("Click to pick a color")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.color_picking and not self.picked_color:
                # Pick color from base image
                pos = event.position().toPoint()
                if self.base_layer:
                    image = self.base_layer.toImage()
                    self.picked_color = QColor(image.pixel(pos))
                    self.shape_points = []
                    self.is_drawing_shape = True
                    if hasattr(self.main_window, 'status_label'):
                        self.main_window.status_label.setText("Draw shape to fill")
                    self.setCursor(Qt.CrossCursor)  # Cross cursor for drawing shape
            elif self.is_drawing_shape:
                # Start drawing shape
                self.shape_points = [event.position().toPoint()]
                self.last_point = event.position().toPoint()
            else:
                # Normal drawing mode
                self.drawing = True
                self.last_point = event.position().toPoint()
                self.setCursor(Qt.ClosedHandCursor)  # Closed hand cursor for drawing
                self.history.append(QPixmap(self.drawing_layer))
                if len(self.history) > self.max_history:
                    self.history.pop(0)
                    
            # Clear redo stack when new drawing occurs
            if self.drawing or self.is_drawing_shape:
                self.redo_stack.clear()
            
    def mouseMoveEvent(self, event):
        if self.is_drawing_shape and event.buttons() & Qt.LeftButton:
            # Add points while drawing shape
            self.shape_points.append(event.position().toPoint())
            self.update_temp_shape()
        elif self.drawing:
            end_point = event.position().toPoint()
            painter = QPainter(self.drawing_layer)
            painter.setRenderHint(QPainter.Antialiasing)
            
            if self.eraser_mode:
                # Erase by drawing with composition mode clear
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                pen = QPen()
                pen.setWidth(self.brush_size * 2)  # Make eraser slightly bigger
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
            else:
                # Normal drawing mode
                pen = QPen()
                pen.setWidth(self.brush_size)
                pen.setCapStyle(Qt.RoundCap)
                pen.setColor(QColor(255, 255, 255, int(255 * self.brush_intensity)))
                painter.setPen(pen)
            
            painter.drawLine(self.last_point, end_point)
            self.last_point = end_point
            painter.end()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_drawing_shape and len(self.shape_points) > 2:
                # Complete and fill shape
                self.finalize_shape()
                self.is_drawing_shape = False
                self.color_picking = False
                self.picked_color = None
                self.setCursor(Qt.ArrowCursor)
            else:
                self.drawing = False
                self.setCursor(Qt.ArrowCursor)
                
    def update_temp_shape(self):
        """Update temporary shape preview"""
        if len(self.shape_points) < 2:
            return
            
        self.temp_layer.fill(Qt.transparent)
        painter = QPainter(self.temp_layer)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw shape outline
        pen = QPen(Qt.white, 2, Qt.SolidLine)  # Solid white line
        painter.setPen(pen)
        
        # Create path from points
        path = QPainterPath()
        path.moveTo(self.shape_points[0])
        for point in self.shape_points[1:]:
            path.lineTo(point)
            
        painter.drawPath(path)
        painter.end()
        self.update()
        
    def finalize_shape(self):
        """Fill the drawn shape with picked color"""
        if len(self.shape_points) < 3:
            return
            
        # Save current state for undo
        self.history.append(QPixmap(self.drawing_layer))
        
        painter = QPainter(self.drawing_layer)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create path from points
        path = QPainterPath()
        path.moveTo(self.shape_points[0])
        for point in self.shape_points[1:]:
            path.lineTo(point)
        path.closeSubpath()
        
        # Fill with picked color
        fill_color = QColor(self.picked_color)
        fill_color.setAlpha(int(255 * self.brush_intensity))
        painter.fillPath(path, fill_color)
        
        painter.end()
        self.temp_layer.fill(Qt.transparent)
        self.update()
        
    def undo(self):
        """Undo last drawing action"""
        if self.history:
            # Save current state for redo
            self.redo_stack.append(QPixmap(self.drawing_layer))
            # Restore previous state
            self.drawing_layer = self.history.pop()
            self.update()
            
    def redo(self):
        """Redo last undone action"""
        if self.redo_stack:
            # Save current state for undo
            self.history.append(QPixmap(self.drawing_layer))
            # Restore redo state
            self.drawing_layer = self.redo_stack.pop()
            self.update()

    def toggle_eraser(self):
        """Toggle between draw and erase mode"""
        self.eraser_mode = self.eraser_btn.isChecked()
        if self.eraser_mode:
            self.setCursor(Qt.CrossCursor)
            self.eraser_btn.setText("❌")  # Change to X when active
        else:
            self.setCursor(Qt.ArrowCursor)
            self.eraser_btn.setText("✏️")  # Change back to circle when inactive

    def save_drawing(self, output_path):
        """Save drawing with black background"""
        # Create final image with black background
        final_image = QImage(512, 512, QImage.Format_RGB32)
        final_image.fill(QColor(0, 0, 0))  # Fill with solid black
        
        # Draw the drawing layer on top
        painter = QPainter(final_image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self.drawing_layer)
        painter.end()
        
        # Save as RGB image
        final_image.save(output_path, quality=100)

    def get_color_at(self, pos):
        """Get color at position in the base image"""
        if self.base_layer:
            image = self.base_layer.toImage()
            if image.valid(pos.x(), pos.y()):
                return QColor(image.pixel(pos.x(), pos.y()))
        return None

    def open_hex_color_picker(self):
        """
        Open a color dialog and append the selected color's HEX code
        to the text editor (txt viewport) in the main window.
        """
        color = QColorDialog.getColor()
        if color.isValid() and self.main_window is not None and hasattr(self.main_window, 'text_editor'):
            hex_color = color.name().upper()  # Get HEX color code in the format "#RRGGBB"
            # Retrieve existing text from the text editor
            current_text = self.main_window.text_editor.toPlainText()
            # Append the HEX color code (separated by a space)
            hex_color = hex_color.lower()
            new_text = f"{hex_color},{current_text}".strip()
            self.main_window.text_editor.setPlainText(new_text)

class TagButton(QWidget):
    def __init__(self, text, position, parent=None):
        super().__init__(parent)
        self.text = text
        self.position = position
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Generate pastel color for main button
        self.bg_color = self.generate_pastel_color()
        
        # Main tag button with random emoji icon
        tag_icons = ["🏷️", "🔖", "📌", "📍", "🎯", "💡", "🔑", "⭐", "💫", "✨"]
        self.button = QPushButton(f"{random.choice(tag_icons)} {text}")
        self.button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.bg_color.name()};
                color: black;
                border: none;
                border-radius: 10px;
                padding: 5px;
            }}
            QPushButton:hover {{
                background-color: {QColor(self.bg_color).lighter(110).name()};
            }}
        """)
        layout.addWidget(self.button)
        
        # Fixed control buttons with consistent icons
        controls = [
            ('❌', 'Delete tag', '#ffb3b3'),    # Delete tag completely
            ('➖', 'Remove from text', '#b3d9ff'),  # Remove tag from text
            ('➕', 'Add to text', '#b3ffb3')    # Add tag to text
        ]
        
        for symbol, tip, color in controls:
            btn = QPushButton(symbol)
            btn.setFixedSize(20, 20)
            btn.setToolTip(tip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: black;
                    border: none;
                    border-radius: 10px;
                    font-size: 12px;
                    padding: 0px;
                    margin: 0px;
                    qproperty-text: '{symbol}';
                }}
                QPushButton:hover {{
                    background-color: {QColor(color).lighter(110).name()};
                }}
            """)
            layout.addWidget(btn)

    def generate_pastel_color(self):
        """Generate a pastel color"""
        return QColor(
            random.randint(180, 255),
            random.randint(180, 255),
            random.randint(180, 255)
        )

class ColorPaletteWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.colors = []
        
    def set_colors(self, hex_codes):
        self.colors = [QColor(code) for code in hex_codes if QColor(code).isValid()]
        self.update()
        
    def paintEvent(self, event):
        if not self.colors:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate color block width
        width = self.width() / len(self.colors)
        height = self.height()
        
        for i, color in enumerate(self.colors):
            # Draw color block
            painter.fillRect(i * width, 0, width, height, color)
            
            # Draw hex code text
            painter.setPen(self.get_contrast_color(color))
            painter.drawText(
                i * width, 0, width, height,
                Qt.AlignCenter,
                color.name().upper()
            )
            
    def get_contrast_color(self, bg_color):
        # Calculate luminance to determine text color
        luminance = (0.299 * bg_color.red() + 
                    0.587 * bg_color.green() + 
                    0.114 * bg_color.blue()) / 255
        return QColor(Qt.black) if luminance > 0.5 else QColor(Qt.white)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Manager")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #000000;
            }
            QPushButton {
                background-color: #ffb3d9;  /* Pastel pink */
                color: #000000;
                border: none;
                border-radius: 10px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #ffc6e3;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #000000;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 5px;
            }
            QScrollArea {
                background-color: #000000;
                border: none;
            }
        """)
        
        # Initialize state variables first
        self.image_folder = None
        self.txt_folder = None
        self.edges_folder = None
        self.drawing_output_folder = None
        self.current_index = -1
        self.image_files = []
        self.txt_files = []
        self.paired_files = []
        self.tag_buttons = {}
        
        # Add config state
        self.config = {
            'image_folder': None,
            'txt_folder': None,
            'edges_folder': None,
            'drawing_output_folder': None,
            'current_index': -1,
            'tags': []
        }
        
        # Setup UI first
        self.setup_ui()
        
        # Install a global event filter so arrow keys will navigate images
        QApplication.instance().installEventFilter(self)
        # Optionally, force the main window to have focus
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Try to load config only after UI is setup (optional)
        try:
            self.load_config()
        except:
            pass  # Silently fail if no config exists
            
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Define button style first
        button_style = """
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 10px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #666666;
            }
        """
        
        # Toolbar-style button panel with icons
        button_panel = QWidget()
        button_layout = QHBoxLayout(button_panel)
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.setSpacing(5)
        
        # Define buttons with icons and colors
        buttons_config = [
            ("🖼️", "Select Reference Images", "#FFB3B3", self.select_image_folder),
            ("🕸️", "Select Edges", "#B3FFB3", self.select_edges_folder),
            ("📝", "Select Text Folder", "#B3B3FF", self.select_txt_folder),
            ("💾", "Select Drawing Output", "#FFE4B3", self.select_drawing_output),
            ("⚙️", "Save Config", "#E4B3FF", self.save_config),
            ("📂", "Load Config", "#B3FFE4", self.load_config),
            ("⬅️", "Previous", "#FFB3E4", self.prev_pair),
            ("➡️", "Next", "#B3FFE4", self.next_pair)
        ]
        
        for icon, tooltip, color, callback in buttons_config:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setToolTip(tooltip)
            btn.clicked.connect(callback)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: none;
                    border-radius: 20px;
                    padding: 5px;
                    font-size: 18px;
                }}
                QPushButton:hover {{
                    background-color: {QColor(color).lighter(110).name()};
                }}
            """)
            button_layout.addWidget(btn)
            
        # # Add bis filter checkbox to button panel
        # self.bis_checkbox = QCheckBox("Show only _bis pairs")
        # self.bis_checkbox.setStyleSheet("""
        #     QCheckBox {
        #         color: white;
        #         background-color: #2d2d2d;
        #         padding: 5px;
        #         border-radius: 5px;
        #     }
        #     QCheckBox:hover {
        #         background-color: #3d3d3d;
        #     }
        # """)
        # self.bis_checkbox.stateChanged.connect(self.update_pairs)
        # button_layout.addWidget(self.bis_checkbox)
        
        main_layout.addWidget(button_panel)
        
        # Content area with tags
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        
        # Tag section
        tag_section = QWidget()
        tag_layout = QHBoxLayout(tag_section)
        
        # Add tag button
        add_tag_btn = QPushButton("➕ Add Tag")
        add_tag_btn.setStyleSheet("""
            QPushButton {
                background-color: #b3ffb3;  /* Light green */
                color: black;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c6ffc6;
            }
        """)
        add_tag_btn.clicked.connect(self.add_new_tag)
        tag_layout.addWidget(add_tag_btn)
        
        # Scrollable tag area
        tag_scroll = QScrollArea()
        tag_scroll.setWidgetResizable(True)
        tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tag_scroll.setMaximumHeight(50)
        tag_scroll.setStyleSheet("background-color: #000000; border: none;")
        
        tag_container = QWidget()
        self.tag_layout = QHBoxLayout(tag_container)
        self.tag_layout.setSpacing(5)
        tag_scroll.setWidget(tag_container)
        
        tag_layout.addWidget(tag_scroll, stretch=1)
        content_layout.addWidget(tag_section)
        
        # Main content (images and text)
        main_content = QWidget()
        main_content_layout = QHBoxLayout(main_content)
        
        # Edges canvas (without black background) - Now on the left
        self.edges_canvas = DrawingCanvas()  # No parent means no black background
        main_content_layout.addWidget(self.edges_canvas, stretch=2)
        
        # Reference canvas (with black background) - Now in the center
        self.reference_canvas = DrawingCanvas(self)  # This will have the black background
        main_content_layout.addWidget(self.reference_canvas, stretch=2)
        
        # Text editor - Stays on the right
        self.text_editor = QTextEdit()
        self.text_editor.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 5px;
                font-family: Consolas;
                font-size: 12pt;
            }
        """)
        
        # Add color palette below text editor
        self.palette_widget = ColorPaletteWidget()
        text_layout = QVBoxLayout()
        text_layout.addWidget(self.text_editor)
        text_layout.addWidget(self.palette_widget)
        main_content_layout.addLayout(text_layout, stretch=1)
        
        # Connect text editor to palette update
        self.text_editor.textChanged.connect(self.update_color_palette)
        
        content_layout.addWidget(main_content)
        main_layout.addWidget(content_area)
        
        # Control sliders
        slider_panel = QWidget()
        slider_layout = QHBoxLayout(slider_panel)
        
        # Brush size slider
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 50)
        self.brush_size_slider.setValue(5)
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        slider_layout.addWidget(QLabel("Brush Size"))
        slider_layout.addWidget(self.brush_size_slider)
        
        # Brush intensity slider
        self.brush_intensity_slider = QSlider(Qt.Horizontal)
        self.brush_intensity_slider.setRange(0, 100)
        self.brush_intensity_slider.setValue(100)
        self.brush_intensity_slider.valueChanged.connect(self.update_brush_intensity)
        slider_layout.addWidget(QLabel("Brush Intensity"))
        slider_layout.addWidget(self.brush_intensity_slider)
        
        # Layer opacity slider
        self.layer_opacity_slider = QSlider(Qt.Horizontal)
        self.layer_opacity_slider.setRange(0, 100)
        self.layer_opacity_slider.setValue(50)
        self.layer_opacity_slider.valueChanged.connect(self.update_layer_opacity)
        slider_layout.addWidget(QLabel("Layer Opacity"))
        slider_layout.addWidget(self.layer_opacity_slider)

        # Add bis filter checkbox and settings
        bis_container = QWidget()
        bis_layout = QHBoxLayout(bis_container)
        bis_layout.setContentsMargins(0, 0, 0, 0)
        bis_layout.setSpacing(5)

        self.bis_suffix = "_bis"  # Default suffix
        self.bis_checkbox = QCheckBox("🪣")
        self.bis_checkbox.setFixedHeight(40)
        self.bis_checkbox.setToolTip("Filter")
        self.bis_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                background-color: #2d2d2d;
                padding: 5px;
                border-radius: 5px;
            }
            QCheckBox:hover {
                background-color: #3d3d3d;
            }
        """)
        self.bis_checkbox.stateChanged.connect(self.update_pairs)
        
        # Add settings button
        self.bis_settings_btn = QPushButton("🧌")
        self.bis_settings_btn.setFixedSize(40, 40)
        self.bis_settings_btn.setToolTip("Filter Rule")
        self.bis_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-radius: 10px;
            }
        """)
        self.bis_settings_btn.clicked.connect(self.change_bis_suffix)
        
        bis_layout.addWidget(self.bis_checkbox)
        bis_layout.addWidget(self.bis_settings_btn)
        bis_layout.addStretch()
        
        slider_layout.addWidget(bis_container)
        
        # Add delete functionality UI elements
        delete_container = QWidget()
        delete_layout = QHBoxLayout(delete_container)
        delete_layout.setContentsMargins(0, 0, 0, 0)
        delete_layout.setSpacing(5)

        # Delete output folder selection button
        self.delete_output_btn = QPushButton("📁")
        self.delete_output_btn.setToolTip("Select folder for moved/deleted files")
        self.delete_output_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff8080;
                border: none;
                border-radius: 10px;
                padding: 5px 5px;
            }
            QPushButton:hover {
                background-color: #ff9999;
            }
        """)
        self.delete_output_btn.clicked.connect(self.select_delete_output)

        # Delete/Move button
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setToolTip("Move current files to backup folder")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4d4d;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)
        self.delete_btn.clicked.connect(self.move_current_files)
        self.delete_btn.setEnabled(False)  # Disabled until output folder is selected

        delete_layout.addWidget(self.delete_btn)
        delete_layout.addWidget(self.delete_output_btn)
        # delete_layout.addStretch()

        slider_layout.addWidget(delete_container)
        
        main_layout.addWidget(slider_panel)
        
        # Add save button
        save_btn = QPushButton("Save (Ctrl+S)")
        save_btn.setStyleSheet(button_style)
        save_btn.clicked.connect(self.save_all)
        main_layout.addWidget(save_btn)
        
        # Status bar
        self.status_label = QLabel("No files loaded")
        self.statusBar().addWidget(self.status_label)
        
        # Menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        
        # Exit QAction
        exit_action = self.file_menu.addAction("Exit", self.close)
        exit_action.setShortcut("Ctrl+Q")
        
        self.setCentralWidget(central_widget)
        
        # Add delete output folder to instance variables
        self.delete_output_folder = None
        
    @Slot()
    def select_image_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.image_files = [f for f in os.listdir(folder) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if self.image_files:
                self.current_index = 0
                self.update_pairs()  # Added this to refresh pairs
                self.load_current_pair()
                # Update config with new folder
                self.config['image_folder'] = folder
                
    @Slot()
    def select_txt_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Text Folder")
        if folder:
            self.txt_folder = folder
            self.txt_files = [f for f in os.listdir(folder) 
                            if f.lower().endswith('.txt')]
            self.update_pairs()
            # Update config with new folder
            self.config['txt_folder'] = folder

    @Slot()
    def select_edges_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Edges Folder")
        if folder:
            self.edges_folder = folder
            self.load_edges_image()
            # Update config with new folder
            self.config['edges_folder'] = folder

    def update_pairs(self):
        """Match image files with their corresponding text files"""
        if not self.image_folder or not self.txt_folder:
            return
            
        self.paired_files = []
        filtered_image_files = self.image_files

        # Filter images if bis checkbox is checked
        if self.bis_checkbox.isChecked():
            # Get base names of all images that have a bis version
            bis_images = {f for f in self.image_files if f.endswith(f'{self.bis_suffix}.png')}
            original_names = {f.replace(f'{self.bis_suffix}.png', '.png') for f in bis_images}
            # Keep both original images and their bis versions
            filtered_image_files = [f for f in self.image_files 
                                  if f in original_names or f.replace(f'{self.bis_suffix}.png', '.png') in original_names]

        for img_file in filtered_image_files:
            base_name = os.path.splitext(img_file)[0]
            txt_file = base_name + '.txt'
            
            if txt_file in self.txt_files:
                self.paired_files.append((
                    os.path.join(self.image_folder, img_file),
                    os.path.join(self.txt_folder, txt_file)
                ))
        
        if self.paired_files:
            self.current_index = 0
            self.load_current_pair()
            
        self.status_label.setText(f"Found {len(self.paired_files)} matching pairs")

    def load_current_pair(self):
        """Load current image-text pair"""
        if not self.paired_files or self.current_index < 0:
            return
            
        img_path, txt_path = self.paired_files[self.current_index]
        
        # Clear previous drawing
        self.reference_canvas.clear_drawing()
        
        # Load reference image
        self.reference_canvas.set_base_image(img_path)
        
        # Load second image if available
        self.load_edges_image()
        
        # Load text
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                self.text_editor.setPlainText(f.read().strip())
        except Exception as e:
            self.status_label.setText(f"Error loading text: {str(e)}")
            
        self.status_label.setText(
            f"Loaded pair {self.current_index + 1}/{len(self.paired_files)}: {os.path.basename(img_path)}")

    @Slot()
    def prev_pair(self):
        if self.paired_files:
            self.current_index = (self.current_index - 1) % len(self.paired_files)
            self.load_current_pair()

    @Slot()
    def next_pair(self):
        if self.paired_files:
            self.current_index = (self.current_index + 1) % len(self.paired_files)
            self.load_current_pair()

    def add_new_tag(self, tag_text=None, position=None, from_config=False):
        """Add a new tag button"""
        if not from_config:
            tag_text, ok = QInputDialog.getText(self, "New Tag", "Enter tag text:")
            if not ok or not tag_text:
                return
            
            # Remove position selection since tags will always go at the end
            position = "end"  # Default to end always

        # Create tag button
        tag_button = TagButton(tag_text, position)
        self.tag_layout.addWidget(tag_button)
        self.tag_buttons[tag_text] = tag_button
        
        # Connect main button click
        tag_button.button.clicked.connect(lambda: self.add_tag_to_text(tag_text))
        
        # Connect control buttons
        control_buttons = tag_button.findChildren(QPushButton)[1:]  # Skip main button
        
        # Delete button (❌)
        control_buttons[0].clicked.connect(lambda: self.delete_tag(tag_text))
        
        # Remove from text button (➖)
        control_buttons[1].clicked.connect(lambda: self.remove_tag_from_text(tag_text))
        
        # Add to text button (➕)
        control_buttons[2].clicked.connect(lambda: self.add_tag_to_text(tag_text))

    def delete_tag(self, tag_text):
        """Delete tag completely"""
        if tag_text in self.tag_buttons:
            self.tag_buttons[tag_text].deleteLater()
            del self.tag_buttons[tag_text]
            self.remove_tag_from_text(tag_text)

    def add_tag_to_text(self, tag_text):
        """Add tag to text before the closing '>'"""
        current_text = self.text_editor.toPlainText()
        
        # Find the closing '>' of the tags section
        tag_end = current_text.find('>')
        if tag_end == -1:
            # If no tag section exists, create one
            new_text = f"<tags: {tag_text}>"
            if current_text:
                new_text += "\n" + current_text
        else:
            # Insert the new tag before the '>'
            if current_text[tag_end-1] == ' ':
                # If there's already a space before '>', just add the tag
                new_text = current_text[:tag_end-1] + f", {tag_text}" + current_text[tag_end-1:]
            else:
                # Add a space before the tag if needed
                new_text = current_text[:tag_end] + f", {tag_text}" + current_text[tag_end:]
                
        self.text_editor.setPlainText(new_text)

    def remove_tag_from_text(self, tag_text):
        """Remove tag from text while preserving the tag structure"""
        current_text = self.text_editor.toPlainText()
        tag_end = current_text.find('>')
        
        if tag_end == -1:
            return
            
        # Get the tags section
        tags_section = current_text[:tag_end]
        rest_of_text = current_text[tag_end:]
        
        # Remove the tag and clean up extra commas and spaces
        tags_section = tags_section.replace(f", {tag_text}", "")  # Remove with comma before
        tags_section = tags_section.replace(f"{tag_text}, ", "")  # Remove with comma after
        tags_section = tags_section.replace(tag_text, "")         # Remove without comma
        
        # Clean up multiple commas and spaces
        while ",  " in tags_section:
            tags_section = tags_section.replace(",  ", ", ")
        while ",," in tags_section:
            tags_section = tags_section.replace(",,", ",")
        if tags_section.endswith(", "):
            tags_section = tags_section[:-2]
            
        new_text = tags_section + rest_of_text
        self.text_editor.setPlainText(new_text)

    @Slot()
    def update_brush_size(self, value):
        self.reference_canvas.brush_size = value
        self.edges_canvas.brush_size = value

    @Slot()
    def update_brush_intensity(self, value):
        intensity = value / 100.0
        self.reference_canvas.brush_intensity = intensity
        self.edges_canvas.brush_intensity = intensity

    @Slot()
    def update_layer_opacity(self, value):
        opacity = value / 100.0
        self.reference_canvas.layer_opacity = opacity
        self.edges_canvas.layer_opacity = opacity
        self.reference_canvas.update()
        self.edges_canvas.update()

    def eventFilter(self, obj, event):
        """Intercept arrow key events globally for image navigation."""
        if event.type() == QEvent.KeyPress:
            # Check for left/right arrow keys while not editing text.
            if event.key() == Qt.Key_Left and not self.text_editor.hasFocus():
                self.prev_pair()
                return True  # Consume the event
            elif event.key() == Qt.Key_Right and not self.text_editor.hasFocus():
                self.next_pair()
                return True  # Consume the event
        # Otherwise, pass through to the base implementation
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """Handle other keyboard shortcuts."""
        if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            self.save_all()
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            if not self.text_editor.hasFocus():
                self.reference_canvas.undo()
        elif (event.key() == Qt.Key_Z and 
              event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier)):
            if not self.text_editor.hasFocus():
                self.reference_canvas.redo()
        else:
            super().keyPressEvent(event)

    def save_text(self):
        """Save changes to text file"""
        if not self.paired_files or self.current_index < 0:
            return
            
        _, txt_path = self.paired_files[self.current_index]
        text_content = self.text_editor.toPlainText().strip()
        
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            self.status_label.setText(f"Saved changes to {os.path.basename(txt_path)}")
        except Exception as e:
            self.status_label.setText(f"Error saving text: {str(e)}")

    @Slot()
    def select_drawing_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Drawing Output Folder")
        if folder:
            self.drawing_output_folder = folder

    def save_config(self):
        """Save current state to config file"""
        config_path = 'data_manager_config.json'
        self.config.update({
            'image_folder': self.image_folder,
            'txt_folder': self.txt_folder,
            'edges_folder': self.edges_folder,
            'drawing_output_folder': self.drawing_output_folder,
            'current_index': self.current_index,
            'tags': [[btn.text, btn.position] for btn in self.tag_buttons.values()]
        })
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f)
            self.status_label.setText(f"Config saved to {config_path}")
        except Exception as e:
            self.status_label.setText(f"Error saving config: {str(e)}")

    def load_config(self):
        """Load state from config file"""
        config_path = 'data_manager_config.json'
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
                
            # Only restore folders if they exist
            if os.path.exists(self.config.get('image_folder', '')):
                self.image_folder = self.config['image_folder']
            else:
                self.image_folder = None
                
            if os.path.exists(self.config.get('txt_folder', '')):
                self.txt_folder = self.config['txt_folder']
            else:
                self.txt_folder = None
                
            if os.path.exists(self.config.get('edges_folder', '')):
                self.edges_folder = self.config['edges_folder']
            else:
                self.edges_folder = None
                
            # Only restore files and index if we have valid folders
            if self.image_folder and self.txt_folder:
                self.image_files = [f for f in os.listdir(self.image_folder) 
                                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                self.txt_files = [f for f in os.listdir(self.txt_folder) 
                                if f.lower().endswith('.txt')]
                self.update_pairs()
                if self.paired_files:  # Only set index if we have pairs
                    self.current_index = min(self.config.get('current_index', 0), 
                                          len(self.paired_files) - 1)
                    self.load_current_pair()
            
            # Restore tags
            for tag_text, position in self.config.get('tags', []):
                self.add_new_tag(tag_text, position, from_config=True)
                
            self.status_label.setText("Config loaded successfully")
        except FileNotFoundError:
            self.status_label.setText("No config file found")
        except Exception as e:
            self.status_label.setText(f"Error loading config: {str(e)}")

    def load_edges_image(self):  # renamed from load_second_image
        """Load corresponding image from edges folder"""
        if not self.edges_folder or not self.paired_files or self.current_index < 0:
            return
            
        base_name = os.path.basename(self.paired_files[self.current_index][0])
        edges_image_path = os.path.join(self.edges_folder, base_name)
        
        if os.path.exists(edges_image_path):
            self.edges_canvas.set_base_image(edges_image_path)
        else:
            self.status_label.setText(f"Warning: No matching edge image found: {base_name}")
            
    def save_drawing(self, output_path):
        """Save drawing with black background"""
        # Create final image with black background
        final_image = QImage(512, 512, QImage.Format_RGB32)
        final_image.fill(QColor(0, 0, 0))  # Fill with solid black
        
        # Draw the drawing layer on top
        painter = QPainter(final_image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self.drawing_layer)
        painter.end()
        
        # Save as RGB image
        final_image.save(output_path, quality=100)

    def save_all(self):
        """Save both drawing and text files"""
        if not self.paired_files or self.current_index < 0:
            return
            
        # Save text
        _, txt_path = self.paired_files[self.current_index]
        text_content = self.text_editor.toPlainText().strip()
        
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
                
            # Save drawing if output folder is set
            if self.drawing_output_folder:
                base_name = os.path.basename(self.paired_files[self.current_index][0])
                output_path = os.path.join(self.drawing_output_folder, base_name)
                self.reference_canvas.save_drawing(output_path)
                
            # Show save confirmation
            self.show_save_confirmation(txt_path, output_path if self.drawing_output_folder else None)
            
        except Exception as e:
            self.status_label.setText(f"Error saving files: {str(e)}")

    def show_save_confirmation(self, txt_path, img_path=None):
        """Show save confirmation in bottom corner"""
        msg = f"Saved text to: {os.path.basename(txt_path)}"
        if img_path:
            msg += f"\nSaved drawing to: {os.path.basename(img_path)}"
            
        self.status_label.setText(msg)
        # Auto-clear after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

    def update_color_palette(self):
        """Parse hex codes from text and update palette"""
        # Find all hex codes in text (both #RRGGBB and #RGB formats)
        text = self.text_editor.toPlainText()
        hex_pattern = r'#(?:[0-9a-fA-F]{3}){1,2}\b'
        hex_codes = re.findall(hex_pattern, text)
        
        # Convert 3-digit hex to 6-digit format
        processed_codes = []
        for code in hex_codes:
            if len(code) == 4:  # #RGB format
                r, g, b = code[1], code[2], code[3]
                code = f"#{r}{r}{g}{g}{b}{b}"
            processed_codes.append(code)
            
        # Update palette widget
        self.palette_widget.set_colors(processed_codes)

    def change_bis_suffix(self):
        """Open dialog to change the bis suffix"""
        new_suffix, ok = QInputDialog.getText(
            self,
            "Change Suffix",
            "Enter new suffix for duplicates:",
            text=self.bis_suffix
        )
        if ok and new_suffix:
            self.bis_suffix = new_suffix
            self.update_pairs()

    def select_delete_output(self):
        """Select output folder for moved/deleted files"""
        folder = QFileDialog.getExistingDirectory(self, "Select Delete Output Folder")
        if folder:
            self.delete_output_folder = folder
            # Create subfolders if they don't exist
            self.create_delete_subfolders()
            self.delete_btn.setEnabled(True)
            self.status_label.setText(f"Delete output folder set to: {folder}")

    def create_delete_subfolders(self):
        """Create subfolders for different file types"""
        if not self.delete_output_folder:
            return

        self.deleted_refs_folder = os.path.join(self.delete_output_folder, "reference_images")
        self.deleted_edges_folder = os.path.join(self.delete_output_folder, "edge_images")
        self.deleted_txt_folder = os.path.join(self.delete_output_folder, "text_files")

        # Create all subfolders
        for folder in [self.deleted_refs_folder, self.deleted_edges_folder, self.deleted_txt_folder]:
            os.makedirs(folder, exist_ok=True)

    def move_current_files(self):
        """Move current files to delete output folder"""
        if not self.delete_output_folder or not self.paired_files or self.current_index < 0:
            return

        try:
            # Get current file paths
            img_path, txt_path = self.paired_files[self.current_index]
            base_name = os.path.basename(img_path)
            txt_name = os.path.basename(txt_path)
            edge_path = os.path.join(self.edges_folder, base_name) if self.edges_folder else None

            # Prepare destination paths
            ref_dest = os.path.join(self.deleted_refs_folder, base_name)
            txt_dest = os.path.join(self.deleted_txt_folder, txt_name)
            edge_dest = os.path.join(self.deleted_edges_folder, base_name) if edge_path else None

            # Move files with safety checks
            moved_files = []
            try:
                # Move reference image
                os.rename(img_path, ref_dest)
                moved_files.append(("reference", img_path, ref_dest))

                # Move text file
                os.rename(txt_path, txt_dest)
                moved_files.append(("text", txt_path, txt_dest))

                # Move edge image if it exists
                if edge_path and os.path.exists(edge_path):
                    os.rename(edge_path, edge_dest)
                    moved_files.append(("edge", edge_path, edge_dest))

                # Verify all moves were successful
                all_moves_verified = all(
                    os.path.exists(dest) and not os.path.exists(src) 
                    for _, src, dest in moved_files
                )

                if all_moves_verified:
                    # Remove current pair from list and update display
                    self.paired_files.pop(self.current_index)
                    if self.paired_files:
                        self.current_index = min(self.current_index, len(self.paired_files) - 1)
                        self.load_current_pair()
                    else:
                        self.current_index = -1
                        self.reference_canvas.clear_drawing()
                        self.edges_canvas.clear_drawing()
                        self.text_editor.clear()

                    self.status_label.setText(f"Successfully moved files to {self.delete_output_folder}")
                else:
                    raise Exception("Move verification failed")

            except Exception as e:
                # If any operation fails, try to restore moved files
                for file_type, src, dest in moved_files:
                    try:
                        if os.path.exists(dest):
                            os.rename(dest, src)
                    except Exception as restore_error:
                        self.status_label.setText(
                            f"Error restoring {file_type} file: {str(restore_error)}"
                        )
                raise Exception(f"Move operation failed: {str(e)}")

        except Exception as e:
            self.status_label.setText(f"Error moving files: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())