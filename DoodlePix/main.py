import sys
from pathlib import Path
from types import SimpleNamespace
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QIcon, QShortcut, QKeySequence, QPainter, QPen, QPixmap, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QTextEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QMessageBox, QDialog, QComboBox,
    QProgressBar
)
import numpy as np

from draw import DrawingHandler
from inference import InferenceHandler

class BrushSettingsDialog(QDialog):
    def __init__(self, drawing_handler, parent=None):
        super().__init__(parent)
        self.drawing_handler = drawing_handler
        self.setWindowTitle("Brush Settings")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Brush size
        size_layout = QHBoxLayout()
        size_label = QLabel("Size:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 100)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(self.drawing_handler.brush_size)
        
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_spin)
        layout.addLayout(size_layout)
        
        # Connect both controls
        self.size_slider.valueChanged.connect(self.size_spin.setValue)
        self.size_spin.valueChanged.connect(self.size_slider.setValue)
        self.size_slider.valueChanged.connect(self.drawing_handler.set_brush_size)
        
        # Brush opacity
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Opacity:")
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0, 1)
        self.opacity_spin.setSingleStep(0.1)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.drawing_handler.brush_opacity * 100))
        
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_spin)
        layout.addLayout(opacity_layout)
        
        # Connect opacity controls
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_spin.setValue(v / 100)
        )
        self.opacity_spin.valueChanged.connect(
            lambda v: self.opacity_slider.setValue(int(v * 100))
        )
        self.opacity_slider.valueChanged.connect(
            lambda v: self.drawing_handler.set_brush_opacity(v / 100)
        )

class DoodlePixUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DoodlePix")
        self.setStyleSheet("background-color: black; color: white;")
        
        # Initialize handlers
        self.drawing_handler = DrawingHandler()
        self.inference_handler = InferenceHandler()
        
        # Initialize image history
        self.generated_images = []
        self.current_image_index = -1
        
        # Initialize status and progress BEFORE setup_ui
        self.status_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        
        # Setup UI and shortcuts
        self.setup_ui()
        self.setup_shortcuts()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)  # Add spacing between panels
        
        # Left panel - Drawing tools
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        left_layout.setSpacing(10)  # Add spacing between tools and canvas
        
        # Tools column
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setSpacing(5)  # Add spacing between tools
        tools_layout.setContentsMargins(5, 5, 5, 5)
        tools_widget.setFixedWidth(40)  # Fix width of tools panel
        
        # Style for tool buttons
        button_style = """
            QPushButton {
                background-color: #2A2A2A;
                border: none;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3A3A3A;
            }
            QPushButton:checked {
                background-color: #4A4A4A;
            }
        """
        
        # Create tool buttons with consistent styling
        for btn_data in [
            ("✏️", "Draw/Erase Toggle", self.drawing_handler.toggle_eraser, True),
            ("🎨", "Color Picker", self.drawing_handler.pick_color, False),
            ("⭐", "Draw Shape", self.drawing_handler.toggle_shape_drawing, True),
            ("↩️", "Undo", self.drawing_handler.undo, False),
            ("↪️", "Redo", self.drawing_handler.redo, False),
            ("🗑️", "Clear Canvas", self.drawing_handler.clear_canvas, False),
            ("💾", "Save Drawing", self.save_drawing, False),
            ("🖌️", "Brush Settings", self.show_brush_settings, False),
        ]:
            btn = QPushButton(btn_data[0])
            btn.setToolTip(btn_data[1])
            btn.setCheckable(btn_data[3])
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(button_style)
            btn.clicked.connect(btn_data[2])
            tools_layout.addWidget(btn)
            
        tools_layout.addStretch()  # Add stretch at bottom
        left_layout.addWidget(tools_widget)
        
        # Create a container for the drawing handler with padding
        drawing_container = QWidget()
        drawing_container_layout = QVBoxLayout(drawing_container)
        drawing_container_layout.setContentsMargins(10, 10, 10, 10)
        drawing_container_layout.addWidget(self.drawing_handler)
        
        left_layout.addWidget(drawing_container)
        
        # Add left panel to main layout with fixed width
        left_panel.setFixedWidth(562)  # 512 + 40 + margins
        main_layout.addWidget(left_panel)
        
        # Center panel - Generation controls
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        
        # Generate button
        generate_btn = QPushButton("🎨 Generate")
        generate_btn.setToolTip("Generate Image (Ctrl+G)")
        generate_btn.clicked.connect(self.generate_image)
        center_layout.addWidget(generate_btn)
        
        # Navigation
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("⬅️")
        prev_btn.setToolTip("Previous Image")
        prev_btn.clicked.connect(self.prev_image)
        next_btn = QPushButton("➡️")
        next_btn.setToolTip("Next Image")
        next_btn.clicked.connect(self.next_image)
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        center_layout.addLayout(nav_layout)
        
        main_layout.addWidget(center_panel)
        
        # Right panel - Generation settings
        right_panel = QWidget()
        right_panel.setFixedWidth(562)  # Match left panel width
        right_panel.setStyleSheet("""
            QLabel { color: #CCCCCC; }
            QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 5px;
                color: white;
                padding: 5px;
            }
            QPushButton {
                background-color: #2A2A2A;
                border: none;
                border-radius: 5px;
                padding: 8px;
                color: white;
            }
            QPushButton:hover {
                background-color: #3A3A3A;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        
        # Model loading section
        model_layout = QHBoxLayout()
        browse_btn = QPushButton("📂")
        browse_btn.setToolTip("Browse Model Path")
        browse_btn.clicked.connect(self.browse_model)
        self.reload_cb = QCheckBox("Reload Model")
        model_layout.addWidget(browse_btn)
        model_layout.addWidget(self.reload_cb)
        right_layout.addLayout(model_layout)
        
        # Prompt input
        right_layout.addWidget(QLabel("Prompt:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setMaximumHeight(60)
        right_layout.addWidget(self.prompt_input)
        
        # Negative prompt
        right_layout.addWidget(QLabel("Negative Prompt:"))
        self.neg_prompt_input = QTextEdit()
        self.neg_prompt_input.setMaximumHeight(60)
        self.neg_prompt_input.setPlainText("NSFW, bad quality, blurry")
        right_layout.addWidget(self.neg_prompt_input)
        
        # Scheduler selection
        right_layout.addWidget(QLabel("Scheduler:"))
        self.scheduler_combo = QComboBox()
        self.scheduler_combo.addItems(self.inference_handler.get_scheduler_names())
        self.scheduler_combo.currentTextChanged.connect(
            self.inference_handler.change_scheduler
        )
        right_layout.addWidget(self.scheduler_combo)
        
        # Generation parameters
        params_layout = QVBoxLayout()
        
        # Steps
        steps_layout = QHBoxLayout()
        steps_layout.addWidget(QLabel("Steps:"))
        self.steps_slider = QSpinBox()
        self.steps_slider.setRange(1, 100)
        self.steps_slider.setValue(20)
        steps_layout.addWidget(self.steps_slider)
        params_layout.addLayout(steps_layout)
        
        # Guidance scale
        guidance_layout = QHBoxLayout()
        guidance_layout.addWidget(QLabel("Guidance:"))
        self.guidance_slider = QDoubleSpinBox()
        self.guidance_slider.setRange(1, 20)
        self.guidance_slider.setValue(7.5)
        self.guidance_slider.setSingleStep(0.5)
        guidance_layout.addWidget(self.guidance_slider)
        params_layout.addLayout(guidance_layout)
        
        # Image guidance
        img_guidance_layout = QHBoxLayout()
        img_guidance_layout.addWidget(QLabel("Image Guidance:"))
        self.img_guidance_slider = QDoubleSpinBox()
        self.img_guidance_slider.setRange(0, 5)
        self.img_guidance_slider.setValue(1.5)
        self.img_guidance_slider.setSingleStep(0.1)
        img_guidance_layout.addWidget(self.img_guidance_slider)
        params_layout.addLayout(img_guidance_layout)
        
        # Seed
        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("Seed:"))
        self.seed_input = QSpinBox()
        self.seed_input.setRange(-1, 999999)
        self.seed_input.setValue(-1)
        self.seed_input.setSpecialValueText("Random")
        seed_layout.addWidget(self.seed_input)
        params_layout.addLayout(seed_layout)
        
        right_layout.addLayout(params_layout)
        
        # Result display
        self.result_label = QLabel()
        self.result_label.setMinimumSize(512, 512)
        self.result_label.setStyleSheet("border: 1px solid #333333;")
        self.result_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.result_label)
        
        # Status bar
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.progress_bar)
        status_layout.addWidget(self.status_label)
        right_layout.addLayout(status_layout)
        
        main_layout.addWidget(right_panel)
        
    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_drawing)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.drawing_handler.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self.drawing_handler.redo)
        QShortcut(QKeySequence("Ctrl+G"), self).activated.connect(self.generate_image)
        
    @Slot()
    def show_brush_settings(self):
        dialog = BrushSettingsDialog(self.drawing_handler, self)
        dialog.exec()
        
    @Slot()
    def browse_model(self):
        path = QFileDialog.getExistingDirectory(self, "Select Model Directory")
        if path and (self.reload_cb.isChecked() or not self.inference_handler.pipeline):
            self.inference_handler.load_model(path)
            
    @Slot()
    def save_drawing(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Drawing", "", "PNG Files (*.png)"
        )
        if file_path:
            self.drawing_handler.get_image().save(file_path)
            
    @Slot()
    def generate_image(self):
        if not self.inference_handler.pipeline and not self.reload_cb.isChecked():
            QMessageBox.warning(self, "Error", "Please load a model first!")
            return
            
        self.progress_bar.show()
        self.status_label.setText("Generating...")
        
        try:
            drawing = self.drawing_handler.get_image()
            
            props = SimpleNamespace(
                prompt=self.prompt_input.toPlainText(),
                negative_prompt=self.neg_prompt_input.toPlainText(),
                num_inference_steps=self.steps_slider.value(),
                guidance_scale=self.guidance_slider.value(),
                image_guidance_scale=self.img_guidance_slider.value(),
                seed=self.seed_input.value() if self.seed_input.value() >= 0 else None
            )
            
            result = self.inference_handler.generate_image(drawing, props)
            
            self.generated_images.append(result)
            self.current_image_index = len(self.generated_images) - 1
            self.display_current_image()
            
            self.status_label.setText("Generation complete!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Generation failed: {str(e)}")
            self.status_label.setText("Generation failed!")
            
        finally:
            self.progress_bar.hide()
            
    @Slot()
    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.display_current_image()
            
    @Slot()
    def next_image(self):
        if self.current_image_index < len(self.generated_images) - 1:
            self.current_image_index += 1
            self.display_current_image()
            
    def display_current_image(self):
        if 0 <= self.current_image_index < len(self.generated_images):
            image = self.generated_images[self.current_image_index]
            # Convert PIL Image to QPixmap using numpy as intermediate
            image_array = np.array(image)
            height, width, channels = image_array.shape
            qimage = QImage(
                image_array.data,
                width,
                height,
                width * channels,  # bytes per line
                QImage.Format_RGB888
            )
            pixmap = QPixmap.fromImage(qimage)
            self.result_label.setPixmap(pixmap.scaled(
                self.result_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DoodlePixUI()
    window.show()
    sys.exit(app.exec())