# HIT137 Assignment 3 - Spot the Difference

## Overview
This desktop application demonstrates object-oriented programming, GUI development with Tkinter, and image processing with OpenCV.

The game flow is:
1. User loads an image.
2. Program creates an exact clone.
3. Program inserts 5 random non-overlapping visual differences into the clone.
4. User clicks on the modified image to find the differences.
5. App validates clicks and updates score, mistakes, and visual feedback.

## Setup
Install dependencies:

pip install opencv-python numpy pillow

Python 3.10+ is recommended.

## Run
python main.py

## Project Structure
- main.py: Entry point, creates Tk root and launches the UI.
- game_ui.py: Tkinter interface, canvas rendering, click handling, status updates.
- game_engine.py: Core game logic, difference generation, click validation, reveal logic.
- alterations.py: Abstract alteration interface and concrete emoji-object sticker alterers.
- debug_preview.py: Optional helper script for visual debugging.

## Code Explanation For Documentation

### 1) main.py
Purpose:
- Starts the application.
- Creates the main window and GameUI object.

Why it matters:
- Keeps startup logic separate from game logic and UI details.

### 2) game_engine.py

#### DifferenceRegion class
Purpose:
- Represents one hidden difference area.

Key attributes:
- x, y: top-left pixel of the region.
- w, h: width and height.
- alteration_type: which object sticker was drawn.
- found: whether user already found it.

Key methods:
- centre(): returns region center for drawing circles.
- contains_point(px, py, tolerance): click-proximity test.
- overlaps(other, margin): ensures regions do not overlap.

#### GameEngine class
Purpose:
- Controls game state and business logic.

Important state:
- _original_image and _modified_image: source and altered image.
- _differences: list of DifferenceRegion objects.
- _mistakes: wrong click count for current image.
- _locked: disables more guesses after 3 mistakes.
- _total_found: cumulative correct findings across rounds.

Important methods:
- load_image(path): reads image, clones it, resets state, generates differences.
- _generate_differences(): generates exactly 5 non-overlapping random regions, applies random object alterers, and validates visible change.
- check_click(px, py): returns hit/already/mistake/locked.
- is_complete(): true when all 5 are found.
- reveal_all(): marks all remaining differences found and locks round.

Design notes for report:
- Uses encapsulation via private attributes and read-only properties.
- Ensures exactly 5 differences or raises clear error.
- Uses proximity-based detection instead of exact-pixel clicking for better UX.

### 3) alterations.py

#### ImageAlterer (abstract base class)
Purpose:
- Defines a common interface for all alteration strategies.
- Methods required by subclasses:
   - name property.
   - apply(image, region).

Why this is important:
- Demonstrates inheritance and polymorphism.
- GameEngine can call alterer.apply() without knowing exact subclass.

#### Concrete sticker alterers
Current random object styles:
- StarStickerAlterer
- DuckStickerAlterer
- SmileyStickerAlterer
- HeartStickerAlterer

How they work:
- Each draws a distinct object with OpenCV primitives (circle, ellipse, polygon, polylines, fillPoly).
- Each modifies only its target region.
- Optional shadow effect improves visibility on complex backgrounds.

### 4) game_ui.py

Purpose:
- Implements all user interaction in Tkinter.

Main UI features:
- Load button with file picker (JPG, PNG, BMP, JPEG, TIFF).
- Left canvas: original image (reference only).
- Right canvas: modified image (clickable).
- Status bar shows:
   - Found (cumulative score)
   - Remaining (current image)
   - Mistakes (current image)
- Reveal button draws blue circles for unfound regions.

Click pipeline:
1. User clicks right canvas.
2. UI maps canvas coordinates to original image coordinates using current scale and centered offsets.
3. UI calls GameEngine.check_click().
4. If hit: draw red circles on both images and update counters.
5. If mistake: increment mistakes; at 3 mistakes show lockout warning.
6. If all found: show completion popup.

## OOP Criteria Mapping (For Assignment Rubric)

### At least three classes
Met:
- DifferenceRegion
- GameEngine
- GameUI
- ImageAlterer + 4 subclasses

### Encapsulation
Met:
- GameEngine uses private state and exposes properties.

### Constructors and methods
Met:
- All main classes use constructors and multiple methods.

### Class interaction
Met:
- GameUI interacts with GameEngine.
- GameEngine interacts with ImageAlterer subclasses.

### Inheritance
Met:
- Sticker classes inherit from ImageAlterer.

### Polymorphism
Met:
- Engine randomly picks a subclass and calls apply() through the same interface.

## OpenCV Criteria Mapping

### Exact clone then alteration
Met:
- Engine clones original image and alters clone only.

### Exactly 5 random non-overlapping differences
Met:
- Engine enforces 5 generated regions.
- Overlap check prevents intersections.

### At least 3 alteration types
Met:
- 4 object-based alteration types (star, duck, smiley, heart).

### All manipulation in OpenCV
Met:
- All sticker drawing uses OpenCV operations.

## Tkinter GUI Criteria Mapping

### Image loading and display
Met:
- File picker supports common formats.
- Original and modified shown side by side.

### Modified image only responds to clicks
Met:
- Click binding is on modified canvas only.

### Finding differences and visual marking
Met:
- Remaining counter visible.
- Hit detection uses proximity.
- Red circles drawn on both images for found differences.
- Completion popup shown at 5/5 found.

### Mistakes logic
Met:
- Mistake counter visible.
- Maximum 3 mistakes per image.
- Round locks after 3 mistakes with warning prompt.

### Reveal logic
Met:
- Reveal button marks all unfound with blue circles on both images.
- User can load a new image to restart.

### Authors
- Sujan Gautam
- Hemraj Budhathoki
- Sangam GC
- Aakriti BC

