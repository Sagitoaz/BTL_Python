"""
Generate icon for BTL Python AI Coder extension
Creates a 128x128 PNG with Python + AI theme
"""
from PIL import Image, ImageDraw, ImageFont
import os

# Create 128x128 image with dark background
size = 128
img = Image.new('RGB', (size, size), color='#1e1e1e')
draw = ImageDraw.Draw(img)

# Draw gradient background circle (Python blue theme)
for i in range(60, 0, -1):
    alpha = int(255 * (60 - i) / 60)
    color = (52, 101, 164, alpha)  # Python blue
    draw.ellipse([64-i, 64-i, 64+i, 64+i], fill=color[:3])

# Draw Python logo-inspired shape (simplified)
# Two interlocking circles
draw.ellipse([30, 25, 70, 65], fill='#3776ab', outline='#ffd43b', width=3)
draw.ellipse([58, 63, 98, 103], fill='#ffd43b', outline='#3776ab', width=3)

# Draw "AI" text
try:
    # Try to use a nice font
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
except:
    # Fallback to default font
    font = ImageFont.load_default()

# Add "AI" text in bottom right
draw.text((75, 90), "AI", fill='#ffffff', font=font, stroke_width=2, stroke_fill='#000000')

# Draw sparkle/star effect for AI
star_points = [(110, 20), (112, 28), (120, 30), (112, 32), (110, 40), (108, 32), (100, 30), (108, 28)]
draw.polygon(star_points, fill='#ffd43b')
star_points2 = [(95, 10), (96, 15), (101, 16), (96, 17), (95, 22), (94, 17), (89, 16), (94, 15)]
draw.polygon(star_points2, fill='#ffffff')

# Save the icon
output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images', 'icon.png')
img.save(output_path, 'PNG')
print(f"✅ Icon created: {output_path}")
print(f"📏 Size: {size}x{size} PNG")
