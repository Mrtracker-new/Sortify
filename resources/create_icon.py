from PIL import Image
import os

def create_icon():
    
    img = Image.new('RGB', (256, 256), color='white')
    img.save('icon.png')
    
    
    img.save('icon.ico', format='ICO')

if __name__ == "__main__":
    create_icon() 
