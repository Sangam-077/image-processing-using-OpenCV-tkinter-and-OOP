"""
debug_preview.py
----------------
Visual debugging tool: Load an image and display the original vs modified
side-by-side to preview the differences before playing.

Run with:
    python debug_preview.py
"""

import cv2
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np

from game_engine import GameEngine


def main():
    root = tk.Tk()
    root.title("Difference Preview Tool")
    root.geometry("1200x600")
    
    # Load button
    def load_image():
        filepath = filedialog.askopenfilename(
            title="Select an image to preview differences",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        )
        if not filepath:
            return
        
        # Initialize engine and load image
        engine = GameEngine()
        try:
            engine.load_image(filepath)
        except ValueError as e:
            print(f"Error: {e}")
            return
        
        # Display images side by side
        orig = engine.original_image
        mod = engine.modified_image
        
        # Resize for display
        max_h = 550
        scale = max_h / max(orig.shape[0], orig.shape[1])
        new_w = int(orig.shape[1] * scale)
        new_h = int(orig.shape[0] * scale)
        
        orig_resized = cv2.resize(orig, (new_w, new_h))
        mod_resized = cv2.resize(mod, (new_w, new_h))
        
        # Create combined view (side by side)
        combined = np.hstack([orig_resized, mod_resized])
        
        # Convert BGR to RGB for display
        combined_rgb = cv2.cvtColor(combined, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL
        pil_image = Image.fromarray(combined_rgb)
        photo = ImageTk.PhotoImage(pil_image)
        
        # Display
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        canvas.image = photo  # Keep a reference!
        
        # Print difference info
        print("\n" + "="*70)
        print("DIFFERENCE PREVIEW")
        print("="*70)
        print(f"Image size: {orig.shape[1]}x{orig.shape[0]}")
        print(f"Displayed size: {new_w}x{new_h}")
        print(f"\nFound {len(engine.differences)} differences:")
        for i, diff in enumerate(engine.differences, 1):
            print(f"  {i}. {diff.alteration_type.upper()}")
            print(f"     Location: x={diff.x}, y={diff.y}")
            print(f"     Size: {diff.w}x{diff.h}")
        print("="*70)
        print("\nLEFT = ORIGINAL | RIGHT = MODIFIED (with 5 differences)")
        print("Look carefully at the right image to spot the differences!")
        print("="*70 + "\n")
    
    # UI
    btn = tk.Button(root, text="Load Image to Preview Differences", command=load_image,
                    bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                    padx=20, pady=10)
    btn.pack(pady=10)
    
    label = tk.Label(root, text="LEFT: Original  |  RIGHT: Modified (with differences)",
                     font=("Arial", 10), fg="#666")
    label.pack()
    
    canvas = tk.Canvas(root, bg="#1a1a1a")
    canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    root.mainloop()


if __name__ == "__main__":
    main()
