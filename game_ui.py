"""
game_ui.py
----------
Tkinter GUI layer for the Spot-the-Difference game.

Responsibilities:
  - Render the original and modified images side by side on two canvases
  - Handle all user interaction (button clicks, canvas clicks)
  - Delegate all game logic to GameEngine (no logic lives here)
  - Translate between canvas coordinates and original image coordinates
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

from game_engine import GameEngine, DifferenceRegion


# ---------------------------------------------------------------------------
# Colour palette (centralised for easy theming)
# ---------------------------------------------------------------------------

PALETTE = {
    "bg":           "#1a1a2e",   # deep navy background
    "panel":        "#16213e",   # slightly lighter panel
    "accent":       "#e94560",   # vivid red-pink accent
    "accent2":      "#0f3460",   # muted blue accent
    "text":         "#eaeaea",   # near-white text
    "text_dim":     "#7a8ca0",   # dimmed secondary text
    "success":      "#4caf50",   # green for found
    "warning":      "#ff9800",   # orange for mistakes
    "danger":       "#e94560",   # red for lockout
    "circle_found": (0, 0, 220), # BGR — red circles (found)
    "circle_reveal":(220, 80, 0),# BGR — blue circles (revealed)
}

# Maximum canvas dimensions (the image is scaled to fit within this box)
CANVAS_W: int = 580
CANVAS_H: int = 480


# ---------------------------------------------------------------------------
# GameUI
# ---------------------------------------------------------------------------

class GameUI:
    """
    Main application window.  Owns the Tkinter root and delegates all
    game-state decisions to a GameEngine instance.

    Layout
    ------
    ┌─────────────────────────────────────────────────────┐
    │  Title bar                                          │
    ├────────────────────────┬────────────────────────────┤
    │   Original canvas      │   Modified canvas          │
    │   (left – read-only)   │   (right – clickable)      │
    ├────────────────────────┴────────────────────────────┤
    │  Status bar: score · remaining · mistakes           │
    ├─────────────────────────────────────────────────────┤
    │  [Load Image]   [Reveal Differences]                │
    └─────────────────────────────────────────────────────┘
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._engine = GameEngine()

        # PhotoImage references must be kept alive (prevents GC)
        self._photo_original: ImageTk.PhotoImage | None = None
        self._photo_modified: ImageTk.PhotoImage | None = None

        # Scale factor: canvas_pixels / original_pixels
        self._scale: float = 1.0
        
        # Displayed image dimensions (used for click coordinate conversion)
        self._display_width: int = 0
        self._display_height: int = 0

        self._build_window()
        self._build_menu_bar()
        self._build_title()
        self._build_canvases()
        self._build_status_bar()
        self._build_controls()

    # ------------------------------------------------------------------
    # Window construction helpers
    # ------------------------------------------------------------------

    def _build_window(self) -> None:
        self._root.title("Spot the Difference")
        self._root.configure(bg=PALETTE["bg"])
        self._root.resizable(True, True)
        self._root.minsize(900, 600)

    def _build_menu_bar(self) -> None:
        menu = tk.Menu(self._root, bg=PALETTE["panel"], fg=PALETTE["text"],
                       activebackground=PALETTE["accent2"],
                       activeforeground=PALETTE["text"])
        file_menu = tk.Menu(menu, tearoff=0,
                            bg=PALETTE["panel"], fg=PALETTE["text"],
                            activebackground=PALETTE["accent2"],
                            activeforeground=PALETTE["text"])
        file_menu.add_command(label="Load Image", command=self._on_load_image)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._root.quit)
        menu.add_cascade(label="File", menu=file_menu)
        self._root.config(menu=menu)

    def _build_title(self) -> None:
        title_frame = tk.Frame(self._root, bg=PALETTE["bg"], pady=12)
        title_frame.pack(fill=tk.X)

        tk.Label(
            title_frame,
            text="SPOT THE DIFFERENCE",
            font=("Courier New", 22, "bold"),
            bg=PALETTE["bg"],
            fg=PALETTE["accent"],
        ).pack()

        tk.Label(
            title_frame,
            text="Find all 5 differences hidden in the right image",
            font=("Courier New", 10),
            bg=PALETTE["bg"],
            fg=PALETTE["text_dim"],
        ).pack()

    def _build_canvases(self) -> None:
        canvas_frame = tk.Frame(self._root, bg=PALETTE["bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        # ── Left panel (original) ──────────────────────────────────────
        left_wrap = tk.Frame(canvas_frame, bg=PALETTE["panel"],
                             bd=1, relief=tk.FLAT)
        left_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        tk.Label(left_wrap, text="ORIGINAL",
                 font=("Courier New", 9, "bold"),
                 bg=PALETTE["panel"], fg=PALETTE["text_dim"]).pack(pady=(6, 2))

        self._canvas_original = tk.Canvas(
            left_wrap,
            width=CANVAS_W, height=CANVAS_H,
            bg="#0d0d1a", highlightthickness=0,
            cursor="crosshair",
        )
        self._canvas_original.pack(padx=8, pady=(0, 8))

        # ── Right panel (modified – clickable) ────────────────────────
        right_wrap = tk.Frame(canvas_frame, bg=PALETTE["panel"],
                              bd=1, relief=tk.FLAT)
        right_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        tk.Label(right_wrap, text="FIND DIFFERENCES HERE",
                 font=("Courier New", 9, "bold"),
                 bg=PALETTE["panel"], fg=PALETTE["accent"]).pack(pady=(6, 2))

        self._canvas_modified = tk.Canvas(
            right_wrap,
            width=CANVAS_W, height=CANVAS_H,
            bg="#0d0d1a", highlightthickness=0,
            cursor="crosshair",
        )
        self._canvas_modified.pack(padx=8, pady=(0, 8))
        self._canvas_modified.bind("<Button-1>", self._on_canvas_click)

        # Placeholder text until an image is loaded
        for canvas, label in [
            (self._canvas_original, "Load an image to begin"),
            (self._canvas_modified, "← Load an image first"),
        ]:
            canvas.create_text(
                CANVAS_W // 2, CANVAS_H // 2,
                text=label,
                fill=PALETTE["text_dim"],
                font=("Courier New", 13),
                tags="placeholder",
            )

    def _build_status_bar(self) -> None:
        status_frame = tk.Frame(self._root, bg=PALETTE["accent2"], pady=8)
        status_frame.pack(fill=tk.X, padx=16)

        # Three status labels — score, remaining, mistakes
        self._var_found     = tk.StringVar(value="Found: 0")
        self._var_remaining = tk.StringVar(value="Remaining: —")
        self._var_mistakes  = tk.StringVar(value="Mistakes: 0 / 3")
        self._var_message   = tk.StringVar(value="Load an image to start playing")

        label_cfg = dict(bg=PALETTE["accent2"], font=("Courier New", 11, "bold"))

        tk.Label(status_frame, textvariable=self._var_found,
                 fg=PALETTE["success"], **label_cfg).pack(side=tk.LEFT, padx=20)
        tk.Label(status_frame, textvariable=self._var_remaining,
                 fg=PALETTE["text"], **label_cfg).pack(side=tk.LEFT, padx=20)
        tk.Label(status_frame, textvariable=self._var_mistakes,
                 fg=PALETTE["warning"], **label_cfg).pack(side=tk.LEFT, padx=20)
        tk.Label(status_frame, textvariable=self._var_message,
                 fg=PALETTE["accent"], **label_cfg).pack(side=tk.RIGHT, padx=20)

    def _build_controls(self) -> None:
        btn_frame = tk.Frame(self._root, bg=PALETTE["bg"], pady=12)
        btn_frame.pack()

        btn_cfg = dict(
            font=("Courier New", 11, "bold"),
            relief=tk.FLAT,
            padx=24, pady=8,
            cursor="hand2",
        )

        self._btn_load = tk.Button(
            btn_frame,
            text="⬆  LOAD IMAGE",
            bg=PALETTE["accent"], fg=PALETTE["text"],
            activebackground="#c73652", activeforeground=PALETTE["text"],
            command=self._on_load_image,
            **btn_cfg,
        )
        self._btn_load.pack(side=tk.LEFT, padx=12)

        self._btn_reveal = tk.Button(
            btn_frame,
            text="👁  REVEAL DIFFERENCES",
            bg=PALETTE["accent2"], fg=PALETTE["text"],
            activebackground="#1a4a8a", activeforeground=PALETTE["text"],
            command=self._on_reveal,
            state=tk.DISABLED,
            **btn_cfg,
        )
        self._btn_reveal.pack(side=tk.LEFT, padx=12)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_load_image(self) -> None:
        """Open a file dialog and load the chosen image into the engine."""
        path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            self._engine.load_image(path)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        self._btn_reveal.config(state=tk.NORMAL)
        self._render_images()
        self._update_status("Image loaded — find the 5 differences!")

    def _on_canvas_click(self, event: tk.Event) -> None:
        """Handle a click on the modified (right) canvas."""
        if self._engine.original_image is None:
            return

        # Convert canvas coordinates → original image coordinates
        # The image is CENTERED on the canvas, so we need to account for that offset
        canvas_center_x = CANVAS_W // 2
        canvas_center_y = CANVAS_H // 2
        
        # Offset from canvas top-left to image top-left
        offset_x = canvas_center_x - self._display_width // 2
        offset_y = canvas_center_y - self._display_height // 2
        
        # Convert: canvas coords → displayed image coords → original image coords
        display_x = event.x - offset_x
        display_y = event.y - offset_y
        
        img_x = int(display_x / self._scale)
        img_y = int(display_y / self._scale)

        result = self._engine.check_click(img_x, img_y)

        if result == "hit":
            # Find the region that was just found and draw circles
            for region in self._engine.differences:
                if region.found:
                    self._draw_circle_on_both(region, PALETTE["circle_found"])
            self._redraw_images()
            if self._engine.is_complete():
                self._update_status("🎉 All differences found!")
                self._show_completion()
            else:
                self._update_status(f"✓ Found one! {self._engine.remaining} remaining.")

        elif result == "mistake":
            self._update_status(
                f"✗ Wrong! Mistakes: {self._engine.mistakes} / {self._engine.MAX_MISTAKES}"
            )
            if self._engine.is_locked:
                self._update_status(
                    f"🔒 Too many mistakes! {self._engine.remaining} differences unfound. "
                    "Load a new image to try again."
                )
                messagebox.showwarning(
                    "Round Over",
                    f"You made {self._engine.MAX_MISTAKES} mistakes.\n"
                    f"{self._engine.remaining} difference(s) were not found.\n\n"
                    "Load a new image to continue.",
                )

        elif result == "already":
            self._update_status("Already found that one — keep looking!")

        self._refresh_stats()

    def _on_reveal(self) -> None:
        """Reveal all unfound differences with blue circles."""
        if self._engine.original_image is None:
            return

        revealed = self._engine.reveal_all()
        for region in revealed:
            self._draw_circle_on_both(region, PALETTE["circle_reveal"])

        self._redraw_images()
        self._refresh_stats()
        self._update_status(
            f"Revealed {len(revealed)} unfound difference(s). Load a new image to play again."
        )

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_images(self) -> None:
        """
        Convert OpenCV BGR images → Tkinter PhotoImages and display them.
        Calculates a uniform scale factor so both images fit the canvas.
        """
        orig = self._engine.original_image
        mod  = self._engine.modified_image
        if orig is None or mod is None:
            return

        img_h, img_w = orig.shape[:2]
        scale_x = CANVAS_W / img_w
        scale_y = CANVAS_H / img_h
        self._scale = min(scale_x, scale_y, 1.0)  # never upscale

        new_w = int(img_w * self._scale)
        new_h = int(img_h * self._scale)
        
        # Store display dimensions for click coordinate conversion
        self._display_width = new_w
        self._display_height = new_h

        def _to_photo(bgr: np.ndarray) -> ImageTk.PhotoImage:
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb).resize((new_w, new_h), Image.LANCZOS)
            return ImageTk.PhotoImage(pil)

        self._photo_original = _to_photo(orig)
        self._photo_modified = _to_photo(mod)

        self._put_image(self._canvas_original, self._photo_original, new_w, new_h)
        self._put_image(self._canvas_modified, self._photo_modified, new_w, new_h)

    def _put_image(self, canvas: tk.Canvas,
                   photo: ImageTk.PhotoImage,
                   w: int, h: int) -> None:
        """Clear a canvas, remove placeholder text, and draw an image centred."""
        canvas.delete("all")
        cx = CANVAS_W // 2
        cy = CANVAS_H // 2
        canvas.create_image(cx, cy, anchor=tk.CENTER, image=photo, tags="img")

    def _redraw_images(self) -> None:
        """Re-render images after circles have been drawn onto the numpy arrays."""
        self._render_images()

    def _draw_circle_on_both(self, region: DifferenceRegion,
                              colour_bgr: tuple[int, int, int]) -> None:
        """
        Draw a circle directly onto both numpy image arrays (original and
        modified) at the region's centre. The circle is sized to enclose
        the bounding box.
        """
        orig = self._engine.original_image
        mod  = self._engine.modified_image
        if orig is None or mod is None:
            return

        cx, cy = region.centre()
        radius = max(region.w, region.h) // 2 + 10
        thickness = 3

        for img in (orig, mod):
            cv2.circle(img, (cx, cy), radius, colour_bgr, thickness)

    # ------------------------------------------------------------------
    # Status / stats helpers
    # ------------------------------------------------------------------

    def _refresh_stats(self) -> None:
        """Update all three status-bar counters from current engine state."""
        self._var_found.set(f"Found: {self._engine.total_found}")
        self._var_remaining.set(f"Remaining: {self._engine.remaining}")
        mistake_color = PALETTE["danger"] if self._engine.is_locked else PALETTE["warning"]
        self._var_mistakes.set(
            f"Mistakes: {self._engine.mistakes} / {self._engine.MAX_MISTAKES}"
        )

    def _update_status(self, message: str) -> None:
        """Set the right-hand status message in the status bar."""
        self._var_message.set(message)

    def _show_completion(self) -> None:
        """Pop up a congratulations dialog."""
        messagebox.showinfo(
            "Congratulations! 🎉",
            f"You found all {self._engine.NUM_DIFFERENCES} differences!\n\n"
            f"Total found so far: {self._engine.total_found}\n\n"
            "Load a new image to keep playing.",
        )
