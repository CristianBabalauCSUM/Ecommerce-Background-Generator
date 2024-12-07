import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import torch
from diffusers import AutoPipelineForInpainting
from diffusers.utils import load_image, make_image_grid
import os
from PIL import Image
import gc
import random

class InpaintingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Inpainting Generator")
        self.root.geometry("800x600")

        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Image selection
        ttk.Label(main_frame, text="Original Image:").grid(row=0, column=0, sticky=tk.W)
        self.original_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.original_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=lambda: self.browse_file('original')).grid(row=0, column=2)

        ttk.Label(main_frame, text="Mask Image:").grid(row=1, column=0, sticky=tk.W)
        self.mask_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.mask_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=lambda: self.browse_file('mask')).grid(row=1, column=2)

        # Seed parameters
        seed_frame = ttk.LabelFrame(main_frame, text="Seed Configuration", padding="5")
        seed_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(seed_frame, text="Random Seeds Count:").grid(row=0, column=0, sticky=tk.W)
        self.random_seeds = tk.StringVar(value="5")
        ttk.Entry(seed_frame, textvariable=self.random_seeds, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(seed_frame, text="Specific Seed:").grid(row=1, column=0, sticky=tk.W)
        self.specific_seed = tk.StringVar(value="0")
        ttk.Entry(seed_frame, textvariable=self.specific_seed, width=10).grid(row=1, column=1, padx=5)

        # Prompts input
        ttk.Label(main_frame, text="Prompts (one per line):").grid(row=3, column=0, sticky=tk.W)
        self.prompts_text = scrolledtext.ScrolledText(main_frame, width=60, height=10)
        self.prompts_text.grid(row=4, column=0, columnspan=3, pady=5)
        self.prompts_text.insert(tk.END, "on a pristine white marble counter with soft natural lighting\na modern minimalist kitchen with stainless steel appliances")

        # Info text
        info_text = "For each seed, the application will generate one image per prompt provided.\nImages will be saved in: inpainted_pictures/[original_filename]/seed_[number]/"
        ttk.Label(main_frame, text=info_text, wraplength=700).grid(row=5, column=0, columnspan=3, pady=10)

        # Generate button
        ttk.Button(main_frame, text="Generate Images", command=self.generate_images).grid(row=6, column=0, columnspan=3, pady=10)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate')
        self.progress.grid(row=7, column=0, columnspan=3, pady=5)

        # Status label
        self.status_var = tk.StringVar()
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=8, column=0, columnspan=3)

    def save_prompts(self, prompts, path="prompts", filename="prompts.txt"):
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, filename)
        with open(filepath, 'w') as f:
            f.write('\n'.join(prompts))
        return filepath

    def browse_file(self, file_type):
        filename = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if filename:
            if file_type == 'original':
                self.original_path.set(filename)
            else:
                self.mask_path.set(filename)

    @staticmethod
    def resize_to_512(image):
        return image.resize((512, 512), Image.Resampling.LANCZOS)

    @staticmethod
    def resize_back(image, original_size):
        return image.resize(original_size, Image.Resampling.LANCZOS)

    def generate_images(self):
        try:
            original_path = self.original_path.get()
            mask_path = self.mask_path.get()
            prompts = self.prompts_text.get("1.0", tk.END).strip().split('\n')
            random_seeds_count = int(self.random_seeds.get())
            specific_seed = int(self.specific_seed.get())

            if not original_path or not mask_path:
                self.status_var.set("Please select both images")
                return

            original_filename = os.path.splitext(os.path.basename(original_path))[0]
            base_output_dir = os.path.join("inpainted_pictures", original_filename)
            os.makedirs(base_output_dir, exist_ok=True)

            self.status_var.set("Initializing pipeline...")
            pipeline = AutoPipelineForInpainting.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                safety_checker=None
            )
            pipeline.enable_sequential_cpu_offload()
            pipeline.enable_attention_slicing("max")

            saved_path = self.save_prompts(prompts=prompts, filename=original_filename)
            print(f"Prompts saved to: {saved_path}")

            init_image = load_image(original_path)
            mask_image = load_image(mask_path)
            original_init_size = init_image.size
            original_mask_size = mask_image.size

            # Resize images to 512x512
            init_image_resized = self.resize_to_512(init_image)
            mask_image_resized = self.resize_to_512(mask_image)
            blurred_mask = pipeline.mask_processor.blur(mask_image_resized, blur_factor=3)

            seeds = [specific_seed] if specific_seed > 0 else random.sample(range(1, 1000), random_seeds_count)
            total_operations = len(seeds) * len(prompts)
            completed = 0

            for seed in seeds:
                seed_dir = os.path.join(base_output_dir, f"seed_{seed}")
                os.makedirs(seed_dir, exist_ok=True)
                generator = torch.Generator("cpu").manual_seed(seed)
                generated_images = []

                for prompt_idx, prompt in enumerate(prompts):
                    self.status_var.set(f"Processing seed {seed}, prompt {prompt_idx + 1}/{len(prompts)}")

                    # Generate image at 512x512
                    image = pipeline(
                        prompt=prompt,
                        image=init_image_resized,
                        mask_image=blurred_mask,
                        generator=generator,
                        strength = 0.9
                    ).images[0]

                    # Resize generated image back to original size
                    image_original_size = self.resize_back(image, original_init_size)

                    # Apply mask overlay at original resolution
                    unmasked_unchanged_image = pipeline.image_processor.apply_overlay(
                        self.resize_back(mask_image_resized, original_mask_size),
                        init_image,
                        image_original_size
                    )

                    # Save images
                    unmasked_unchanged_image.save(os.path.join(seed_dir, f"prompt_{prompt_idx + 1}_seed_{seed}_unmasked.png"))
                    filename = f"prompt_{prompt_idx + 1}_seed_{seed}.png"
                    image_original_size.save(os.path.join(seed_dir, filename))
                    generated_images.append(image_original_size)

                    completed += 1
                    self.progress['value'] = (completed / total_operations) * 100
                    self.root.update_idletasks()

                if generated_images:
                    grid = make_image_grid(generated_images, rows=1, cols=len(generated_images))
                    grid.save(os.path.join(base_output_dir, f"seed_{seed}_grid.png"))

            self.status_var.set("Generation complete!")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
        finally:
            torch.cuda.empty_cache()
            gc.collect()

if __name__ == "__main__":
    root = tk.Tk()
    app = InpaintingApp(root)
    root.mainloop()