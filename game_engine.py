"""
game_engine.py
--------------
Core game logic: DifferenceRegion data model and GameEngine state manager.
No GUI code lives here — pure logic only.
"""

import random
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# DifferenceRegion
# ---------------------------------------------------------------------------

class DifferenceRegion:
    """
    Represents a single hidden difference placed on the modified image.

    Attributes
    ----------
    x, y : int
        Top-left corner of the bounding box (in original image pixel coords).
    w, h : int
        Width and height of the bounding box.
    alteration_type : str
        Human-readable label for the alteration applied.
    found : bool
        Whether the player has successfully located this region.
    """

    # Minimum and maximum side length for a difference region (pixels)
    MIN_SIZE: int = 60
    MAX_SIZE: int = 130

    def __init__(self, x: int, y: int, w: int, h: int, alteration_type: str) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.alteration_type = alteration_type
        self.found: bool = False

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def centre(self) -> tuple[int, int]:
        """Return the centre pixel of this region."""
        return self.x + self.w // 2, self.y + self.h // 2

    def contains_point(self, px: int, py: int, tolerance: int = 20) -> bool:
        """
        Return True when the point (px, py) falls within the region,
        expanded outward by *tolerance* pixels on every side.
        """
        return (
            self.x - tolerance <= px <= self.x + self.w + tolerance
            and self.y - tolerance <= py <= self.y + self.h + tolerance
        )

    def overlaps(self, other: "DifferenceRegion", margin: int = 10) -> bool:
        """
        Return True when this region's bounding box (plus a safety margin)
        intersects with *other*'s bounding box.
        """
        return not (
            self.x + self.w + margin <= other.x
            or other.x + other.w + margin <= self.x
            or self.y + self.h + margin <= other.y
            or other.y + other.h + margin <= self.y
        )

    def __repr__(self) -> str:
        return (
            f"DifferenceRegion(x={self.x}, y={self.y}, w={self.w}, h={self.h}, "
            f"type={self.alteration_type!r}, found={self.found})"
        )


# ---------------------------------------------------------------------------
# GameEngine
# ---------------------------------------------------------------------------

