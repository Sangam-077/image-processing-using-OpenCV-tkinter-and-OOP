"""
alterations.py
--------------
Abstract base class ImageAlterer and emoji-like sticker alteration strategies.

Demonstrates:
    - Inheritance   : all subclasses extend ImageAlterer
    - Polymorphism  : GameEngine calls alterer.apply() without knowing the subclass
    - Encapsulation : each subclass owns its own drawing parameters
"""

from __future__ import annotations

import abc
import random
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from game_engine import DifferenceRegion


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------

class ImageAlterer(abc.ABC):
    """
    Abstract base for all image-alteration strategies.

    Subclasses must implement:
        apply(image, region) -> None   — modify *image* in-place inside *region*
        name -> str                    — human-readable label
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Return a human-readable label for this alteration type."""

    @abc.abstractmethod
    def apply(self, image: np.ndarray, region: "DifferenceRegion") -> None:
        """
        Modify *image* in-place within the bounding box described by *region*.

        Parameters
        ----------
        image  : np.ndarray
            The full image (BGR, uint8) to be modified.
        region : DifferenceRegion
            Bounding box and metadata for the target area.
        """


# ---------------------------------------------------------------------------
# Concrete Alteration 1 — Colour Shift
# ---------------------------------------------------------------------------

def _random_bright_bgr() -> tuple[int, int, int]:
    """Return a vibrant random BGR colour suitable for sticker fills."""
    return (
        random.randint(40, 255),
        random.randint(40, 255),
        random.randint(40, 255),
    )


def _draw_shadow(roi: np.ndarray, center: tuple[int, int], radius: int) -> None:
    """Add a soft shadow so stickers stand out on busy backgrounds."""
    shadow = roi.copy()
    cv2.circle(shadow, center, radius, (20, 20, 20), -1, lineType=cv2.LINE_AA)
    cv2.addWeighted(shadow, 0.30, roi, 0.70, 0, dst=roi)


class StarStickerAlterer(ImageAlterer):
    """Draw a colorful star sticker inside the target region."""

    @property
    def name(self) -> str:
        return "star"

    def apply(self, image: np.ndarray, region: "DifferenceRegion") -> None:
        x, y, w, h = region.x, region.y, region.w, region.h
        roi = image[y : y + h, x : x + w]

        cx, cy = w // 2, h // 2
        outer = max(12, min(w, h) // 2 - 8)
        inner = max(6, int(outer * 0.45))

        _draw_shadow(roi, (cx + 2, cy + 2), outer + 2)

        points: list[list[int]] = []
        for i in range(10):
            angle = -np.pi / 2 + i * (np.pi / 5)
            radius = outer if i % 2 == 0 else inner
            px = int(cx + np.cos(angle) * radius)
            py = int(cy + np.sin(angle) * radius)
            points.append([px, py])

        pts = np.array(points, dtype=np.int32)
        fill = _random_bright_bgr()
        cv2.fillPoly(roi, [pts], fill, lineType=cv2.LINE_AA)
        cv2.polylines(roi, [pts], True, (255, 255, 255), 2, lineType=cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Concrete Alteration 2 — Gaussian Blur
# ---------------------------------------------------------------------------

class DuckStickerAlterer(ImageAlterer):
    """Draw a simple duck-like sticker shape in the target region."""

    @property
    def name(self) -> str:
        return "duck"

    def apply(self, image: np.ndarray, region: "DifferenceRegion") -> None:
        x, y, w, h = region.x, region.y, region.w, region.h
        roi = image[y : y + h, x : x + w]

        cx, cy = w // 2, h // 2
        body_axes = (max(14, int(w * 0.30)), max(10, int(h * 0.22)))
        head_r = max(8, min(w, h) // 7)
        body_color = (60, 220, 255)  # yellow-ish in BGR

        _draw_shadow(roi, (cx + 2, cy + 2), max(body_axes) + 6)

        # Body
        cv2.ellipse(
            roi,
            (cx - 4, cy + 4),
            body_axes,
            0,
            0,
            360,
            body_color,
            -1,
            lineType=cv2.LINE_AA,
        )
        # Head
        head_center = (cx + body_axes[0] - 2, cy - body_axes[1] + 2)
        cv2.circle(roi, head_center, head_r, body_color, -1, lineType=cv2.LINE_AA)

        # Beak
        beak = np.array(
            [
                [head_center[0] + head_r - 2, head_center[1] - 2],
                [head_center[0] + head_r + 10, head_center[1] + 2],
                [head_center[0] + head_r - 2, head_center[1] + 6],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(roi, [beak], (0, 140, 255), lineType=cv2.LINE_AA)

        # Eye
        cv2.circle(roi, (head_center[0] + 1, head_center[1] - 2), 2, (0, 0, 0), -1)


# ---------------------------------------------------------------------------
# Concrete Alteration 3 — Brightness / Contrast
# ---------------------------------------------------------------------------

class SmileyStickerAlterer(ImageAlterer):
    """Draw a smiley-face sticker in the target region."""

    @property
    def name(self) -> str:
        return "smiley"

    def apply(self, image: np.ndarray, region: "DifferenceRegion") -> None:
        x, y, w, h = region.x, region.y, region.w, region.h
        roi = image[y : y + h, x : x + w]

        cx, cy = w // 2, h // 2
        r = max(14, min(w, h) // 2 - 8)

        _draw_shadow(roi, (cx + 2, cy + 2), r + 2)

        cv2.circle(roi, (cx, cy), r, (50, 220, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(roi, (cx, cy), r, (255, 255, 255), 2, lineType=cv2.LINE_AA)

        eye_r = max(2, r // 8)
        eye_y = cy - r // 3
        cv2.circle(roi, (cx - r // 3, eye_y), eye_r, (0, 0, 0), -1)
        cv2.circle(roi, (cx + r // 3, eye_y), eye_r, (0, 0, 0), -1)

        cv2.ellipse(
            roi,
            (cx, cy + r // 6),
            (max(5, r // 2), max(4, r // 3)),
            0,
            15,
            165,
            (0, 0, 0),
            2,
            lineType=cv2.LINE_AA,
        )


class HeartStickerAlterer(ImageAlterer):
    """Draw a heart sticker in the target region."""

    @property
    def name(self) -> str:
        return "heart"

    def apply(self, image: np.ndarray, region: "DifferenceRegion") -> None:
        x, y, w, h = region.x, region.y, region.w, region.h
        roi = image[y : y + h, x : x + w]

        cx, cy = w // 2, h // 2
        size = max(14, min(w, h) // 3)

        _draw_shadow(roi, (cx + 2, cy + 2), size + 8)

        left = (cx - size // 2, cy - size // 4)
        right = (cx + size // 2, cy - size // 4)
        bottom = (cx, cy + size)

        cv2.circle(roi, left, size // 2, (80, 40, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(roi, right, size // 2, (80, 40, 255), -1, lineType=cv2.LINE_AA)

        tri = np.array(
            [
                [cx - size, cy],
                [cx + size, cy],
                [bottom[0], bottom[1]],
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(roi, [tri], (80, 40, 255), lineType=cv2.LINE_AA)
        cv2.polylines(roi, [tri], True, (255, 255, 255), 2, lineType=cv2.LINE_AA)
