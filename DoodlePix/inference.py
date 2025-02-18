from PIL import Image, ImageOps
import numpy as np
from types import SimpleNamespace

class InferenceHandler:
    def __init__(self):
        self.pipeline = None
        self.device = None
        self.schedulers = None
        self._setup_done = False
        
    def _lazy_setup(self):
        """Lazy load ML dependencies only when needed"""
        if self._setup_done:
            return
            
        import torch
        from diffusers import (
            StableDiffusionInstructPix2PixPipeline,
            DDIMScheduler,
            DDPMScheduler,
            PNDMScheduler,
            EulerAncestralDiscreteScheduler,
            DPMSolverMultistepScheduler
        )
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.schedulers = {
            "DDIM": DDIMScheduler,
            "DDPM": DDPMScheduler,
            "PNDM": PNDMScheduler,
            "Euler Ancestral": EulerAncestralDiscreteScheduler,
            "DPM++ 2M": DPMSolverMultistepScheduler
        }
        
        self._torch = torch
        self._pipeline_class = StableDiffusionInstructPix2PixPipeline
        self._setup_done = True
        
    def get_scheduler_names(self):
        """Get list of available schedulers without loading ML stuff"""
        return ["DDIM", "DDPM", "PNDM", "Euler Ancestral", "DPM++ 2M"]
        
    def load_model(self, model_path, scheduler_name="DDIM"):
        """Load the model from path"""
        try:
            self._lazy_setup()
            
            scheduler_class = self.schedulers.get(scheduler_name)
            scheduler = scheduler_class.from_pretrained(model_path, subfolder="scheduler")
            
            self.pipeline = self._pipeline_class.from_pretrained(
                model_path,
                torch_dtype=self._torch.float16,
                safety_checker=None,
                scheduler=scheduler
            ).to(self.device)
            
            # Enable optimizations
            self.pipeline.enable_model_cpu_offload()
            self.pipeline.enable_attention_slicing()
            if hasattr(self.pipeline, "enable_xformers_memory_efficient_attention"):
                self.pipeline.enable_xformers_memory_efficient_attention()
                
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
            
    def change_scheduler(self, scheduler_name):
        """Change scheduler if pipeline is loaded"""
        if self.pipeline and self._setup_done:
            scheduler_class = self.schedulers.get(scheduler_name)
            self.pipeline.scheduler = scheduler_class.from_config(
                self.pipeline.scheduler.config
            )
            
    def generate_image(self, drawing, props):
        """Generate image from drawing"""
        if not self.pipeline:
            raise ValueError("Pipeline not loaded! Please load a model first.")
            
        # Convert drawing to PIL Image if needed
        if not isinstance(drawing, Image.Image):
            drawing = Image.fromarray(np.array(drawing))
            
        # Ensure image is in RGB mode
        if drawing.mode != 'RGB':
            drawing = drawing.convert('RGB')
            
        # Process drawing (ensure white lines on black background)
        processed_image = ImageOps.invert(drawing)
        
        # Ensure image is the correct size
        if processed_image.size != (512, 512):
            processed_image = processed_image.resize((512, 512))
        
        # Generate image
        with self._torch.no_grad():
            output = self.pipeline(
                prompt=props.prompt,
                negative_prompt=props.negative_prompt,
                image=processed_image,
                num_inference_steps=props.num_inference_steps,
                guidance_scale=props.guidance_scale,
                image_guidance_scale=props.image_guidance_scale,
                generator=self._torch.manual_seed(props.seed) if props.seed else None
            ).images[0]
            
        return output