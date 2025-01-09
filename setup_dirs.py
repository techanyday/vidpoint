import os

# Create necessary directories
dirs = ['templates', 'downloads', 'presentations']
for dir in dirs:
    os.makedirs(dir, exist_ok=True)
    print(f"Created directory: {dir}")
