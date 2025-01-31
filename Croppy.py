import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import os
from tkinterdnd2 import TkinterDnD
import math
import time
import threading
from rembg import remove
import numpy as np
from queue import Queue
from PIL import Image, ImageTk, ImageOps

class ImageCropperApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Quick Image Cropper")
        self.geometry("800x600")
        
        # Set window background and border color
        self.configure(bg='#000000')  # Black background for window
        
        # Set custom icon (replace 'icon.ico' with your icon file path)
        try:
            self.iconbitmap('icon.ico')
        except:
            pass  # Fallback to default icon if file not found
        
        # Add output directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Add rembg related variables
        self.rembg_queue = Queue()
        self.processing_thread = None
        self.is_processing = False
        
        # Dark theme colors
        self.colors = {
            'bg': '#1e1e1e',
            'accent': '#ff9966',
            'text': '#ffffff',
            'viewport': '#68c2ff',
            'button_bg': '#000000',
            'button_fg': '#ffffff',
            'button_active': '#333333',
            'button_border': '#ffffff'
        }
        
        # Style configuration
        self.style = ttk.Style()
        
        # Set theme to default first
        self.style.theme_use('default')
        
        # Modern button style with rounded corners and explicit colors
        self.style.configure('Custom.TButton',
            padding=(2, 4),  # Even more horizontal padding
            background=self.colors['button_bg'],
            foreground=self.colors['button_fg'],
            bordercolor=self.colors['button_fg'],
            lightcolor=self.colors['button_bg'],
            darkcolor=self.colors['button_bg'],
            relief='groove',  # Try different relief style
            borderwidth=4,    # Thicker border
            # font=('Bradley Hand ITC', 10, 'bold'))
            # font=('Ink Free', 14, 'bold'))
            # font=('Juice ITC', 10, 'bold'))
            font=('Verdana', 12))
        
        
        # Button states mapping
        self.style.map('Custom.TButton',
            background=[('active', '#333333'), ('pressed', '#333333')],
            foreground=[('active', '#ffffff'), ('pressed', '#ffffff')],
            bordercolor=[('active', '#ffffff'), ('pressed', '#ffffff')],
            relief=[('pressed', 'flat')])
            
        # Modern checkbox style
        self.style.configure('Custom.TCheckbutton',
            background=self.colors['bg'],
            foreground=self.colors['text'],
            font=('Verdana', 10,),
            indicatorcolor=self.colors['button_bg'],
            indicatorrelief='flat',
            borderwidth=2,
            focuscolor=self.colors['button_border'])
            
        self.style.map('Custom.TCheckbutton',
            background=[('active', self.colors['bg'])],
            foreground=[('active', self.colors['text'])],
            indicatorcolor=[('selected', self.colors['accent']),
                          ('active', self.colors['button_active'])])

        # Configure other styles
        self.style.configure('Custom.TFrame', 
                           background=self.colors['bg'])
        self.style.configure('Custom.TLabel',
                           background=self.colors['bg'],
                           foreground=self.colors['text'],
                           font=('Verdana', 12))
        
        # Style the slider (Scale)
        self.style.configure('Custom.Horizontal.TScale',
            background=self.colors['bg'],
            troughcolor=self.colors['accent'],  # Pink background
            bordercolor=self.colors['viewport'],
            lightcolor=self.colors['text'],       # White handle
            darkcolor=self.colors['text'])        # White handle
            
        self.style.map('Custom.Horizontal.TScale',
            background=[('active', self.colors['bg'])],
            troughcolor=[('active', self.colors['viewport'])],
            lightcolor=[('active', '#ffffff')],   # White handle on hover
            darkcolor=[('active', '#ffffff')])    # White handle on hover

        # State variables
        self.image = None
        self.photo = None
        self.crop_mode = "square"  # or "free"
        self.drag_start = None
        self.crop_rect = None
        self.pan_start = None
        self.image_position = [0, 0]  # [x, y]
        self.zoom = 1.0
        self.counter = 1
        
        # Add popup related variables
        self.popup = None
        self.popup_thread = None
        
        # Add queue panel variables
        self.queue_items = []
        self.preview_size = (150, 150)
        
        # Change default background color
        self.bg_color_var = tk.StringVar(value='white')
        
       
        self.current_folder = None
        self.folder_images = []
        self.current_image_index = -1
        
        # Add output size variable
        self.output_size_var = tk.IntVar(value=512)
        
        # Style configuration for Entry widgets
        self.style.configure('Custom.TEntry',
            padding=5,
            fieldbackground=self.colors['button_bg'],
            foreground=self.colors['button_fg'],
            insertcolor=self.colors['button_fg'],  # Cursor color
            font=('Segoe UI', 9))
        
        # Add grid-related variables
        self.grid_mode = False
        self.grid_rows = tk.IntVar(value=2)
        self.grid_cols = tk.IntVar(value=2)
        self.grid_position = [0, 0]  # [x, y] offset for grid
        self.grid_drag_start = None
        
        # Add grid resize handles state
        self.grid_resize_handle = None
        self.grid_size = [0, 0]  # [width, height] of grid
        
        self.setup_ui()
        self.bind_events()
        self.start_background_processing()
    
    def setup_ui(self):
        # Main container
        main_container = ttk.Frame(self, style='Custom.TFrame')
        main_container.pack(fill='both', expand=True)
        
        # Left control panel (vertical layout)
        left_control_panel = ttk.Frame(main_container, style='Custom.TFrame')
        left_control_panel.pack(side='left', fill='y', padx=5, pady=5)
        
        # Mode switch button
        self.mode_btn = ttk.Button(left_control_panel, text="Mode: Square", 
                                  command=self.toggle_mode,
                                  style='Custom.TButton')
        self.mode_btn.pack(fill='x', pady=2)
        
        # Save button
        self.save_btn = ttk.Button(left_control_panel, text="Save Crop (S)", 
                                  command=self.save_crop,
                                  style='Custom.TButton')
        self.save_btn.pack(fill='x', pady=2)
        
        # Base name input with styled Entry
        ttk.Label(left_control_panel, text="Base name:", 
                 style='Custom.TLabel').pack(fill='x', pady=2)
        self.base_name = ttk.Entry(left_control_panel, 
                                 style='Custom.TEntry',
                                 font=('Segoe UI', 9))
        self.base_name.insert(0, "crop")
        self.base_name.pack(fill='x', pady=2)
        
        # Output size input
        ttk.Label(left_control_panel, text="Output size (px):", 
                 style='Custom.TLabel').pack(fill='x', pady=2)
        self.size_entry = ttk.Entry(left_control_panel,
                                  textvariable=self.output_size_var,
                                  style='Custom.TEntry',
                                  font=('Segoe UI', 9))
        self.size_entry.pack(fill='x', pady=2)
        
        # Folder selection button
        self.folder_btn = ttk.Button(left_control_panel, text="Select Output Folder", 
                                    command=self.select_output_folder,
                                    style='Custom.TButton')
        self.folder_btn.pack(fill='x', pady=2)
        
        # Background removal controls
        ttk.Separator(left_control_panel, orient='horizontal').pack(fill='x', pady=5)
        
        self.rembg_var = tk.BooleanVar(value=False)
        self.rembg_check = ttk.Checkbutton(left_control_panel, 
                                          text="Remove Background",
                                          variable=self.rembg_var,
                                          style='Custom.TCheckbutton')
        self.rembg_check.pack(fill='x', pady=2)
        
        # Add threshold control
        ttk.Label(left_control_panel, text="Removal Threshold :", 
                 style='Custom.TLabel').pack(fill='x', pady=2)
        self.threshold_var = tk.DoubleVar(value=0.5)  # Default threshold
        self.threshold_slider = ttk.Scale(left_control_panel, 
                                        from_=0.0, to=1.0,
                                        variable=self.threshold_var,
                                        orient='horizontal',
                                        style='Custom.Horizontal.TScale')
        self.threshold_slider.pack(fill='x', pady=2)
        
        ttk.Label(left_control_panel, text="Background:", 
                 style='Custom.TLabel').pack(fill='x', pady=2)
        for color in ['white', 'transparent', 'black']:  # Reordered with white first
            ttk.Radiobutton(left_control_panel, text=color.capitalize(),
                          variable=self.bg_color_var, value=color,
                          style='Custom.TCheckbutton').pack(fill='x')
        
        # Status label at bottom of left panel
        self.status_label = ttk.Label(left_control_panel, text="", 
                                     style='Custom.TLabel',
                                     wraplength=150)
        self.status_label.pack(side='bottom', fill='x', pady=5)
        
        # Navigation buttons
        nav_frame = ttk.Frame(left_control_panel, style='Custom.TFrame')
        nav_frame.pack(fill='x', pady=2)
        
        self.prev_btn = ttk.Button(nav_frame, text="← Prev", 
                                  command=self.load_previous_image,
                                  style='Custom.TButton')
        self.prev_btn.pack(side='left', expand=True, fill='x', padx=(0, 2))
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", 
                                  command=self.load_next_image,
                                  style='Custom.TButton')
        self.next_btn.pack(side='left', expand=True, fill='x', padx=(2, 0))
        
        grid_frame = ttk.LabelFrame(left_control_panel, text="Grid Controls", 
                                  style='Custom.TFrame')
        grid_frame.pack(fill='x', pady=5)
        
        self.grid_btn = ttk.Button(grid_frame, text="Toggle Grid", 
                                 command=self.toggle_grid,
                                 style='Custom.TButton')
        self.grid_btn.pack(fill='x', pady=2)
        
        # Row and column inputs
        row_frame = ttk.Frame(grid_frame, style='Custom.TFrame')
        row_frame.pack(fill='x', pady=2)
        ttk.Label(row_frame, text="Rows:", 
                 style='Custom.TLabel').pack(side='left')
        ttk.Entry(row_frame, textvariable=self.grid_rows,
                 width=5, style='Custom.TEntry').pack(side='right')
        
        col_frame = ttk.Frame(grid_frame, style='Custom.TFrame')
        col_frame.pack(fill='x', pady=2)
        ttk.Label(col_frame, text="Cols:", 
                 style='Custom.TLabel').pack(side='left')
        ttk.Entry(col_frame, textvariable=self.grid_cols,
                 width=5, style='Custom.TEntry').pack(side='right')
        
        # Center panel with canvas
        center_panel = ttk.Frame(main_container, style='Custom.TFrame')
        center_panel.pack(side='left', fill='both', expand=True)
        
        # Canvas for image display
        self.canvas = tk.Canvas(center_panel, bg=self.colors['viewport'])
        self.canvas.pack(fill='both', expand=True)
        
        # Right panel (queue) - now wider
        self.queue_panel = ttk.Frame(main_container, style='Custom.TFrame', width=200)
        self.queue_panel.pack(side='right', fill='y', padx=5, pady=5)
        self.queue_panel.pack_propagate(False)  # Maintain width
        
        ttk.Label(self.queue_panel, text="Processing Queue", 
                 style='Custom.TLabel').pack(pady=5)
        
        # Queue canvas with scrollbar
        self.queue_canvas = tk.Canvas(self.queue_panel, 
                                    bg=self.colors['bg'],
                                    highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.queue_panel, orient="vertical", 
                                command=self.queue_canvas.yview)
        
        scrollbar.pack(side="right", fill="y")
        self.queue_canvas.pack(side="left", fill="both", expand=True)
        
        # Frame for queue items
        self.queue_frame = ttk.Frame(self.queue_canvas, style='Custom.TFrame')
        self.queue_window = self.queue_canvas.create_window(
            (0, 0), window=self.queue_frame, anchor="nw", width=180
        )
        
        # Configure scrolling
        self.queue_frame.bind("<Configure>", self.on_queue_configure)
        self.queue_canvas.bind('<Configure>', self.on_canvas_configure)
        self.queue_canvas.bind('<MouseWheel>', self.on_queue_scroll)
        
        # Make sure canvas accepts drops
        self.canvas.drop_target_register('DND_Files')
        self.drop_target_register('DND_Files')  # Register main window too

    def bind_events(self):
        # Drag and drop bindings
        self.canvas.dnd_bind('<<Drop>>', self.handle_drop)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        
        # Mouse bindings with shift key check
        self.canvas.bind('<ButtonPress-1>', self.handle_click)
        self.canvas.bind('<B1-Motion>', self.handle_drag)
        self.canvas.bind('<ButtonRelease-1>', self.end_crop)
        self.canvas.bind('<ButtonPress-3>', self.start_pan)
        self.canvas.bind('<B3-Motion>', self.update_pan)
        self.canvas.bind('<MouseWheel>', self.zoom_image)
        
        # Grid bindings with Alt and Ctrl
        self.canvas.bind('<Alt-Button-1>', self.start_grid_drag)
        self.canvas.bind('<Alt-B1-Motion>', self.update_grid_drag)
        self.canvas.bind('<Alt-ButtonRelease-1>', lambda e: self.end_grid_drag())
        
        # Add Ctrl bindings for handles
        self.canvas.bind('<Control-Button-1>', self.start_grid_resize)
        self.canvas.bind('<Control-B1-Motion>', self.update_grid_resize)
        self.canvas.bind('<Control-ButtonRelease-1>', lambda e: self.end_grid_resize())
        
        # Other bindings remain the same
        self.bind('<s>', lambda e: self.save_crop())
        self.bind('<Left>', lambda e: self.load_previous_image())
        self.bind('<Right>', lambda e: self.load_next_image())
        
        # Make sure canvas accepts drops
        self.canvas.drop_target_register('DND_Files')
        self.drop_target_register('DND_Files')  # Register main window too

    def handle_drop(self, event):
        file_path = event.data
        # Clean up the file path (remove {} and quotes if present)
        file_path = file_path.strip('{}').strip('"')
        
        if os.path.isfile(file_path):
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.current_folder = os.path.dirname(file_path)
                self.load_folder_images()
                self.load_specific_image(file_path)
        elif os.path.isdir(file_path):
            self.current_folder = file_path
            self.load_folder_images()
            if self.folder_images:
                self.load_specific_image(self.folder_images[0])

    def load_folder_images(self):
        """Load all images from the current folder"""
        if not self.current_folder:
            return
            
        self.folder_images = []
        for entry in os.scandir(self.current_folder):
            if entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.folder_images.append(entry.path)
        
        # Sort by creation time to maintain folder order
        self.folder_images.sort(key=lambda x: os.path.getctime(x))
        
        # Update navigation buttons
        self.update_nav_buttons()

    def load_specific_image(self, file_path):
        """Load a specific image and update the index"""
        try:
            self.image = Image.open(file_path)
            # Make sure the file is in the list before finding its index
            if file_path not in self.folder_images:
                self.folder_images.append(file_path)
                self.folder_images.sort(key=lambda x: os.path.getctime(x))
            self.current_image_index = self.folder_images.index(file_path)
            self.update_image_display()
            self.update_nav_buttons()
            self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            self.status_label.config(text="Error loading image")

    def load_next_image(self):
        """Load the next image in the folder"""
        if not self.folder_images or self.current_image_index >= len(self.folder_images) - 1:
            return
            
        self.current_image_index += 1
        self.load_specific_image(self.folder_images[self.current_image_index])

    def load_previous_image(self):
        """Load the previous image in the folder"""
        if not self.folder_images or self.current_image_index <= 0:
            return
            
        self.current_image_index -= 1
        self.load_specific_image(self.folder_images[self.current_image_index])

    def update_nav_buttons(self):
        """Update the state of navigation buttons"""
        if not self.folder_images:
            self.prev_btn.state(['disabled'])
            self.next_btn.state(['disabled'])
            return
            
        # Update previous button
        if self.current_image_index <= 0:
            self.prev_btn.state(['disabled'])
        else:
            self.prev_btn.state(['!disabled'])
            
        # Update next button
        if self.current_image_index >= len(self.folder_images) - 1:
            self.next_btn.state(['disabled'])
        else:
            self.next_btn.state(['!disabled'])

    def load_image(self, path):
        """Load a single image without folder navigation"""
        try:
            self.image = Image.open(path)
            self.current_folder = os.path.dirname(path)
            self.load_folder_images()
            self.load_specific_image(path)
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            self.status_label.config(text="Error loading image")

    def update_image_display(self):
        if self.image:
            # Apply zoom
            new_size = (int(self.image.width * self.zoom), 
                       int(self.image.height * self.zoom))
            resized = self.image.resize(new_size, Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(resized)
            
            # Update canvas
            self.canvas.delete('image')  # Only delete the image
            self.canvas.create_image(self.image_position[0], self.image_position[1], 
                                   image=self.photo, anchor='nw', tags='image')
            
            # Redraw crop rectangle if it exists
            if self.crop_rect:
                self.draw_crop_rect(*self.crop_rect)
            
            # Clear and redraw grid if in grid mode
            self.canvas.delete('grid')
            if self.grid_mode:
                self.draw_grid()
    
    def draw_crop_rect(self, x1, y1, x2, y2):
        """Draw crop rectangle and corner handles"""
        # Clear existing rectangle and handles
        self.canvas.delete('crop_rect')
        self.canvas.delete('handle')
        
        # Draw rectangle
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline='white',
            dash=(10, 10),
            tags='crop_rect'
        )
        
        # Draw corner handles
        corner_size = 5
        corners = [
            (x1, y1, 'nw'), (x2, y1, 'ne'),
            (x1, y2, 'sw'), (x2, y2, 'se')
        ]
        
        for x, y, pos in corners:
            handle = self.canvas.create_oval(
                x-corner_size, y-corner_size,
                x+corner_size, y+corner_size,
                fill='#e74c3c',
                outline='white',
                tags=('handle', f'handle_{pos}')
            )
            # Remove old bindings since we're using handle_click now

    def start_handle_drag(self, event, position):
        """Start dragging a corner handle"""
        self.drag_handle = position
        self.drag_start = (event.x, event.y)

    def update_handle_drag(self, event, position):
        """Update crop rectangle while dragging handle"""
        if not self.crop_rect:
            return
            
        x1, y1, x2, y2 = self.crop_rect
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        
        # Update coordinates based on handle position
        if position == 'nw':
            x1 += dx
            y1 += dy
        elif position == 'ne':
            x2 += dx
            y1 += dy
        elif position == 'sw':
            x1 += dx
            y2 += dy
        elif position == 'se':
            x2 += dx
            y2 += dy
        
        # Maintain square aspect ratio if in square mode
        if self.crop_mode == "square":
            width = x2 - x1
            height = y2 - y1
            size = min(abs(width), abs(height))
            
            if position in ['nw', 'se']:
                if abs(width) > abs(height):
                    x2 = x1 + (size if width > 0 else -size)
                else:
                    y2 = y1 + (size if height > 0 else -size)
            else:
                if abs(width) > abs(height):
                    x1 = x2 - (size if width > 0 else -size)
                else:
                    y1 = y2 - (size if height > 0 else -size)
        
        # Update crop rectangle
        self.crop_rect = (x1, y1, x2, y2)
        self.draw_crop_rect(x1, y1, x2, y2)
        self.drag_start = (event.x, event.y)

    def toggle_mode(self):
        self.crop_mode = "free" if self.crop_mode == "square" else "square"
        self.mode_btn.config(text=f"Mode: {self.crop_mode.capitalize()}")
    
    def start_crop(self, event):
        if not self.image:
            return
        self.drag_start = (event.x, event.y)
        
    def update_crop(self, event):
        if not self.drag_start:
            return
            
        if self.crop_mode == "square":
            size = min(abs(event.x - self.drag_start[0]), 
                      abs(event.y - self.drag_start[1]))
            x1 = min(self.drag_start[0], self.drag_start[0] + size)
            y1 = min(self.drag_start[1], self.drag_start[1] + size)
            x2 = x1 + size
            y2 = y1 + size
        else:
            x1 = min(self.drag_start[0], event.x)
            y1 = min(self.drag_start[1], event.y)
            x2 = max(self.drag_start[0], event.x)
            y2 = max(self.drag_start[1], event.y)
        
        self.crop_rect = (x1, y1, x2, y2)
        self.draw_crop_rect(*self.crop_rect)
    
    def end_crop(self, event):
        self.drag_start = None
    
    def start_pan(self, event):
        self.pan_start = (event.x - self.image_position[0], 
                         event.y - self.image_position[1])
    
    def update_pan(self, event):
        if not self.pan_start:
            return
        self.image_position[0] = event.x - self.pan_start[0]
        self.image_position[1] = event.y - self.pan_start[1]
        self.update_image_display()
    
    def zoom_image(self, event):
        if not self.image:
            return
            
        # Get mouse position relative to canvas
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        
        # Store old zoom for ratio calculation
        old_zoom = self.zoom
        
        # Update zoom factor
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom *= factor
        self.zoom = max(0.1, min(5.0, self.zoom))  # Limit zoom range
        
        # Adjust position to zoom towards mouse pointer
        scale = self.zoom / old_zoom
        self.image_position[0] = x - (x - self.image_position[0]) * scale
        self.image_position[1] = y - (y - self.image_position[1]) * scale
        
        self.update_image_display()
    
    def move_image(self, dx, dy):
        if not self.image:
            return
        self.image_position[0] += dx
        self.image_position[1] += dy
        self.update_image_display()
    
    def select_output_folder(self):
        dir_path = filedialog.askdirectory(
            initialdir=self.output_dir,
            title="Select Output Directory"
        )
        if dir_path:  # If a directory was selected
            self.output_dir = dir_path
            self.status_label.config(text=f"Output folder: {dir_path}")
    
    def create_save_popup(self, filename):
        # Remove existing popup if any
        if self.popup:
            self.popup.destroy()
        
        # Create new popup
        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)  # Remove window decorations
        
        # Calculate position (bottom right)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        popup_width = 300
        popup_height = 60
        x = screen_width - popup_width - 20
        y = screen_height - popup_height - 40
        
        self.popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        
        # Style the popup
        frame = ttk.Frame(self.popup, style='Custom.TFrame')
        frame.pack(fill='both', expand=True)
        
        # Add save icon (✓) and message
        message = ttk.Label(frame, 
                          text=f"✓ Saved: {os.path.basename(filename)}", 
                          style='Custom.TLabel',
                          font=('Arial', 10))
        message.pack(pady=20)
        
        # Make semi-transparent
        self.popup.attributes('-alpha', 0.9)
        
        # Start fade out thread
        if self.popup_thread and self.popup_thread.is_alive():
            self.popup_thread.join()
        self.popup_thread = threading.Thread(target=self.fade_out_popup)
        self.popup_thread.start()
    
    def fade_out_popup(self):
        if not self.popup:
            return
            
        time.sleep(1)  # Show for 1 second
        
        # Fade out over 500ms
        for i in range(10):
            if not self.popup:
                return
            self.popup.attributes('-alpha', 0.9 - (i * 0.09))
            time.sleep(0.05)
        
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def start_background_processing(self):
        """Start the background processing thread"""
        def process_queue():
            while True:
                if not self.rembg_queue.empty() and not self.is_processing:
                    self.is_processing = True
                    crop_data = self.rembg_queue.get()
                    self.process_and_save_crop(**crop_data)
                    self.is_processing = False
                time.sleep(0.1)  # Prevent busy waiting
        
        self.processing_thread = threading.Thread(target=process_queue, daemon=True)
        self.processing_thread.start()

    def on_queue_configure(self, event):
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        self.queue_canvas.itemconfig(self.queue_window, width=event.width)

    def on_queue_scroll(self, event):
        """Handle mouse wheel scrolling in queue"""
        self.queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def add_to_queue_display(self, image, filename):
        """Add item to queue display, newest at top, max 3 items"""
        # Create initial preview
        preview = image.copy()
        preview.thumbnail(self.preview_size)
        photo = ImageTk.PhotoImage(preview)
        
        # Create frame for this queue item
        item_frame = ttk.Frame(self.queue_frame, style='Custom.TFrame')
        
        # Add preview image centered
        preview_frame = ttk.Frame(item_frame, style='Custom.TFrame')
        preview_frame.pack(fill='x', pady=2)
        preview_label = ttk.Label(preview_frame, image=photo)
        preview_label.image = photo  # Keep reference
        preview_label.pack(expand=True)
        
        # Add filename and processing status
        info_frame = ttk.Frame(item_frame, style='Custom.TFrame')
        info_frame.pack(fill='x', pady=2)
        
        name_label = ttk.Label(info_frame, 
                             text=os.path.basename(filename),
                             style='Custom.TLabel',
                             wraplength=150)
        name_label.pack(side='left', fill='x', expand=True)
        
        # Status label based on whether it's a background removal item
        if "_nobg" in filename:
            status_label = ttk.Label(info_frame, text="⏳", style='Custom.TLabel')
        else:
            status_label = ttk.Label(info_frame, text="✓", style='Custom.TLabel')
        status_label.pack(side='right', padx=5)
        
        # Store references
        queue_item = {
            'frame': item_frame,
            'preview': preview_label,
            'status': status_label,
            'filename': filename,
            'separator': None  # Will store separator reference if created
        }
        
        # First unpack all existing items and their separators
        for item in self.queue_items:
            item['frame'].pack_forget()
            if item['separator']:
                item['separator'].destroy()
                item['separator'] = None
        
        # Add new item to front of list
        self.queue_items.insert(0, queue_item)
        
        # Remove excess items
        while len(self.queue_items) > 3:  # Keep 3 items
            old_item = self.queue_items.pop()
            if old_item['separator']:
                old_item['separator'].destroy()
            old_item['frame'].destroy()
        
        # Pack all items in order (newest first) with new separators
        for i, item in enumerate(self.queue_items):
            item['frame'].pack(fill='x', padx=5, pady=5)
            # Add separator after each item except the last one
            if i < len(self.queue_items) - 1:
                separator = ttk.Separator(self.queue_frame, orient='horizontal')
                separator.pack(fill='x', padx=5)
                item['separator'] = separator
        
        # Update scroll region
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))

    def update_queue_item_status(self, filename, status):
        for item in self.queue_items:
            if item['filename'] == filename:
                if status == 'done':
                    item['status'].configure(text="✓")
                elif status == 'error':
                    item['status'].configure(text="❌")
                break

    def process_and_save_crop(self, image, filename, remove_bg=False, bg_color='transparent'):
        """Process and save a single cropped image"""
        try:
            if remove_bg:
                # Create a copy of the image for processing
                process_image = image.copy()
                # Remove background with threshold
                image_array = np.array(process_image)
                removed_bg = remove(image_array, 
                                 alpha_matting=True,
                                 alpha_matting_foreground_threshold=int(self.threshold_var.get() * 255),
                                 alpha_matting_background_threshold=int((1 - self.threshold_var.get()) * 255))
                process_image = Image.fromarray(removed_bg)
                
                # Apply background color if specified
                if bg_color != 'transparent':
                    # Create background layer
                    bg = Image.new('RGBA', process_image.size, 
                                 'white' if bg_color == 'white' else 'black')
                    # Composite the image over background
                    process_image = Image.alpha_composite(bg, process_image.convert('RGBA'))
                
                # Save processed image
                process_image.save(filename, 'PNG')
                
                # Update preview with processed image
                self.after(0, lambda: self.update_queue_preview(filename, process_image))
            else:
                # Save original image
                image.save(filename)
                
            # Update queue item status
            self.after(0, lambda: self.update_queue_item_status(filename, 'done'))
            # Show save popup
            self.after(0, lambda: self.create_save_popup(filename))
            print(f"Processed and saved: {filename}")
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            self.after(0, lambda: self.update_queue_item_status(filename, 'error'))

    def update_queue_preview(self, filename, processed_image):
        """Update queue preview with processed image"""
        for item in self.queue_items:
            if item['filename'] == filename:
                # Create new preview
                preview = processed_image.copy()
                preview.thumbnail(self.preview_size)
                photo = ImageTk.PhotoImage(preview)
                
                # Update preview label
                item['preview'].configure(image=photo)
                item['preview'].image = photo  # Keep reference
                break

    def save_crop(self):
        if self.grid_mode:
            self.save_grid_crops()
        else:
            if not self.crop_rect or not self.image:
                return
            
            # Get crop coordinates
            x1, y1, x2, y2 = self.crop_rect
            
            # Convert to image coordinates
            x1 = int((x1 - self.image_position[0]) / self.zoom)
            y1 = int((y1 - self.image_position[1]) / self.zoom)
            x2 = int((x2 - self.image_position[0]) / self.zoom)
            y2 = int((y2 - self.image_position[1]) / self.zoom)
            
            # Ensure correct order of coordinates
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            # Crop the image
            cropped = self.image.crop((x1, y1, x2, y2))
            
            # Resize based on mode and output_size
            target_size = self.output_size_var.get()
            if self.crop_mode == "square":
                cropped = cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)
                prefix = "square_"
            else:
                # Calculate new dimensions maintaining aspect ratio
                prefix = "free_"
                width, height = cropped.size
                if width > height:
                    new_width = target_size
                    new_height = int(height * (target_size / width))
                else:
                    new_height = target_size
                    new_width = int(width * (target_size / height))
                cropped = cropped.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Generate filename
            base = self.base_name.get() or "crop"
            base = f"{base}_{prefix}"
            
            while True:
                # Add "_nobg" suffix for background removal
                suffix = "_nobg" if self.rembg_var.get() else ""
                filename = os.path.join(self.output_dir, f"{base}{suffix}_{self.counter}.png")
                
                if not os.path.exists(filename):
                    if self.rembg_var.get():
                        # Queue for background removal
                        self.rembg_queue.put({
                            'image': cropped,
                            'filename': filename,
                            'remove_bg': True,
                            'bg_color': self.bg_color_var.get()
                        })
                        self.add_to_queue_display(cropped, filename)
                        self.status_label.config(
                            text=f"Queued for processing: {os.path.basename(filename)}")
                    else:
                        # Save normal crop directly
                        cropped.save(filename)
                        self.add_to_queue_display(cropped, filename)  # Add to queue display
                        self.create_save_popup(filename)
                        self.status_label.config(text=f"Saved: {os.path.basename(filename)}")
                    
                    self.counter += 1
                    break
                self.counter += 1

    def handle_click(self, event):
        """Handle mouse click based on modifier keys"""
        if event.state & 0x20000:  # Alt is pressed
            return  # Let grid handling take over
        elif event.state & 0x4:    # Ctrl is pressed
            return  # Let grid resize handling take over
        elif event.state & 0x1:    # Shift is pressed
            # Check if click is near a handle
            if self.crop_rect:
                x1, y1, x2, y2 = self.crop_rect
                corners = [
                    (x1, y1, 'nw'), (x2, y1, 'ne'),
                    (x1, y2, 'sw'), (x2, y2, 'se')
                ]
                
                # Check distance to each corner
                for cx, cy, pos in corners:
                    if abs(event.x - cx) < 10 and abs(event.y - cy) < 10:
                        self.drag_handle = pos
                        self.drag_start = (event.x, event.y)
                        return "break"
        else:
            # Disable grid mode on normal click
            if self.grid_mode:
                self.grid_mode = False
                self.grid_btn.config(text="Grid: Off")
            # Normal crop creation
            self.drag_handle = None
            self.drag_start = (event.x, event.y)

    def handle_drag(self, event):
        """Handle drag based on initial action"""
        if event.state & 0x1 and self.drag_handle:  # Shift pressed and handle selected
            self.update_handle_drag(event)
        elif self.drag_start:  # Normal crop
            self.update_crop(event)

    def update_handle_drag(self, event):
        """Update crop rectangle while dragging handle"""
        if not self.crop_rect:
            return
            
        x1, y1, x2, y2 = self.crop_rect
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        
        # Update coordinates based on handle position
        if self.drag_handle == 'nw':
            x1 += dx
            y1 += dy
        elif self.drag_handle == 'ne':
            x2 += dx
            y1 += dy
        elif self.drag_handle == 'sw':
            x1 += dx
            y2 += dy
        elif self.drag_handle == 'se':
            x2 += dx
            y2 += dy
        
        # Maintain square aspect ratio if in square mode
        if self.crop_mode == "square":
            width = x2 - x1
            height = y2 - y1
            size = min(abs(width), abs(height))
            
            if self.drag_handle in ['nw', 'se']:
                if abs(width) > abs(height):
                    x2 = x1 + (size if width > 0 else -size)
                else:
                    y2 = y1 + (size if height > 0 else -size)
            else:
                if abs(width) > abs(height):
                    x1 = x2 - (size if width > 0 else -size)
                else:
                    y1 = y2 - (size if height > 0 else -size)
        
        # Update crop rectangle
        self.crop_rect = (x1, y1, x2, y2)
        self.draw_crop_rect(x1, y1, x2, y2)
        self.drag_start = (event.x, event.y)

    def toggle_grid(self):
        """Toggle grid mode on/off"""
        self.grid_mode = not self.grid_mode
        self.grid_btn.config(text="Grid: On" if self.grid_mode else "Grid: Off")
        self.update_image_display()

    def start_grid_drag(self, event):
        """Start dragging the grid (Alt pressed)"""
        if not self.grid_mode:
            return
        
        # Only start grid drag if not resizing
        if not self.grid_resize_handle:
            self.grid_drag_start = (event.x - self.grid_position[0],
                                  event.y - self.grid_position[1])
        return "break"

    def update_grid_drag(self, event):
        """Update grid position while dragging (Alt pressed)"""
        if not self.grid_mode or not self.grid_drag_start:
            return
            
        # Only move grid if not resizing
        if not self.grid_resize_handle:
            self.grid_position[0] = event.x - self.grid_drag_start[0]
            self.grid_position[1] = event.y - self.grid_drag_start[1]
            self.update_image_display()
        return "break"

    def start_grid_resize(self, event):
        """Start resizing the grid with Ctrl pressed"""
        if not self.grid_mode:
            return
            
        # Check if clicking on a handle
        handle = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(handle)
        
        for tag in tags:
            if tag.startswith('grid_handle_'):
                self.grid_resize_handle = tag.split('_')[-1]
                self.drag_start = (event.x, event.y)
                return "break"
        
        return "break"

    def update_grid_resize(self, event):
        """Update grid size while Ctrl is pressed"""
        if not self.grid_mode or not self.grid_resize_handle:
            return
            
        # Calculate movement
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        
        # Update grid size based on handle
        if 'w' in self.grid_resize_handle:
            self.grid_position[0] += dx
            self.grid_size[0] -= dx
        if 'e' in self.grid_resize_handle:
            self.grid_size[0] += dx
        if 'n' in self.grid_resize_handle:
            self.grid_position[1] += dy
            self.grid_size[1] -= dy
        if 's' in self.grid_resize_handle:
            self.grid_size[1] += dy
        
        # Ensure minimum size
        min_size = 50
        if self.grid_size[0] < min_size:
            if 'w' in self.grid_resize_handle:
                self.grid_position[0] -= min_size - self.grid_size[0]
            self.grid_size[0] = min_size
        if self.grid_size[1] < min_size:
            if 'n' in self.grid_resize_handle:
                self.grid_position[1] -= min_size - self.grid_size[1]
            self.grid_size[1] = min_size
        
        self.drag_start = (event.x, event.y)
        self.update_image_display()
        return "break"

    def end_grid_drag(self):
        """End grid dragging"""
        self.grid_drag_start = None

    def end_grid_resize(self):
        """End grid resizing"""
        self.grid_resize_handle = None

    def draw_grid(self):
        """Draw the grid overlay with resize handles"""
        if not self.grid_mode or not self.image:
            return
            
        # Calculate default grid size if not set
        if self.grid_size[0] == 0 or self.grid_size[1] == 0:
            self.grid_size = [
                self.image.width * self.zoom,
                self.image.height * self.zoom
            ]
        
        # Draw grid lines
        cell_width = self.grid_size[0] / self.grid_cols.get()
        cell_height = self.grid_size[1] / self.grid_rows.get()
        
        # Draw vertical lines
        for i in range(self.grid_cols.get() + 1):
            x = self.grid_position[0] + (i * cell_width)
            self.canvas.create_line(
                x, self.grid_position[1],
                x, self.grid_position[1] + self.grid_size[1],
                fill='white', dash=(5, 5), tags='grid'
            )
        
        # Draw horizontal lines
        for i in range(self.grid_rows.get() + 1):
            y = self.grid_position[1] + (i * cell_height)
            self.canvas.create_line(
                self.grid_position[0], y,
                self.grid_position[0] + self.grid_size[0], y,
                fill='white', dash=(5, 5), tags='grid'
            )
        
        # Draw resize handles
        handle_size = 10
        handles = [
            # Corners
            ('nw', self.grid_position[0], self.grid_position[1]),
            ('ne', self.grid_position[0] + self.grid_size[0], self.grid_position[1]),
            ('sw', self.grid_position[0], self.grid_position[1] + self.grid_size[1]),
            ('se', self.grid_position[0] + self.grid_size[0], self.grid_position[1] + self.grid_size[1]),
            # Sides
            ('n', self.grid_position[0] + self.grid_size[0]/2, self.grid_position[1]),
            ('s', self.grid_position[0] + self.grid_size[0]/2, self.grid_position[1] + self.grid_size[1]),
            ('w', self.grid_position[0], self.grid_position[1] + self.grid_size[1]/2),
            ('e', self.grid_position[0] + self.grid_size[0], self.grid_position[1] + self.grid_size[1]/2)
        ]
        
        for pos, x, y in handles:
            self.canvas.create_rectangle(
                x - handle_size/2, y - handle_size/2,
                x + handle_size/2, y + handle_size/2,
                fill='#e74c3c', outline='white',
                tags=('grid', f'grid_handle_{pos}')
            )

    def save_grid_crops(self):
        """Save all grid cell crops"""
        if not self.grid_mode or not self.image:
            return
            
        # Calculate cell dimensions in image coordinates
        cell_width = self.grid_size[0] / self.grid_cols.get() / self.zoom
        cell_height = self.grid_size[1] / self.grid_rows.get() / self.zoom
        
        # Calculate grid offset in image coordinates
        offset_x = (self.grid_position[0] - self.image_position[0]) / self.zoom
        offset_y = (self.grid_position[1] - self.image_position[1]) / self.zoom
        
        # Crop and save each cell
        for row in range(self.grid_rows.get()):
            for col in range(self.grid_cols.get()):
                # Calculate crop coordinates
                x1 = offset_x + (col * cell_width)
                y1 = offset_y + (row * cell_height)
                x2 = x1 + cell_width
                y2 = y1 + cell_height
                
                # Ensure coordinates are within image bounds
                x1 = max(0, min(x1, self.image.width))
                y1 = max(0, min(y1, self.image.height))
                x2 = max(0, min(x2, self.image.width))
                y2 = max(0, min(y2, self.image.height))
                
                # Crop the cell
                cropped = self.image.crop((x1, y1, x2, y2))
                
                # Resize if needed
                target_size = self.output_size_var.get()
                cropped = cropped.resize((target_size, target_size), 
                                      Image.Resampling.LANCZOS)
                
                # Generate filename
                base = self.base_name.get() or "crop"
                suffix = "_nobg" if self.rembg_var.get() else ""
                filename = os.path.join(
                    self.output_dir,
                    f"{base}_grid_{row+1}x{col+1}{suffix}_{self.counter}.png"
                )
                
                # Save or queue for processing
                if self.rembg_var.get():
                    self.rembg_queue.put({
                        'image': cropped,
                        'filename': filename,
                        'remove_bg': True,
                        'bg_color': self.bg_color_var.get()
                    })
                    self.add_to_queue_display(cropped, filename)
                else:
                    cropped.save(filename)
                    self.add_to_queue_display(cropped, filename)
                
                self.counter += 1
        
        self.status_label.config(text=f"Saved {self.grid_rows.get() * self.grid_cols.get()} grid crops")

if __name__ == "__main__":
    app = ImageCropperApp()
    app.mainloop()