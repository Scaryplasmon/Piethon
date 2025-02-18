import sys
import os
from pathlib import Path
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QScrollArea
)
import cv2
import numpy as np
import random

class ImageProcessor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cute Image Processor 🎨")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #000000;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QScrollArea {
                background-color: #000000;
                border: none;
            }
        """)

        # Initialize state variables
        self.image_folder = None
        self.current_index = -1
        self.image_files = []
        self.original_image = None
        self.processed_image = None
        self.history = []
        self.redo_stack = []
        self.max_history = 50
        self.slider_position = 0.5  # Add this for the comparison slider position
        self.comparison_active = False  # Track if we're dragging the comparison slider

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Button panel with cute icons
        button_panel = QWidget()
        button_layout = QHBoxLayout(button_panel)
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.setSpacing(5)

        # Define buttons with icons and pastel colors
        buttons_config = [
            ("📁", "Open Folder", "#FFB3B3", self.select_folder),
            ("⬅️", "Previous Image", "#B3FFB3", self.prev_image),
            ("➡️", "Next Image", "#B3B3FF", self.next_image),
            ("💾", "Save Image (Ctrl+S)", "#FFE4B3", self.save_image),
            ("↩️", "Undo (Ctrl+Z)", "#E4B3FF", self.undo),
            ("↪️", "Redo (Ctrl+Shift+Z)", "#B3FFE4", self.redo)
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

        main_layout.addWidget(button_panel)

        # Image display and controls container
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)

        # Create a custom widget for the image viewport with comparison slider
        self.viewport_container = QWidget()
        viewport_layout = QVBoxLayout(self.viewport_container)
        viewport_layout.setContentsMargins(0, 0, 0, 0)

        # Image label now in a container for comparison handling
        self.image_label = QLabel()
        self.image_label.setMinimumSize(512, 512)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.mousePressEvent = self.start_comparison
        self.image_label.mouseMoveEvent = self.update_comparison
        self.image_label.mouseReleaseEvent = self.end_comparison
        viewport_layout.addWidget(self.image_label)

        content_layout.addWidget(self.viewport_container, stretch=2)

        # Sliders panel
        sliders_widget = QWidget()
        sliders_layout = QVBoxLayout(sliders_widget)
        sliders_layout.setSpacing(5)

        # Add reset all button at the top of sliders
        reset_all_btn = QPushButton("🔄 Reset All")
        reset_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFB3B3;
                border: none;
                border-radius: 10px;
                padding: 5px;
                color: black;
            }
            QPushButton:hover {
                background-color: #FFC6C6;
            }
        """)
        reset_all_btn.clicked.connect(self.reset_all_sliders)
        sliders_layout.addWidget(reset_all_btn)

        # Define sliders with cute icons and pastel colors
        self.sliders = {}
        sliders_config = [
            ("🌈", "Hue", (-360, 360), "#FFB3B3"),  # Updated Hue range
            ("⚡", "Contrast", (-100, 100), "#B3FFB3"),
            ("❤️", "Red", (-100, 100), "#FFB3B3"),
            ("💙", "Blue", (-100, 100), "#B3B3FF"),
            ("💚", "Green", (-100, 100), "#B3FFB3"),
            ("✨", "Gamma", (1, 500), "#FFE4B3"),
            ("🎨", "Saturation", (-100, 100), "#E4B3FF"),
            ("📊", "Posterize", (2, 16), "#B3FFE4"),
            ("🌟", "Brightness", (-100, 100), "#FFD700"),
            ("🎭", "Vibrance", (-100, 100), "#FF69B4"),
            ("🌓", "Shadows", (-100, 100), "#4B0082"),
            ("🌞", "Highlights", (-100, 100), "#FFA500")
        ]

        for icon, name, (min_val, max_val), color in sliders_config:
            slider_container = QWidget()
            slider_layout = QHBoxLayout(slider_container)
            slider_layout.setContentsMargins(5, 0, 5, 0)
            slider_layout.setSpacing(5)
            
            # Create fixed-width label container
            label = QLabel(f"{icon} {name}")
            label.setStyleSheet("color: white;")
            label.setFixedWidth(100)  # Fixed width for labels
            
            # Create slider first
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            default_value = 0 if name != "Gamma" and name != "Posterize" else (100 if name == "Gamma" else 16)
            slider.setValue(default_value)
            slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    background: #333333;
                    height: 8px;
                    border-radius: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: {color};
                    width: 18px;
                    margin: -5px 0;
                    border-radius: 9px;
                }}
            """)
            slider.valueChanged.connect(self.process_image)
            
            # Now create decrease button
            dec_btn = QPushButton("◀")
            dec_btn.setFixedSize(24, 24)  # Make buttons square
            dec_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: none;
                    border-radius: 12px;
                    font-size: 12px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {QColor(color).lighter(110).name()};
                }}
            """)
            dec_btn.clicked.connect(lambda checked, s=slider: s.setValue(s.value() - 1))
            
            # Create increase button
            inc_btn = QPushButton("▶")
            inc_btn.setFixedSize(24, 24)  # Make buttons square
            inc_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: none;
                    border-radius: 12px;
                    font-size: 12px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {QColor(color).lighter(110).name()};
                }}
            """)
            inc_btn.clicked.connect(lambda checked, s=slider: s.setValue(s.value() + 1))
            
            # Create fixed-width value label
            value_label = QLabel(str(default_value))
            value_label.setStyleSheet("color: white;")
            value_label.setFixedWidth(40)  # Fixed width for value labels
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            slider.valueChanged.connect(lambda v, l=value_label: l.setText(str(v)))
            
            # Add reset button
            reset_btn = QPushButton("↺")
            reset_btn.setFixedSize(24, 24)  # Make buttons square
            reset_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: none;
                    border-radius: 12px;
                    font-size: 14px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {QColor(color).lighter(110).name()};
                }}
            """)
            reset_btn.clicked.connect(lambda checked, s=slider, v=default_value: s.setValue(v))
            
            # Add all widgets to layout with proper alignment
            slider_layout.addWidget(label)
            slider_layout.addWidget(dec_btn)
            slider_layout.addWidget(slider, 1)  # Give slider stretch factor of 1
            slider_layout.addWidget(inc_btn)
            slider_layout.addWidget(value_label)
            slider_layout.addWidget(reset_btn)
            
            sliders_layout.addWidget(slider_container)
            self.sliders[name] = slider

        # Make sliders area scrollable
        scroll = QScrollArea()
        scroll.setWidget(sliders_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background-color: #000000; border: none;")
        content_layout.addWidget(scroll)

        main_layout.addWidget(content_area)

        # Status bar
        self.status_label = QLabel("No image loaded")
        self.statusBar().addWidget(self.status_label)
        self.statusBar().setStyleSheet("color: white;")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder:
            self.image_folder = folder
            self.image_files = [f for f in os.listdir(folder) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if self.image_files:
                self.current_index = 0
                self.load_current_image()

    def load_current_image(self):
        if not self.image_files or self.current_index < 0:
            return

        image_path = os.path.join(self.image_folder, self.image_files[self.current_index])
        self.original_image = cv2.imread(image_path)
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.process_image()
        self.status_label.setText(f"Loaded: {self.image_files[self.current_index]}")

    def process_image(self):
        if self.original_image is None:
            return

        # Save state for undo
        if len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append(self.processed_image.copy() if self.processed_image is not None 
                          else self.original_image.copy())
        self.redo_stack.clear()

        # Process image with current slider values
        img = self.original_image.copy()
        img = img.astype(np.float32) / 255.0

        # Apply adjustments
        # Hue
        if self.sliders["Hue"].value() != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            hsv[:,:,0] = (hsv[:,:,0] + self.sliders["Hue"].value()) % 360
            img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # Contrast
        if self.sliders["Contrast"].value() != 0:
            factor = (259 * (self.sliders["Contrast"].value() + 255)) / (255 * (259 - self.sliders["Contrast"].value()))
            img = np.clip(factor * (img - 0.5) + 0.5, 0, 1)

        # RGB adjustments
        img[:,:,0] = np.clip(img[:,:,0] * (1 + self.sliders["Red"].value()/100), 0, 1)
        img[:,:,1] = np.clip(img[:,:,1] * (1 + self.sliders["Green"].value()/100), 0, 1)
        img[:,:,2] = np.clip(img[:,:,2] * (1 + self.sliders["Blue"].value()/100), 0, 1)

        # Gamma
        gamma = self.sliders["Gamma"].value() / 100
        img = np.power(img, gamma)

        # Saturation
        if self.sliders["Saturation"].value() != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            hsv[:,:,1] = np.clip(hsv[:,:,1] * (1 + self.sliders["Saturation"].value()/100), 0, 1)
            img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # Vibrance (selective saturation based on saturation levels)
        if self.sliders["Vibrance"].value() != 0:
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
            # Apply stronger saturation to less saturated pixels
            saturation_mask = 1.0 - hsv[:,:,1]
            adjustment = (self.sliders["Vibrance"].value() / 100.0) * saturation_mask
            hsv[:,:,1] = np.clip(hsv[:,:,1] * (1 + adjustment), 0, 1)
            img = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        # Shadows (adjust darker areas)
        if self.sliders["Shadows"].value() != 0:
            luminance = np.mean(img, axis=2)
            shadow_mask = 1.0 - luminance
            adjustment = (self.sliders["Shadows"].value() / 100.0) * shadow_mask[:,:,np.newaxis]
            img = np.clip(img * (1 + adjustment), 0, 1)

        # Highlights (adjust brighter areas)
        if self.sliders["Highlights"].value() != 0:
            luminance = np.mean(img, axis=2)
            highlight_mask = luminance
            adjustment = (self.sliders["Highlights"].value() / 100.0) * highlight_mask[:,:,np.newaxis]
            img = np.clip(img * (1 + adjustment), 0, 1)

        # Posterize
        if self.sliders["Posterize"].value() != 16:
            levels = self.sliders["Posterize"].value()
            img = np.clip(np.floor(img * levels) / (levels - 1), 0, 1)

        # Brightness
        if self.sliders["Brightness"].value() != 0:
            img = np.clip(img + self.sliders["Brightness"].value()/100, 0, 1)

        # Convert back to uint8
        self.processed_image = (img * 255).astype(np.uint8)

        # Update display with comparison view
        self.update_display()

    def save_image(self):
        if self.processed_image is None or not self.image_files:
            return

        current_file = self.image_files[self.current_index]
        base_name, ext = os.path.splitext(current_file)
        output_path = os.path.join(self.image_folder, f"{base_name}_bis{ext}")
        
        # Convert back to BGR for saving
        save_image = cv2.cvtColor(self.processed_image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, save_image)
        self.status_label.setText(f"Saved: {os.path.basename(output_path)}")

    def undo(self):
        if self.history:
            self.redo_stack.append(self.processed_image.copy())
            self.processed_image = self.history.pop()
            self.update_display()

    def redo(self):
        if self.redo_stack:
            self.history.append(self.processed_image.copy())
            self.processed_image = self.redo_stack.pop()
            self.update_display()

    def update_display(self):
        if self.processed_image is None or self.original_image is None:
            return
            
        # Create the comparison view
        height, width = self.processed_image.shape[:2]
        bytes_per_line = 3 * width
        
        # Create a combined image for comparison
        combined = self.processed_image.copy()
        split_x = int(width * self.slider_position)
        combined[:, :split_x] = self.original_image[:, :split_x]
        
        # Draw the comparison handle
        handle_width = 4
        handle_color = (255, 255, 255)  # White color for the handle
        combined[:, split_x-handle_width:split_x+handle_width] = handle_color
        
        # Add arrow indicators
        arrow_height = 20
        arrow_width = 10
        arrow_y = height // 2
        
        # Draw left arrow
        cv2.arrowedLine(combined, 
                       (split_x - 20, arrow_y),
                       (split_x - 10, arrow_y),
                       handle_color, 2, tipLength=0.5)
        
        # Draw right arrow
        cv2.arrowedLine(combined,
                       (split_x + 20, arrow_y),
                       (split_x + 10, arrow_y),
                       handle_color, 2, tipLength=0.5)
        
        # Convert to QImage and display
        q_img = QImage(combined.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def start_comparison(self, event):
        """Start the comparison slider drag"""
        self.comparison_active = True
        self.update_slider_position(event)

    def update_comparison(self, event):
        """Update the comparison slider position during drag"""
        if self.comparison_active:
            self.update_slider_position(event)

    def end_comparison(self, event):
        """End the comparison slider drag"""
        self.comparison_active = False

    def update_slider_position(self, event):
        """Update the slider position based on mouse position"""
        if self.image_label.pixmap():
            # Get the image display rect
            rect = self.image_label.pixmap().rect()
            mapped_rect = self.image_label.rect()
            
            # Calculate the relative position
            pos = event.position()
            x = pos.x() - mapped_rect.x()
            width = mapped_rect.width()
            
            # Update slider position (constrained between 0 and 1)
            self.slider_position = max(0, min(1, x / width))
            self.update_display()

    def prev_image(self):
        if self.image_files:
            self.current_index = (self.current_index - 1) % len(self.image_files)
            self.load_current_image()

    def next_image(self):
        if self.image_files:
            self.current_index = (self.current_index + 1) % len(self.image_files)
            self.load_current_image()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            self.save_image()
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            if event.modifiers() & Qt.ShiftModifier:
                self.redo()
            else:
                self.undo()
        else:
            super().keyPressEvent(event)

    def reset_all_sliders(self):
        """Reset all sliders to their default values"""
        for name, slider in self.sliders.items():
            default_value = 0 if name != "Gamma" and name != "Posterize" else (100 if name == "Gamma" else 16)
            slider.setValue(default_value)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageProcessor()
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())