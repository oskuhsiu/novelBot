from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder(path, text="PENDING"):
    img = Image.new('RGB', (800, 1200), color=(50, 50, 50))
    d = ImageDraw.Draw(img)
    # Using default font if no TTF available
    # d.text((300, 600), text, fill=(200, 200, 200))
    # Draw a border
    d.rectangle([10, 10, 790, 1190], outline=(100, 100, 100), width=5)
    
    # Draw X
    d.line([10, 10, 790, 1190], fill=(70, 70, 70), width=2)
    d.line([10, 1190, 790, 10], fill=(70, 70, 70), width=2)
    
    img.save(path)
    print(f"Created {path}")

if __name__ == "__main__":
    create_placeholder("projects/Mankind/output/comic/ch_1/placeholder.png", "Strip Pending")
