import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from PIL import Image, ImageTk
import os
from tkinterdnd2 import TkinterDnD
import math
import random

class PromptViewer(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Prompt Viewer")
        self.geometry("1200x800")
        
        # Set window background and border color
        self.configure(bg='#000000')
        
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
        self.style.theme_use('default')
        
        # Configure styles
        self.setup_styles()
        
        # State variables
        self.image_folder = None
        self.txt_folder = None
        self.current_index = -1
        self.image_files = []
        self.txt_files = []
        self.paired_files = []  # List of (image_path, txt_path) tuples
        self.current_image = None
        self.photo = None
        self.zoom = 1.0
        self.image_position = [0, 0]
        
        # Add these new instance variables
        self.tag_buttons = {}  # Dictionary to store tag buttons and their data
        self.tag_frame = None  # Will hold the scrollable frame for tags
        
        # Add new state variable
        self.image_folder2 = None
        self.current_image2 = None
        self.photo2 = None
        
        # Setup UI
        self.setup_ui()
        self.bind_events()
        
    def setup_styles(self):
        """Configure custom styles for widgets"""
        # Button style
        self.style.configure('Custom.TButton',
            padding=(10, 5),
            background=self.colors['button_bg'],
            foreground=self.colors['button_fg'],
            bordercolor=self.colors['button_fg'],
            font=('Verdana', 10))
            
        # Text style
        self.style.configure('Custom.TFrame',
            background=self.colors['bg'])
            
        # Label style
        self.style.configure('Custom.TLabel',
            background=self.colors['bg'],
            foreground=self.colors['text'],
            font=('Verdana', 10))
            
        # Entry style
        self.style.configure('Custom.TEntry',
            fieldbackground=self.colors['button_bg'],
            foreground=self.colors['button_fg'],
            insertcolor=self.colors['button_fg'])
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_container = ttk.Frame(self, style='Custom.TFrame')
        main_container.pack(fill='both', expand=True)
        
        # Top control panel
        control_panel = ttk.Frame(main_container, style='Custom.TFrame')
        control_panel.pack(fill='x', padx=5, pady=5)
        
        # Folder selection buttons
        self.img_folder_btn = ttk.Button(control_panel, 
                                       text="Select Image Folder",
                                       command=self.select_image_folder,
                                       style='Custom.TButton')
        self.img_folder_btn.pack(side='left', padx=5)
        
        self.txt_folder_btn = ttk.Button(control_panel, 
                                       text="Select Text Folder",
                                       command=self.select_txt_folder,
                                       style='Custom.TButton')
        self.txt_folder_btn.pack(side='left', padx=5)
        
        # Add second image folder button
        self.img_folder2_btn = ttk.Button(control_panel, 
                                        text="Select Second Image Folder",
                                        command=self.select_image_folder2,
                                        style='Custom.TButton')
        self.img_folder2_btn.pack(side='left', padx=5)
        
        # Navigation buttons
        self.prev_btn = ttk.Button(control_panel, 
                                 text="← Previous",
                                 command=self.prev_pair,
                                 style='Custom.TButton')
        self.prev_btn.pack(side='left', padx=5)
        
        self.next_btn = ttk.Button(control_panel, 
                                 text="Next →",
                                 command=self.next_pair,
                                 style='Custom.TButton')
        self.next_btn.pack(side='left', padx=5)
        
        # Add tag control panel below the main control panel
        tag_control_panel = ttk.Frame(main_container, style='Custom.TFrame')
        tag_control_panel.pack(fill='x', padx=5)
        
        # Add button
        add_tag_btn = ttk.Button(tag_control_panel, 
                                text="+ Add Tag",
                                command=self.add_new_tag,
                                style='Custom.TButton')
        add_tag_btn.pack(side='left', padx=5, pady=5)
        
        # Create scrollable frame for tags
        tag_scroll = ttk.Scrollbar(tag_control_panel, orient="horizontal")
        tag_scroll.pack(side='bottom', fill='x')
        
        self.tag_frame = tk.Canvas(tag_control_panel, 
                                 height=40,
                                 bg=self.colors['bg'],
                                 highlightthickness=0,
                                 xscrollcommand=tag_scroll.set)
        self.tag_frame.pack(fill='x', expand=True, pady=5)
        
        tag_scroll.config(command=self.tag_frame.xview)
        
        # Create frame inside canvas to hold buttons
        self.button_container = tk.Frame(self.tag_frame, bg=self.colors['bg'])
        self.tag_frame.create_window((0, 0), window=self.button_container, anchor='nw')
        
        # Configure scroll region when buttons are added/removed
        self.button_container.bind('<Configure>', self.on_frame_configure)
        
        # Content area
        content_frame = ttk.Frame(main_container, style='Custom.TFrame')
        content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left image canvas
        self.canvas = tk.Canvas(content_frame, 
                              bg=self.colors['bg'],
                              highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Center image canvas
        self.canvas2 = tk.Canvas(content_frame, 
                               bg=self.colors['bg'],
                               highlightthickness=0)
        self.canvas2.pack(side='left', fill='both', expand=True)
        
        # Text editor (right side)
        self.text_editor = tk.Text(content_frame,
                                 wrap='word',
                                 bg=self.colors['button_bg'],
                                 fg=self.colors['button_fg'],
                                 insertbackground=self.colors['button_fg'],
                                 font=('Consolas', 12))
        self.text_editor.pack(side='left', fill='both', expand=True)
        
        # Save button for text changes
        self.save_btn = ttk.Button(control_panel,
                                text="Save Changes (Ctrl+S)",
                                command=self.save_text,
                                style='Custom.TButton')
        self.save_btn.pack(side='right', padx=5)
        
        # Status label
        self.status_label = ttk.Label(main_container,
                                    text="No files loaded",
                                    style='Custom.TLabel')
        self.status_label.pack(side='bottom', fill='x', padx=5)
        
    def bind_events(self):
        """Bind keyboard and mouse events"""
        # Bind save shortcut globally
        self.bind('<Control-s>', lambda e: self.save_text())
        
        # Bind navigation keys to canvas and main window
        self.canvas.bind('<Left>', lambda e: self.prev_pair())
        self.canvas.bind('<Right>', lambda e: self.next_pair())
        self.bind('<Left>', self.handle_left_arrow)
        self.bind('<Right>', self.handle_right_arrow)
        
        # Canvas events for zooming
        self.canvas.bind('<MouseWheel>', self.handle_zoom)
        self.canvas.bind('<Button-4>', self.handle_zoom)
        self.canvas.bind('<Button-5>', self.handle_zoom)
        
    def select_image_folder(self):
        """Select folder containing images"""
        self.image_folder = filedialog.askdirectory()
        if self.image_folder:
            self.image_files = [f for f in os.listdir(self.image_folder)
                              if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self.update_pairs()
            
    def select_txt_folder(self):
        """Select folder containing text files"""
        self.txt_folder = filedialog.askdirectory()
        if self.txt_folder:
            self.txt_files = [f for f in os.listdir(self.txt_folder)
                            if f.lower().endswith('.txt')]
            self.update_pairs()
            
    def select_image_folder2(self):
        """Select second folder containing images"""
        self.image_folder2 = filedialog.askdirectory()
        if self.image_folder2:
            self.update_pairs()
            
    def update_pairs(self):
        """Match image files with their corresponding text files"""
        if not self.image_folder or not self.txt_folder:
            return
            
        self.paired_files = []
        for img_file in self.image_files:
            base_name = os.path.splitext(img_file)[0]
            txt_file = base_name + '.txt'
            
            # Check if second image exists (if folder is selected)
            img2_exists = False
            if self.image_folder2:
                img2_path = os.path.join(self.image_folder2, img_file)
                img2_exists = os.path.exists(img2_path)
            
            # Only add pairs if txt exists and (no second folder selected or second image exists)
            if txt_file in self.txt_files and (not self.image_folder2 or img2_exists):
                self.paired_files.append((
                    os.path.join(self.image_folder, img_file),
                    os.path.join(self.image_folder2, img_file) if self.image_folder2 else None,
                    os.path.join(self.txt_folder, txt_file)
                ))
        
        if self.paired_files:
            self.current_index = 0
            self.load_current_pair()
        
        self.status_label.config(
            text=f"Found {len(self.paired_files)} matching pairs")
            
    def load_current_pair(self):
        """Load current image-text pair"""
        if not self.paired_files or self.current_index < 0:
            return
            
        img_path, img2_path, txt_path = self.paired_files[self.current_index]
        
        # Load and display first image
        self.current_image = Image.open(img_path)
        self.update_image_display()
        
        # Load and display second image if it exists
        if img2_path:
            self.current_image2 = Image.open(img2_path)
            self.update_image2_display()
        else:
            self.canvas2.delete('all')
            self.current_image2 = None
            self.photo2 = None
        
        # Load and display text
        self.text_editor.delete('1.0', tk.END)
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                self.text_editor.insert('1.0', f.read())
        except Exception as e:
            self.status_label.config(text=f"Error loading text: {str(e)}")
            
        self.status_label.config(
            text=f"Pair {self.current_index + 1}/{len(self.paired_files)}: {os.path.basename(img_path)}")
            
    def update_image_display(self):
        """Update image display with current zoom and position"""
        if not self.current_image:
            return
            
        # Calculate new size
        new_width = int(self.current_image.width * self.zoom)
        new_height = int(self.current_image.height * self.zoom)
        
        # Resize image
        resized = self.current_image.resize((new_width, new_height),
                                          Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(resized)
        
        # Update canvas
        self.canvas.delete('all')
        self.canvas.create_image(self.image_position[0],
                               self.image_position[1],
                               anchor='nw',
                               image=self.photo)
                               
    def update_image2_display(self):
        """Update second image display with current zoom and position"""
        if not self.current_image2:
            return
            
        # Calculate new size
        new_width = int(self.current_image2.width * self.zoom)
        new_height = int(self.current_image2.height * self.zoom)
        
        # Resize image
        resized = self.current_image2.resize((new_width, new_height),
                                           Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        self.photo2 = ImageTk.PhotoImage(resized)
        
        # Update canvas
        self.canvas2.delete('all')
        self.canvas2.create_image(self.image_position[0],
                                self.image_position[1],
                                anchor='nw',
                                image=self.photo2)

    def handle_zoom(self, event):
        """Handle mouse wheel zoom"""
        if not self.current_image:
            return
            
        # Get zoom direction
        if event.num == 4 or event.delta > 0:
            self.zoom *= 1.1
        elif event.num == 5 or event.delta < 0:
            self.zoom /= 1.1
            
        # Limit zoom range
        self.zoom = max(0.1, min(5.0, self.zoom))
        
        self.update_image_display()
        self.update_image2_display()  # Update second image as well
        
    def save_text(self):
        """Save changes to text file"""
        if not self.paired_files or self.current_index < 0:
            return
            
        _, txt_path = self.paired_files[self.current_index]
        text_content = self.text_editor.get('1.0', tk.END).strip()
        
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            self.status_label.config(text=f"Saved changes to {os.path.basename(txt_path)}")
        except Exception as e:
            self.status_label.config(text=f"Error saving text: {str(e)}")
            
    def next_pair(self):
        """Load next image-text pair"""
        if not self.paired_files:
            return
            
        self.current_index = (self.current_index + 1) % len(self.paired_files)
        self.load_current_pair()
        
    def prev_pair(self):
        """Load previous image-text pair"""
        if not self.paired_files:
            return
            
        self.current_index = (self.current_index - 1) % len(self.paired_files)
        self.load_current_pair()

    def handle_left_arrow(self, event):
        """Handle left arrow key press"""
        # Check if text editor has focus
        if self.focus_get() != self.text_editor:
            self.prev_pair()
        
    def handle_right_arrow(self, event):
        """Handle right arrow key press"""
        # Check if text editor has focus
        if self.focus_get() != self.text_editor:
            self.next_pair()

    def on_frame_configure(self, event=None):
        """Reset the scroll region to encompass the inner frame"""
        self.tag_frame.configure(scrollregion=self.tag_frame.bbox("all"))

    def generate_contrasting_colors(self):
        """Generate a random background color and its contrast color for text"""
        # Generate random background color (not too dark or light)
        bg_color = '#{:06x}'.format(random.randint(0x404040, 0xCFCFCF))
        
        # Convert to RGB
        bg_rgb = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))
        
        # Calculate luminance
        luminance = (0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2])/255
        
        # Choose black or white text based on background luminance
        fg_color = '#000000' if luminance > 0.5 else '#FFFFFF'
        
        return bg_color, fg_color

    def add_new_tag(self):
        """Add a new tag button"""
        tag_text = simpledialog.askstring("New Tag", "Enter tag text:")
        if not tag_text:
            return
            
        position = simpledialog.askstring("Tag Position", 
                                        "Add tag at (start/end)?",
                                        initialvalue="end")
        if position not in ['start', 'end']:
            position = 'end'
            
        bg_color, fg_color = self.generate_contrasting_colors()
        
        # Create frame to hold button and controls
        tag_container = tk.Frame(self.button_container, bg=self.colors['bg'])
        tag_container.pack(side='left', padx=2)
        
        # Create the main tag button
        tag_button = tk.Button(tag_container,
                             text=tag_text,
                             bg=bg_color,
                             fg=fg_color,
                             command=lambda: self.add_tag_to_text(tag_text, position))
        tag_button.pack(side='left')
        
        # Add controls
        tk.Button(tag_container,
                 text='×',
                 command=lambda: self.delete_tag(tag_container, tag_text),
                 bg=self.colors['button_bg'],
                 fg=self.colors['button_fg']).pack(side='left')
                 
        tk.Button(tag_container,
                 text='-',
                 command=lambda: self.remove_tag_from_text(tag_text),
                 bg=self.colors['button_bg'],
                 fg=self.colors['button_fg']).pack(side='left')
                 
        tk.Button(tag_container,
                 text='+',
                 command=lambda: self.add_tag_to_text(tag_text, position),
                 bg=self.colors['button_bg'],
                 fg=self.colors['button_fg']).pack(side='left')
        
        self.tag_buttons[tag_text] = {
            'container': tag_container,
            'position': position,
            'colors': (bg_color, fg_color)
        }
        
        self.on_frame_configure()

    def delete_tag(self, container, tag_text):
        """Delete a tag button"""
        container.destroy()
        self.tag_buttons.pop(tag_text, None)
        self.on_frame_configure()

    def add_tag_to_text(self, tag_text, position):
        """Add tag text to the editor"""
        if position == 'start':
            current_text = self.text_editor.get('1.0', tk.END)
            self.text_editor.delete('1.0', tk.END)
            self.text_editor.insert('1.0', tag_text + ' ' + current_text)
        else:
            self.text_editor.insert(tk.END, ' ' + tag_text)

    def remove_tag_from_text(self, tag_text):
        """Remove all occurrences of tag from text"""
        current_text = self.text_editor.get('1.0', tk.END)
        new_text = current_text.replace(tag_text, '').replace('  ', ' ')
        self.text_editor.delete('1.0', tk.END)
        self.text_editor.insert('1.0', new_text)

if __name__ == "__main__":
    app = PromptViewer()
    app.mainloop()