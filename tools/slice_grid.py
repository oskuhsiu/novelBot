from PIL import Image
import sys
import os

def slice_grid(image_path):
    try:
        im = Image.open(image_path)
        w, h = im.size
        # Assuming exactly 2x2 grid: Top-Left, Top-Right, Bot-Left, Bot-Right
        mid_w = w // 2
        mid_h = h // 2
        
        panels = []
        panels.append(im.crop((0, 0, mid_w, mid_h)))       # P1: TL
        panels.append(im.crop((mid_w, 0, w, mid_h)))       # P2: TR
        panels.append(im.crop((0, mid_h, mid_w, h)))       # P3: BL
        panels.append(im.crop((mid_w, mid_h, w, h)))       # P4: BR
        
        # Determine output filename pattern
        # strip_X.png -> strip_X_p1.png
        # If strip_X_grid.png -> strip_X_grid_p1.png? User wants final names.
        # I'll just append _p{i} to input stem.
        
        base, ext = os.path.splitext(image_path)
        
        for i, p in enumerate(panels):
            out_path = f"{base}_p{i+1}{ext}"
            p.save(out_path)
            print(f"Saved {out_path}")
            
    except Exception as e:
        print(f"Error slicing {image_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 slice_grid.py <image_path> [image_path ...]")
        sys.exit(1)
    
    for path in sys.argv[1:]:
        slice_grid(path)
