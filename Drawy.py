from tkinter import Frame, Canvas, Button, Scale, HORIZONTAL, Label
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
from tkinterdnd2 import TkinterDnD, DND_FILES

class DrawingApp:
    def __init__(self):
        # Initialize root with TkinterDnD
        self.root = TkinterDnD.Tk()
        self.root.title("Dataset Drawing Tool")
        self.root.geometry("512x512")
        self.root.configure(bg='black')

        # State variables
        self.current_image_path = None
        self.image_folder = None
        self.output_folder = None
        self.image_files = []
        self.current_image_index = -1
        self.brush_size = 5
        self.brush_intensity = 1.0  # 0 = black, 1 = white
        
        # Initialize history for undo
        self.history = []
        self.max_history = 50
        
        # Drawing state
        self.prev_x = None
        self.prev_y = None
        self.drawing = False  # Add this to track when we're actually drawing
        self.stroke_points = []
        self.smoothing_amount = 0
        self.layer_opacity = 0.5
        
        # Initialize status label
        self.status_label = None
        
        # Add zoom state
        self.zoom_factor = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 4.0
        
        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        # Control panel
        control_frame = Frame(self.root, bg='black')
        control_frame.pack(pady=10)

        # Buttons (remove smoothing button)
        Button(control_frame, text="Set Output Folder", command=self.set_output_folder).pack(side='left', padx=5)
        Button(control_frame, text="Load Images", command=self.load_image_folder).pack(side='left', padx=5)
        Button(control_frame, text="Previous", command=self.prev_image).pack(side='left', padx=5)
        Button(control_frame, text="Next", command=self.next_image).pack(side='left', padx=5)

        # Sliders frame
        slider_frame = Frame(self.root, bg='black')
        slider_frame.pack(pady=5)

        # Brush size slider
        Scale(slider_frame, from_=1, to=50, orient=HORIZONTAL, label="Brush Size",
              command=self.update_brush_size, length=200, bg='black', fg='white').pack(side='left', padx=10)

        # Brush intensity slider
        Scale(slider_frame, from_=0, to=1, orient=HORIZONTAL, label="Brush Intensity",
              command=self.update_brush_intensity, length=200, resolution=0.01, bg='black', fg='white').pack(side='left', padx=10)

        # Add smoothing slider
        Scale(slider_frame, from_=0, to=20, orient=HORIZONTAL, label="Stroke Smoothing",
              command=self.update_smoothing, length=200, bg='black', fg='white').pack(side='left', padx=10)

        # Add layer opacity slider
        Scale(slider_frame, from_=0, to=1, orient=HORIZONTAL, label="Layer Opacity",
              command=self.update_opacity, length=200, resolution=0.01, bg='black', fg='white').pack(side='left', padx=10)

        # Add status label at the bottom
        self.status_label = Label(self.root, text="", bg='black', fg='white')
        self.status_label.pack(side='bottom', pady=5)

        # Canvas setup
        self.canvas_frame = Frame(self.root, bg='black')
        self.canvas_frame.pack(expand=True, fill='both', pady=10)

        self.canvas = Canvas(self.canvas_frame, bg='black', width=512, height=512)
        self.canvas.pack(expand=True)

        # Create two layers
        self.reference_layer = self.canvas.create_image(0, 0, anchor='nw')
        self.drawing_layer = self.canvas.create_image(0, 0, anchor='nw')
        
        # Initialize drawing surface
        self.drawing_surface = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        self.drawing_photo = ImageTk.PhotoImage(self.drawing_surface)
        self.canvas.itemconfig(self.drawing_layer, image=self.drawing_photo)

    def setup_bindings(self):
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        self.root.bind("<s>", self.save_drawing)
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Control-z>", self.undo)
        
        # Add mouse wheel binding for zoom
        self.canvas.bind("<MouseWheel>", self.handle_zoom)  # Windows
        self.canvas.bind("<Button-4>", self.handle_zoom)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.handle_zoom)    # Linux scroll down
        
        # Setup drag and drop
        self.canvas.drop_target_register(DND_FILES)
        self.canvas.dnd_bind('<<Drop>>', self.handle_drop)

    def start_drawing(self, event):
        self.drawing = True
        scale = 512 / (512 * self.zoom_factor)
        self.prev_x = event.x * scale
        self.prev_y = event.y * scale
        self.stroke_points = [(self.prev_x, self.prev_y)]

    def stop_drawing(self, event):
        if self.drawing:
            self.save_state()
        self.drawing = False
        self.prev_x = None
        self.prev_y = None
        self.stroke_points = []

    def draw(self, event):
        if not self.drawing:
            return

        # Convert event coordinates to original 512x512 space
        scale = 512 / (512 * self.zoom_factor)
        x = event.x * scale
        y = event.y * scale

        if self.smoothing_amount > 0:
            # Add point to stroke
            self.stroke_points.append((x, y))
            
            # Keep only last N points for smoothing based on smoothing amount
            window_size = int(self.smoothing_amount)
            if len(self.stroke_points) > window_size:
                self.stroke_points = self.stroke_points[-window_size:]
            
            # Calculate smoothed point
            x = sum(p[0] for p in self.stroke_points) / len(self.stroke_points)
            y = sum(p[1] for p in self.stroke_points) / len(self.stroke_points)

        # Draw line
        draw = ImageDraw.Draw(self.drawing_surface)
        color = int(255 * self.brush_intensity)
        if self.prev_x is not None:
            draw.line([self.prev_x, self.prev_y, x, y], 
                     fill=(color, color, color, color), 
                     width=self.brush_size)
        
        self.prev_x, self.prev_y = x, y
        
        # Update canvas with zoomed version
        current_size = int(512 * self.zoom_factor)
        resized_draw = self.drawing_surface.resize((current_size, current_size), Image.Resampling.LANCZOS)
        self.drawing_photo = ImageTk.PhotoImage(resized_draw)
        self.canvas.itemconfig(self.drawing_layer, image=self.drawing_photo)

    def update_brush_size(self, value):
        self.brush_size = int(float(value))

    def update_brush_intensity(self, value):
        self.brush_intensity = float(value)

    def update_smoothing(self, value):
        self.smoothing_amount = float(value)

    def update_opacity(self, value):
        self.layer_opacity = float(value)
        self.update_layer_opacity()

    def update_layer_opacity(self):
        if hasattr(self, 'drawing_surface'):
            # Create a copy of the drawing surface with updated opacity
            temp_surface = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            temp_surface.paste(self.drawing_surface, (0, 0))
            
            # Update alpha channel
            bands = list(temp_surface.split())
            if len(bands) == 4:  # If RGBA
                bands[3] = bands[3].point(lambda x: int(x * self.layer_opacity))
                temp_surface = Image.merge('RGBA', bands)
            
            self.drawing_photo = ImageTk.PhotoImage(temp_surface)
            self.canvas.itemconfig(self.drawing_layer, image=self.drawing_photo)

    def save_state(self):
        if len(self.history) >= self.max_history:
            self.history.pop(0)
        self.history.append(self.drawing_surface.copy())

    def undo(self, event=None):
        if self.history:
            self.drawing_surface = self.history.pop()
            self.drawing_photo = ImageTk.PhotoImage(self.drawing_surface)
            self.canvas.itemconfig(self.drawing_layer, image=self.drawing_photo)
            if self.status_label:
                self.status_label.config(text="Undo")

    def load_image_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.image_folder = folder
            self.image_files = [f for f in os.listdir(folder) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if self.image_files:
                self.current_image_index = 0
                self.load_current_image()

    def set_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder = folder

    def load_current_image(self):
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = os.path.join(self.image_folder, self.image_files[self.current_image_index])
            self.current_image_path = image_path
            
            # Load and resize reference image
            current_size = int(512 * self.zoom_factor)
            image = Image.open(image_path)
            image = image.resize((current_size, current_size), Image.Resampling.LANCZOS)
            self.reference_photo = ImageTk.PhotoImage(image)
            self.canvas.itemconfig(self.reference_layer, image=self.reference_photo)
            
            # Reset drawing layer
            self.drawing_surface = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            resized_draw = self.drawing_surface.resize((current_size, current_size), Image.Resampling.LANCZOS)
            self.drawing_photo = ImageTk.PhotoImage(resized_draw)
            self.canvas.itemconfig(self.drawing_layer, image=self.drawing_photo)

    def next_image(self):
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()

    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()

    def save_drawing(self, event=None):
        if not self.output_folder:
            self.status_label.config(text="Error: Please set output folder first")
            return
        
        if not self.current_image_path:
            self.status_label.config(text="Error: No image loaded")
            return

        # Create black background
        final_image = Image.new('RGB', (512, 512), (0, 0, 0))
        alphaInt= int(255 * self.brush_intensity)
        #make sure drawing surface is full alpha 255
        self.drawing_surface = self.drawing_surface.convert('RGBA')
        self.drawing_surface.putalpha(alphaInt)
        
        # Composite drawing layer
        final_image.paste(self.drawing_surface, (0, 0), self.drawing_surface)
        
        # Save with same name as input
        output_name = os.path.basename(self.current_image_path)
        output_path = os.path.join(self.output_folder, output_name)
        final_image.save(output_path)
        
        # Update status label instead of showing popup
        self.status_label.config(text=f"Saved: {output_name}")

    def handle_drop(self, event):
        file_path = event.data.strip('{}')  # Clean the file path
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.image_folder = os.path.dirname(file_path)
            self.image_files = [f for f in os.listdir(self.image_folder) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self.current_image_index = self.image_files.index(os.path.basename(file_path))
            self.load_current_image()

    def handle_zoom(self, event):
        # Get the current size
        current_size = int(512 * self.zoom_factor)
        
        # Handle different event types (Windows vs Linux)
        if event.num == 5 or event.delta < 0:  # Zoom out
            self.zoom_factor = max(self.min_zoom, self.zoom_factor - 0.1)
        elif event.num == 4 or event.delta > 0:  # Zoom in
            self.zoom_factor = min(self.max_zoom, self.zoom_factor + 0.1)
            
        # Calculate new size
        new_size = int(512 * self.zoom_factor)
        
        # Resize canvas
        self.canvas.config(width=new_size, height=new_size)
        
        # Update both layers with new size
        if hasattr(self, 'reference_photo') and self.reference_photo:
            image = Image.open(self.current_image_path)
            resized_ref = image.resize((new_size, new_size), Image.Resampling.LANCZOS)
            self.reference_photo = ImageTk.PhotoImage(resized_ref)
            self.canvas.itemconfig(self.reference_layer, image=self.reference_photo)
            
        if hasattr(self, 'drawing_surface') and self.drawing_surface:
            resized_draw = self.drawing_surface.resize((new_size, new_size), Image.Resampling.LANCZOS)
            self.drawing_photo = ImageTk.PhotoImage(resized_draw)
            self.canvas.itemconfig(self.drawing_layer, image=self.drawing_photo)

if __name__ == "__main__":
    app = DrawingApp()
    app.root.mainloop()