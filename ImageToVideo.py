import sys
import os
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QFileDialog, QListWidget, QSlider, 
                            QSpinBox, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, QUrl, QSize, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QIcon

class VideoGeneratorThread(QThread):
    progress_updated = Signal(int)
    video_completed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, image_paths, output_path, fps):
        super().__init__()
        self.image_paths = image_paths
        self.output_path = output_path
        self.fps = fps
        
    def run(self):
        try:
            if not self.image_paths:
                self.error_occurred.emit("No images to process")
                return
                
            # Get the first image to determine dimensions
            first_img = cv2.imread(self.image_paths[0])
            if first_img is None:
                self.error_occurred.emit(f"Failed to read image: {self.image_paths[0]}")
                return
                
            height, width, _ = first_img.shape
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, (width, height))
            
            # Process each image
            total_images = len(self.image_paths)
            for i, img_path in enumerate(self.image_paths):
                img = cv2.imread(img_path)
                if img is None:
                    self.error_occurred.emit(f"Failed to read image: {img_path}")
                    continue
                    
                # Resize if dimensions don't match
                if img.shape[0] != height or img.shape[1] != width:
                    img = cv2.resize(img, (width, height))
                    
                video_writer.write(img)
                progress = int((i + 1) / total_images * 100)
                self.progress_updated.emit(progress)
                
            video_writer.release()
            self.video_completed.emit(self.output_path)
            
        except Exception as e:
            self.error_occurred.emit(f"Error generating video: {str(e)}")


class ImagePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.current_pixmap = None
        self.setStyleSheet("background-color: #2a2a2a;")
        
    def setPixmap(self, pixmap):
        self.current_pixmap = pixmap
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.current_pixmap:
            painter = self.window().createPainter(self)
            scaled_pixmap = self.current_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the pixmap
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)


class ImageToVideoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image to Video Converter")
        self.setMinimumSize(800, 600)
        
        self.image_paths = []
        self.current_preview_index = 0
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self.update_preview)
        self.is_previewing = False
        
        self.init_ui()
        
    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Top section: Preview area and image list
        top_layout = QHBoxLayout()
        
        # Preview area
        self.preview_widget = ImagePreviewWidget()
        top_layout.addWidget(self.preview_widget, 2)
        
        # Image list section
        list_layout = QVBoxLayout()
        list_label = QLabel("Images (Drag & Drop)")
        self.image_list = QListWidget()
        self.image_list.setAcceptDrops(True)
        self.image_list.setDragEnabled(True)
        self.image_list.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.image_list.setMinimumWidth(200)
        self.image_list.currentRowChanged.connect(self.display_selected_image)
        
        # Enable drag and drop for the list widget
        self.setAcceptDrops(True)
        
        # Buttons for image list
        list_buttons_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Images")
        self.remove_btn = QPushButton("Remove Selected")
        self.clear_btn = QPushButton("Clear All")
        
        self.add_btn.clicked.connect(self.add_images)
        self.remove_btn.clicked.connect(self.remove_selected_images)
        self.clear_btn.clicked.connect(self.clear_images)
        
        list_buttons_layout.addWidget(self.add_btn)
        list_buttons_layout.addWidget(self.remove_btn)
        list_buttons_layout.addWidget(self.clear_btn)
        
        list_layout.addWidget(list_label)
        list_layout.addWidget(self.image_list)
        list_layout.addLayout(list_buttons_layout)
        
        top_layout.addLayout(list_layout, 1)
        
        # Middle section: Controls
        controls_layout = QHBoxLayout()
        
        # FPS control
        fps_layout = QVBoxLayout()
        fps_label = QLabel("Framerate (FPS):")
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 60)
        self.fps_spinbox.setValue(24)
        fps_layout.addWidget(fps_label)
        fps_layout.addWidget(self.fps_spinbox)
        controls_layout.addLayout(fps_layout)
        
        # Preview controls
        preview_layout = QVBoxLayout()
        preview_label = QLabel("Preview:")
        preview_buttons = QHBoxLayout()
        self.preview_btn = QPushButton("Start Preview")
        self.preview_btn.clicked.connect(self.toggle_preview)
        preview_buttons.addWidget(self.preview_btn)
        preview_layout.addWidget(preview_label)
        preview_layout.addLayout(preview_buttons)
        controls_layout.addLayout(preview_layout)
        
        # Export controls
        export_layout = QVBoxLayout()
        export_label = QLabel("Export:")
        self.export_btn = QPushButton("Export Video")
        self.export_btn.clicked.connect(self.export_video)
        export_layout.addWidget(export_label)
        export_layout.addWidget(self.export_btn)
        controls_layout.addLayout(export_layout)
        
        # Bottom section: Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Add all layouts to main layout
        main_layout.addLayout(top_layout)
        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.progress_bar)
        
        self.setCentralWidget(main_widget)
        
    def createPainter(self, widget):
        from PySide6.QtGui import QPainter
        return QPainter(widget)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        self.add_image_urls(urls)
        
    def add_image_urls(self, urls):
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path) and self.is_image_file(file_path):
                if file_path not in self.image_paths:
                    self.image_paths.append(file_path)
        
        # Sort images alphanumerically
        self.image_paths.sort(key=self.natural_sort_key)
        self.update_image_list()
        
    def natural_sort_key(self, s):
        import re
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
    def is_image_file(self, file_path):
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
        return any(file_path.lower().endswith(ext) for ext in image_extensions)
        
    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Images", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.gif)"
        )
        
        if files:
            for file_path in files:
                if file_path not in self.image_paths:
                    self.image_paths.append(file_path)
            
            # Sort images alphanumerically
            self.image_paths.sort(key=self.natural_sort_key)
            self.update_image_list()
            
    def update_image_list(self):
        self.image_list.clear()
        for path in self.image_paths:
            self.image_list.addItem(os.path.basename(path))
            
        if self.image_paths and self.current_preview_index >= len(self.image_paths):
            self.current_preview_index = 0
            
        if self.image_paths:
            self.image_list.setCurrentRow(self.current_preview_index)
            self.display_selected_image(self.current_preview_index)
            
    def remove_selected_images(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            idx = self.image_list.row(item)
            if 0 <= idx < len(self.image_paths):
                del self.image_paths[idx]
                
        self.update_image_list()
        
    def clear_images(self):
        self.image_paths = []
        self.update_image_list()
        self.preview_widget.setPixmap(None)
        
    def display_selected_image(self, index):
        if 0 <= index < len(self.image_paths):
            pixmap = QPixmap(self.image_paths[index])
            if not pixmap.isNull():
                self.preview_widget.setPixmap(pixmap)
                
    def toggle_preview(self):
        if self.is_previewing:
            self.preview_timer.stop()
            self.is_previewing = False
            self.preview_btn.setText("Start Preview")
        else:
            if not self.image_paths:
                QMessageBox.warning(self, "Warning", "No images to preview")
                return
                
            self.is_previewing = True
            self.preview_btn.setText("Stop Preview")
            fps = self.fps_spinbox.value()
            self.preview_timer.start(1000 // fps)  # Convert fps to milliseconds
            
    def update_preview(self):
        if not self.image_paths:
            self.toggle_preview()
            return
            
        self.current_preview_index = (self.current_preview_index + 1) % len(self.image_paths)
        self.image_list.setCurrentRow(self.current_preview_index)
        self.display_selected_image(self.current_preview_index)
        
    def export_video(self):
        if not self.image_paths:
            QMessageBox.warning(self, "Warning", "No images to export")
            return
            
        output_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Video", 
            "", 
            "MP4 Files (*.mp4)"
        )
        
        if not output_path:
            return
            
        if not output_path.lower().endswith('.mp4'):
            output_path += '.mp4'
            
        fps = self.fps_spinbox.value()
        
        # Stop preview if running
        if self.is_previewing:
            self.toggle_preview()
            
        # Show progress bar
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Start video generation in a separate thread
        self.video_thread = VideoGeneratorThread(self.image_paths, output_path, fps)
        self.video_thread.progress_updated.connect(self.update_progress)
        self.video_thread.video_completed.connect(self.video_export_completed)
        self.video_thread.error_occurred.connect(self.show_error)
        self.video_thread.start()
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def video_export_completed(self, output_path):
        self.progress_bar.setVisible(False)
        QMessageBox.information(
            self, 
            "Export Complete", 
            f"Video has been exported to:\n{output_path}"
        )
        
    def show_error(self, message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for a consistent look across platforms
    
    # Set dark theme
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, Qt.GlobalColor.darkGray)
    palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Base, Qt.GlobalColor.darkGray)
    palette.setColor(palette.ColorRole.AlternateBase, Qt.GlobalColor.darkGray)
    palette.setColor(palette.ColorRole.ToolTipBase, Qt.GlobalColor.darkGray)
    palette.setColor(palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.Button, Qt.GlobalColor.darkGray)
    palette.setColor(palette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(palette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(palette.ColorRole.Highlight, Qt.GlobalColor.darkBlue)
    palette.setColor(palette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    window = ImageToVideoApp()
    window.show()
    sys.exit(app.exec()) 