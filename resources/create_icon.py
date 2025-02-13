from PIL import Image
import os

def create_icon():
    # Create a simple icon
    img = Image.new('RGB', (256, 256), color='white')
    img.save('icon.png')
    
    # Convert to ICO
    img.save('icon.ico', format='ICO')

if __name__ == "__main__":
    create_icon() 