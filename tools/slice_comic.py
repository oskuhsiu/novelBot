import cv2
import numpy as np
import sys
import os

def split_panels(image_path, output_dir):
    """
    Split a comic strip into panels based on white space detection or simple vertical splitting.
    For simplicity, this version assumes a vertical strip of panels separated by white/black gutters.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read {image_path}")
        return

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold to find gutters (assuming white or very light gutters)
    # Adjust threshold as needed based on style
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    
    # Logic to find horizontal gutters
    # Sum pixels across rows. Rows with high sum (all white) are gutters.
    # This is a naive implementation; a robust one would use contours.
    
    # Using contours directly on inverted image
    # Invert so content is white, background is black
    _, thresh_inv = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    
    contours, _ = cv2.findContours(thresh_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    panel_count = 0
    # Sort contours from top to bottom
    boundingBoxes = [cv2.boundingRect(c) for c in contours]
    (contours, boundingBoxes) = zip(*sorted(zip(contours, boundingBoxes),
                                            key=lambda b: b[1][1]))

    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        
        # Filter small noise
        if w < 50 or h < 50:
            continue
            
        panel = img[y:y+h, x:x+w]
        panel_filename = os.path.join(output_dir, f"split_panel_{panel_count}.png")
        cv2.imwrite(panel_filename, panel)
        print(f"Saved {panel_filename}")
        panel_count += 1

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python slice_comic.py <image_path> <output_dir>")
        sys.exit(1)
        
    split_panels(sys.argv[1], sys.argv[2])
