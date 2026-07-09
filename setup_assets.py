import os
import shutil

# Paths
static_images_dir = r"store/static/store/images"
media_products_dir = r"media/products"
media_categories_dir = r"media/categories"

# Brand assets uploaded by the user
src_logo = r"C:/Users/siyaa/.gemini/antigravity/brain/e5ca9193-a6f7-4b85-8a56-d81e34642a7f/media__1780930088056.jpg"
src_veranda = r"C:/Users/siyaa/.gemini/antigravity/brain/e5ca9193-a6f7-4b85-8a56-d81e34642a7f/media__1780930088173.jpg"

# Create directories
os.makedirs(static_images_dir, exist_ok=True)
os.makedirs(media_products_dir, exist_ok=True)
os.makedirs(media_categories_dir, exist_ok=True)
os.makedirs(r"store/static/store/css", exist_ok=True)
os.makedirs(r"store/static/store/js", exist_ok=True)

print("Created directory structure.")

# Copy brand logo
if os.path.exists(src_logo):
    shutil.copy(src_logo, os.path.join(static_images_dir, "logo.jpg"))
    shutil.copy(src_logo, os.path.join(media_categories_dir, "cicada_wears.jpg"))
    print("Copied logo to static and media.")
else:
    print(f"Warning: Source logo not found at {src_logo}")

# Copy veranda image
if os.path.exists(src_veranda):
    shutil.copy(src_veranda, os.path.join(static_images_dir, "veranda.jpg"))
    shutil.copy(src_veranda, os.path.join(media_products_dir, "kerala_kurta.jpg"))
    print("Copied veranda image to static and media.")
else:
    print(f"Warning: Source veranda image not found at {src_veranda}")