class GameEngine:
    """
    Manages all game state: image loading, difference generation,
    click validation, scoring, and game-over conditions.

    The UI layer interacts exclusively through the public methods below;
    it never touches internal state directly (encapsulation).

    Constants
    ---------
    NUM_DIFFERENCES : int
        Number of differences placed per image (always 5).
    MAX_MISTAKES : int
        Maximum wrong clicks allowed before the round is locked.
    """

    NUM_DIFFERENCES: int = 5
    MAX_MISTAKES: int = 3

    def __init__(self) -> None:
        # Images stored as NumPy arrays (BGR, as returned by OpenCV)
        self._original_image: np.ndarray | None = None
        self._modified_image: np.ndarray | None = None

        self._differences: list[DifferenceRegion] = []

        # Per-round state
        self._mistakes: int = 0
        self._locked: bool = False

        # Cumulative across all rounds
        self._total_found: int = 0

        # Deferred import avoids circular dependency between modules
        from alterations import (
            StarStickerAlterer,
            DuckStickerAlterer,
            SmileyStickerAlterer,
            HeartStickerAlterer,
        )

        # Pool of alterer instances — polymorphism in action
        self._alterers = [
            StarStickerAlterer(),
            DuckStickerAlterer(),
            SmileyStickerAlterer(),
            HeartStickerAlterer(),
        ]

    # ------------------------------------------------------------------
    # Public properties (read-only views of internal state)
    # ------------------------------------------------------------------

    @property
    def original_image(self) -> np.ndarray | None:
        return self._original_image

    @property
    def modified_image(self) -> np.ndarray | None:
        return self._modified_image

    @property
    def differences(self) -> list[DifferenceRegion]:
        return list(self._differences)  # defensive copy

    @property
    def mistakes(self) -> int:
        return self._mistakes

    @property
    def total_found(self) -> int:
        return self._total_found

    @property
    def remaining(self) -> int:
        return sum(1 for d in self._differences if not d.found)

    @property
    def is_locked(self) -> bool:
        return self._locked

    # ------------------------------------------------------------------
    # Image loading
    # ------------------------------------------------------------------

    def load_image(self, path: str) -> None:
        """
        Load an image from *path*, clone it, inject 5 random differences
        into the clone, and reset all per-round state.

        Raises
        ------
        ValueError
            If the file cannot be read by OpenCV.
        """
        image = cv2.imread(path)
        if image is None:
            raise ValueError(f"Cannot read image: {path!r}")

        self._original_image = image
        self._modified_image = image.copy()
        self._differences = []
        self._mistakes = 0
        self._locked = False

        self._generate_differences()

    # ------------------------------------------------------------------
    # Difference generation (private)
    # ------------------------------------------------------------------

    def _generate_differences(self) -> None:
        """
        Place exactly NUM_DIFFERENCES non-overlapping DifferenceRegion
        objects on the modified image, applying a randomly chosen alterer
        to each.
        """
        if self._original_image is None:
            return

        img_h, img_w = self._original_image.shape[:2]
        # Start with the requested region size/margin, then relax constraints
        # if the image cannot fit all regions under current settings.
        border = 10
        margin = 10
        min_size = DifferenceRegion.MIN_SIZE
        max_size = DifferenceRegion.MAX_SIZE

        placed: list[DifferenceRegion] = []
        total_attempts = 0
        attempts_since_progress = 0
        max_total_attempts = 5000
        relax_after_attempts = 250

        while len(placed) < self.NUM_DIFFERENCES and total_attempts < max_total_attempts:
            total_attempts += 1
            attempts_since_progress += 1

            max_w = min(max_size, img_w - 2 * border)
            max_h = min(max_size, img_h - 2 * border)
            min_w = min(min_size, max_w)
            min_h = min(min_size, max_h)

            # If no valid box can be sampled, relax constraints immediately.
            if max_w < 20 or max_h < 20:
                min_size = max(20, min_size - 8)
                max_size = max(min_size, max_size - 8)
                border = max(2, border - 1)
                margin = max(0, margin - 2)
                attempts_since_progress = 0
                continue

            w = random.randint(min_w, max_w)
            h = random.randint(min_h, max_h)

            x_min = border
            y_min = border
            x_max = img_w - w - border
            y_max = img_h - h - border

            if x_max < x_min or y_max < y_min:
                continue

            x = random.randint(x_min, x_max)
            y = random.randint(y_min, y_max)

            alterer = random.choice(self._alterers)
            candidate = DifferenceRegion(x, y, w, h, alterer.name)

            if any(candidate.overlaps(existing, margin=margin) for existing in placed):
                if attempts_since_progress >= relax_after_attempts:
                    # Relax spacing and size constraints to ensure we can place all 5.
                    min_size = max(20, min_size - 6)
                    max_size = max(min_size, max_size - 6)
                    margin = max(0, margin - 1)
                    border = max(2, border - 1)
                    attempts_since_progress = 0
                continue

            # Apply alteration, but only keep it if the visual delta vs original
            # is strong enough to be reasonably findable.
            backup = self._modified_image[y : y + h, x : x + w].copy()
            alterer.apply(self._modified_image, candidate)

            if not self._is_region_visibly_changed(candidate):
                self._modified_image[y : y + h, x : x + w] = backup
                if attempts_since_progress >= relax_after_attempts:
                    min_size = max(20, min_size - 6)
                    max_size = max(min_size, max_size - 6)
                    margin = max(0, margin - 1)
                    border = max(2, border - 1)
                    attempts_since_progress = 0
                continue

            placed.append(candidate)
            attempts_since_progress = 0

        if len(placed) != self.NUM_DIFFERENCES:
            raise ValueError(
                "Could not place 5 non-overlapping differences on this image. "
                "Please choose a larger or less crowded image."
            )

        self._differences = placed

    def _is_region_visibly_changed(self, region: DifferenceRegion) -> bool:
        """
        Return True when the altered region differs enough from the original
        to be visually detectable by the player.
        """
        if self._original_image is None or self._modified_image is None:
            return False

        x, y, w, h = region.x, region.y, region.w, region.h
        original_roi = self._original_image[y : y + h, x : x + w]
        modified_roi = self._modified_image[y : y + h, x : x + w]

        diff = cv2.absdiff(original_roi, modified_roi)
        mean_delta = float(np.mean(diff))

        # Pixel counts as changed if any channel delta is noticeable.
        changed_mask = np.any(diff >= 20, axis=2)
        changed_ratio = float(np.mean(changed_mask))

        return mean_delta >= 14.0 and changed_ratio >= 0.10

    # ------------------------------------------------------------------
    # Click validation
    # ------------------------------------------------------------------

    def check_click(self, px: int, py: int) -> str:
        """
        Validate a player click at image coordinates (px, py).

        Returns
        -------
        "hit"      — click landed on an unfound difference (now marked found)
        "already"  — click landed on an already-found difference
        "mistake"  — click missed all differences (mistake counter incremented)
        "locked"   — round is already locked; click ignored
        """
        if self._locked:
            return "locked"

        for region in self._differences:
            if region.contains_point(px, py):
                if region.found:
                    return "already"
                region.found = True
                self._total_found += 1
                return "hit"

        # Missed — count as mistake
        self._mistakes += 1
        if self._mistakes >= self.MAX_MISTAKES:
            self._locked = True
        return "mistake"

    # ------------------------------------------------------------------
    # Game-state queries
    # ------------------------------------------------------------------

    def is_complete(self) -> bool:
        """Return True when all differences in the current round are found."""
        return len(self._differences) > 0 and all(d.found for d in self._differences)

    def reveal_all(self) -> list[DifferenceRegion]:
        """
        Mark every unfound difference as found and lock the round.
        Returns the list of regions that were revealed (previously unfound).
        """
        revealed = [d for d in self._differences if not d.found]
        for region in revealed:
            region.found = True
        self._locked = True
        return revealed
