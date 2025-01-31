import os
import json
import imageio

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image
from moviepy.editor import ImageSequenceClip, VideoFileClip, concatenate_videoclips
import re

# Enhanced UI design and integration
class MediaToolkitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Toolkit App")
        self.configure(bg='black')
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.create_tabs()
        self.apply_styles()

    def apply_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', background='#f0c040', foreground='black', font=('Arial', 10, 'bold'))
        style.configure('TLabel', background='black', foreground='white', font=('Arial', 10, 'bold'))
        style.configure('TEntry', background='gray', foreground='white', insertbackground='white')
        style.map('TButton', background=[('active', '#e0b030')])

    def create_tabs(self):
        tab_control = ttk.Notebook(self)
        tab_control.pack(expand=1, fill="both")

        self.file_hierarchy_tab(tab_control)
        self.image_processing_tab(tab_control)
        self.video_processing_tab(tab_control)

    def setup_ui_components(self, tab, operations):
        for operation in operations:
            frame = ttk.Frame(tab, padding=5)
            frame.pack(fill='x', padx=5, pady=5)

            tk.Label(frame, text=operation["label_text"], bg='black', fg='white').pack(side='left')
            input_field = tk.Entry(frame, bg='gray', fg='white')
            input_field.pack(side='left', fill='x', expand=True)
            tk.Button(frame, text="Browse", command=lambda f=input_field: self.update_entry_with_directory(f)).pack(side='left')

            tk.Button(tab, text=operation["button_text"], bg='#f0c040', command=lambda f=input_field, op=operation: op["command"](f.get())).pack(fill='x', padx=10, pady=5)
    def setup_general_controls(self, tab, operation):
        input_dir = tk.StringVar()
        output_dir = tk.StringVar()
        tk.Label(tab, text="Input Directory:", bg='black', fg='white').pack(fill='x')
        tk.Entry(tab, textvariable=input_dir, bg='gray', fg='white').pack(fill='x')
        tk.Label(tab, text="Output Directory:", bg='black', fg='white').pack(fill='x')
        tk.Entry(tab, textvariable=output_dir, bg='gray', fg='white').pack(fill='x')
        tk.Button(tab, text="Browse", bg='black', fg='white',
                    command=lambda: input_dir.set(filedialog.askdirectory())).pack(fill='x')
        tk.Button(tab, text="Browse", bg='black', fg='white',
                    command=lambda: output_dir.set(filedialog.askdirectory())).pack(fill='x')
        tk.Button(tab, text=operation["button_text"], bg='black', fg='white',
                    command=lambda: operation["command"](input_dir.get(), output_dir.get())).pack(fill='x')

    def update_entry_with_directory(self, entry_field):
        directory = filedialog.askdirectory()
        if directory:  # Only update if a directory was selected
            entry_field.delete(0, tk.END)
            entry_field.insert(0, directory)


    def file_hierarchy_tab(self, tab_control):
        tab = ttk.Frame(tab_control)
        tab_control.add(tab, text='File Hierarchy')

        # Keep reference to input_field and output_text
        input_field = tk.Entry(tab, bg='gray', fg='white')
        input_field.pack(side='top', fill='x', padx=5, pady=5)

        output_text = ScrolledText(tab, wrap='word', bg='black', fg='white', insertbackground='white')
        output_text.pack(side='top', fill='both', expand=True, padx=5, pady=5)

        tk.Button(tab, text="Browse", bg='#f0c040', fg='black',
                  command=lambda: self.update_entry_with_directory(input_field)).pack(side='top', fill='x', padx=10, pady=2)
        tk.Button(tab, text="Print Hierarchy", bg='#f0c040', fg='black',
                  command=lambda: self.print_hierarchy(input_field.get(), output_text)).pack(side='top', fill='x', padx=10, pady=2)
        
    def image_processing_tab(self, tab_control):
        tab = ttk.Frame(tab_control)
        tab_control.add(tab, text='Image Processing')

        tk.Label(tab, text="Input Directory:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        input_entry = tk.Entry(tab, textvariable=self.input_dir, bg='gray', fg='white')
        input_entry.pack(fill='x', padx=5, pady=2)
        tk.Button(tab, text="Browse", bg='#f0c040', fg='black', command=lambda: self.update_entry_with_directory(input_entry)).pack(fill='x', padx=5, pady=2)
        
        tk.Label(tab, text="Output Directory:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        output_entry = tk.Entry(tab, textvariable=self.output_dir, bg='gray', fg='white')
        output_entry.pack(fill='x', padx=5, pady=2)
        tk.Button(tab, text="Browse", bg='#f0c040', fg='black', command=lambda: self.update_entry_with_directory(output_entry)).pack(fill='x', padx=5, pady=2)

        # Button for operations
        tk.Button(tab, text="Resize Images", bg='#f0c040', fg='black', command=self.resize_images_dialog).pack(fill='x', padx=10, pady=5)
        tk.Button(tab, text="Flip Images", bg='#f0c040', fg='black', command=self.flip_images_dialog).pack(fill='x', padx=10, pady=5)
        tk.Button(tab, text="Optimize Images", bg='#f0c040', fg='black', command=self.optimize_images_dialog).pack(fill='x', padx=10, pady=5)
        tk.Button(tab, text="Rename Images", bg='#f0c040', fg='black', command=self.rename_files_dialog).pack(fill='x', padx=10, pady=5)

    def video_processing_tab(self, tab_control):
        tab = ttk.Frame(tab_control)
        tab_control.add(tab, text='Video Processing')

        tk.Label(tab, text="Input Directory:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        input_entry = tk.Entry(tab, textvariable=self.input_dir, bg='gray', fg='white')
        input_entry.pack(fill='x', padx=5, pady=2)
        tk.Button(tab, text="Browse", bg='#f0c040', fg='black', command=lambda: self.update_entry_with_directory(input_entry)).pack(fill='x', padx=5, pady=2)
        
        tk.Label(tab, text="Output Directory:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        output_entry = tk.Entry(tab, textvariable=self.output_dir, bg='gray', fg='white')
        output_entry.pack(fill='x', padx=5, pady=2)
        tk.Button(tab, text="Browse", bg='#f0c040', fg='black', command=lambda: self.update_entry_with_directory(output_entry)).pack(fill='x', padx=5, pady=2)

        
        tk.Label(tab, text="FPS:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        self.fps = tk.Entry(tab, bg='gray', fg='white')
        self.fps.pack(fill='x', padx=5, pady=2)
        
        tk.Button(tab, text="Create Video from Images", bg='#f0c040', fg='black', command=self.create_video_from_images_dialog).pack(fill='x', padx=10, pady=5)
        tk.Label(tab, text="Resize Video Width:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        self.resize_width_entry = tk.Entry(tab, bg='gray', fg='white')
        self.resize_width_entry.pack(fill='x', padx=5, pady=2)

        tk.Label(tab, text="Resize Video Height:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        self.resize_height_entry = tk.Entry(tab, bg='gray', fg='white')
        self.resize_height_entry.pack(fill='x', padx=5, pady=2)
        
        tk.Label(tab, text="First Index Convention:", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        self.start_index = tk.Entry(tab, bg='gray', fg='white')
        self.start_index.pack(fill='x', padx=5, pady=2)
        tk.Button(tab, text="Resize Video", bg='#f0c040', fg='black', command=self.resize_video_dialog).pack(fill='x', padx=10, pady=5)


        tk.Button(tab, text="Merge Videos", bg='#f0c040', fg='black', command=self.merge_videos_in_folder).pack(fill='x', padx=10, pady=5)

        tk.Label(tab, text="Frame Range (start-end):", bg='black', fg='white').pack(fill='x', padx=5, pady=2)
        range_entry = tk.Entry(tab, bg='gray', fg='white')
        range_entry.pack(fill='x', padx=5, pady=2)

        tk.Button(tab, text="Split Video into Frames", bg='#f0c040', fg='black', command=lambda: self.split_video_frames(input_entry.get(), output_entry.get())).pack(fill='x', padx=10, pady=5)

    def rename_files_dialog(self):
        self.rename_files(self.input_dir.get(), self.output_dir.get())
    def extract_number(self, filename):
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else float('inf')

    def rename_files(self, input_path, output_dir):
        try:
            input_files = sorted(
                [f for f in os.listdir(input_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
                key=self.extract_number
            )
                
            # Filter and sort output files that are PNG or JPG
            output_files = sorted(
                [f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
                key=self.extract_number
            )

            # Check if the number of files matches
            if len(input_files) != len(output_files):
                print("Error: The number of images in the input and output folders does not match.")
                messagebox.showerror("Error", "The number of images in the input and output folders does not match.")
                return
            else:
                for input_file, output_file in zip(input_files, output_files):
                    input_full_path = os.path.join(input_path, input_file)
                    output_full_path = os.path.join(output_dir, output_file)
                    new_output_path = os.path.join(output_dir, input_file)
                    os.rename(output_full_path, new_output_path)
                
            messagebox.showinfo("Success", "Files have been renamed successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename: {str(e)}")
    def optimize_images_dialog(self):
        self.optimize_images(self.input_dir.get(), self.output_dir.get())
        
    def optimize_images(self, input_dir, output_dir):
        for file in os.listdir(input_dir):
            if file.lower().endswith(".png"):
                img = Image.open(os.path.join(input_dir, file))
                img.save(os.path.join(output_dir, file), optimize=True)
        messagebox.showinfo("Success", "Images optimized successfully.")

    def resize_video_dialog(self):
        try:
            width = int(self.resize_width_entry.get())
            height = int(self.resize_height_entry.get())
            if width > 0 and height > 0:
                self.resize_video(self.input_dir.get(), self.output_dir.get(), width, height)
            else:
                messagebox.showerror("Error", "Width and height must be positive integers.")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integer values for width and height.")

    def resize_video(self, input_path, output_dir, width, height):
        if not os.path.isfile(input_path):
            messagebox.showerror("Error", "The specified input path does not point to a file.")
            return

        if not os.path.exists(output_dir):
            messagebox.showerror("Error", "The specified output directory does not exist.")
            return
        
        try:
            # Ensure the output directory ends with a slash
            output_dir = os.path.join(output_dir, '')
            output_path = os.path.join(output_dir, "resized_video.mp4")

            clip = VideoFileClip(input_path)
            resized_clip = clip.resize(newsize=(width, height))
            resized_clip.write_videofile(output_path)
            resized_clip.close()

            messagebox.showinfo("Success", f"Video resized and saved to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to resize video: {str(e)}")

    def merge_videos_in_folder(self):
        input_path = self.input_dir.get()
        output_path = self.output_dir.get()
        fps_string_input = self.fps.get()
        fps_input = int(fps_string_input)
        # Ensure output directory exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # Gather all mp4 files in the input directory
        video_files = [os.path.join(input_path, f) for f in sorted(os.listdir(input_path)) if f.lower().endswith(".mp4")]

        # Load all videos into MoviePy VideoFileClip objects
        clips = [VideoFileClip(f) for f in video_files]

        # Concatenate all video clips
        final_clip = concatenate_videoclips(clips)

        # Define the output file path
        output_file = os.path.join(output_path, "merged_video.mp4")

        # Write the concatenated clip to the output file
        final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac", fps= fps_input)

        # Close all clips to free up resources
        for clip in clips:
            clip.close()
        final_clip.close()

        messagebox.showinfo("Success", f"Videos merged and saved to {output_path}")

    def split_video_frames(self, input_path, output_dir):
        # Ensure output directory exists
        input_path = self.input_dir.get()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        clip = VideoFileClip(input_path)
        frame_index = 1  # Start naming frames from 1

        for current_frame in clip.iter_frames():
            
            file_name = f"{frame_index:06d}"

            # Construct the full path for the image
            image_path = os.path.join(output_dir, f"{file_name}.png")

            # Save the current frame as an image
            imageio.imwrite(image_path, current_frame)

            frame_index += 1

        messagebox.showinfo("Success", "Video frames split successfully.")
            
    def print_hierarchy(self, directory, output_text):
        try:
            structure = self.directory_to_dict(directory)
            struc_json_string = json.dumps(structure, indent=4)
            output_text.delete(1.0, 'end')
            output_text.insert('end', struc_json_string)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    @staticmethod
    def directory_to_dict(path):
        name = os.path.basename(path)
        if os.path.isdir(path):
            return {name: [MediaToolkitApp.directory_to_dict(os.path.join(path, name)) for name in os.listdir(path)]}
        else:
            return name

    @staticmethod
    def extract_numbers(s):
        return tuple(int(num) for num in re.findall(r'\d+', s))


    def resize_images_dialog(self):
        width = simpledialog.askinteger("Input", "Width:", parent=self)
        height = simpledialog.askinteger("Input", "Height:", parent=self)
        crop = simpledialog.askstring("Input", "Crop (True/False):", parent=self)
        if width and height:
            if crop.lower() == "true":
                offset_Y = simpledialog.askstring("Input", "offset_Y:", parent=self)
                offset_Y = int(offset_Y)
                if offset_Y != 0:
                    self.resize_images(self.input_dir.get(), self.output_dir.get(), (width, height), crop=True, offset_Y=offset_Y)
                else:
                    self.resize_images(self.input_dir.get(), self.output_dir.get(), (width, height), crop=True)
            else:
                self.resize_images(self.input_dir.get(), self.output_dir.get(), (width, height))
    def flip_images_dialog(self):
        X_axis = simpledialog.askstring("Input", "X_axis:", parent=self)
        if X_axis.lower() == "true" or X_axis.lower() == "false":
            self.flip_images(self.input_dir.get(), self.output_dir.get(), X_axis)
    def create_video_from_images_dialog(self):
        # Directly use self.input_dir and self.output_dir without additional dialogues
        if self.input_dir.get() and self.output_dir.get():
            self.create_video_from_images(self.input_dir.get(), self.output_dir.get(),self.fps.get())
        else:
            messagebox.showerror("Error", "Input or output directory not specified.")

    def resize_images(self, input_dir, output_dir, size, crop=False, offset_Y=0):
        for file in os.listdir(input_dir):
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(os.path.join(input_dir, file))

                if crop:
                    width, height = img.size
                    new_width, new_height = size
                    
                    left = (width - new_width)/2
                    top = (height - new_height)/2
                    right = (width + new_width)/2
                    bottom = (height + new_height)/2
                    if offset_Y != 0:
                        top = top - offset_Y
                        bottom = bottom - offset_Y
                    # Crop the center of the image
                    img = img.crop((left, top, right, bottom))
                else:
                    img = img.resize(size, Image.Resampling.LANCZOS)
                img.save(os.path.join(output_dir, file))
        messagebox.showinfo("Success", "Images resized successfully.")

    def flip_images(self, input_dir, output_dir, X_axis):
        if X_axis.lower() == "true":
            X = True
        else:
            X = False
        for file in os.listdir(input_dir):
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(os.path.join(input_dir, file))
                if X==True:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                else:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                img.save(os.path.join(output_dir, "flipped_" + file))
        messagebox.showinfo("Success", "Images flipped successfully.")

    def create_video_from_images(self, input_dir, output_dir, FPS):
        # Make sure directories are not empty
        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Input or output directory is empty.")
            return
        
        frame_rate = float(FPS)
        print(frame_rate)
        try:
            image_files = [os.path.join(input_dir, f) for f in sorted(os.listdir(input_dir), key=self.extract_numbers) if f.lower().endswith(".png")]
            if not image_files:
                messagebox.showerror("Error", "No PNG files found.")
                return
            clip = ImageSequenceClip(image_files, fps=frame_rate)
            output_file = os.path.join(output_dir, "output_video.mp4")
            clip.write_videofile(output_file)
            clip.close()
            messagebox.showinfo("Success", f"Video created and saved to {output_file}")
        except FileNotFoundError as e:
            messagebox.showerror("File Not Found Error", str(e))

    def update_entry_with_directory(self, entry_field):
        directory = filedialog.askdirectory()
        if directory:  # Only update if a directory was selected
            entry_field.delete(0, tk.END)
            entry_field.insert(0, directory)


# Run the application
if __name__ == "__main__":
    app = MediaToolkitApp()
    app.mainloop()
