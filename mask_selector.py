import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk


class ImageWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Viewer with Click Event and Masking")

        # Select and load an image
        self.filepath = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )

        if not self.filepath:
            print("No file selected.")
            self.root.destroy()
            return

        self.image = Image.open(self.filepath)
        self.photo = ImageTk.PhotoImage(self.image)

        # Configure the window size to match the image
        self.root.geometry(f"{self.image.width}x{self.image.height + 50}")

        # Create a canvas to display the image
        self.canvas = tk.Canvas(self.root, width=self.image.width, height=self.image.height)
        self.canvas.pack()

        # Display the image on the canvas
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # Bind the mouse click event to the canvas
        self.canvas.bind("<Button-1>", self.add_star)

        # Add a button below the canvas
        self.button = tk.Button(self.root, text="Mask this element", command=self.mask_element)
        self.button.pack(pady=10)

        # Variable to store the currently selected star
        self.current_star_id = None
        self.current_star_coords = None

    def add_star(self, event):
        x, y = event.x, event.y
        print(f"Clicked at coordinates: ({x}, {y})")

        # Remove the existing star if present
        if self.current_star_id:
            self.canvas.delete(self.current_star_id)

        # Draw a new star and store its ID and coordinates
        self.current_star_id = self.draw_star(x, y)
        self.current_star_coords = (x, y)

    def draw_star(self, x, y, size=10):
        points = [
            x, y - size,  # Top
               x + size * 0.4, y - size * 0.3,  # Top-right
               x + size, y,  # Right
               x + size * 0.4, y + size * 0.3,  # Bottom-right
            x, y + size,  # Bottom
               x - size * 0.4, y + size * 0.3,  # Bottom-left
               x - size, y,  # Left
               x - size * 0.4, y - size * 0.3,  # Top-left
        ]
        return self.canvas.create_polygon(points, fill="yellow", outline="black")

    def mask_element(self):
        if not self.current_star_coords:
            print("No star selected for masking.")
            return
        print(f"Masking element at: {self.current_star_coords}")
        # Add actual masking logic here


# Create the tkinter application
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageWindow(root)
    root.mainloop()
