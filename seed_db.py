import os
import shutil
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cicada_rise.settings')
django.setup()

from django.contrib.auth.models import User
from store.models import Category, Product, ProductImage, ProductVariant, Review

# Paths to generated images
src_dir = r"C:/Users/siyaa/.gemini/antigravity/brain/e5ca9193-a6f7-4b85-8a56-d81e34642a7f"
logo_src = os.path.join(src_dir, "media__1780930088056.jpg")
veranda_src = os.path.join(src_dir, "media__1780930088173.jpg")

# Find the generated product image paths dynamically
gen_kurta = ""
gen_lehenga = ""
gen_kaftan = ""

for f in os.listdir(src_dir):
    if "_kurta_" in f and f.endswith(".png"):
        gen_kurta = os.path.join(src_dir, f)
    elif f.startswith("floral_lehenga_") and f.endswith(".png"):
        gen_lehenga = os.path.join(src_dir, f)
    elif f.startswith("linen_kaftan_") and f.endswith(".png"):
        gen_kaftan = os.path.join(src_dir, f)

# Destination folders
products_media_dir = r"media/products"
categories_media_dir = r"media/categories"
os.makedirs(products_media_dir, exist_ok=True)
os.makedirs(categories_media_dir, exist_ok=True)

# Copy files and define database-relative paths
kerala_kurta_path = "products/kerala_kurta.jpg"
indigo_kurta_path = "products/indigo_kurta.png"
floral_lehenga_path = "products/floral_lehenga.png"
linen_kaftan_path = "products/linen_kaftan.png"

# Perform file copy
if os.path.exists(veranda_src):
    shutil.copy(veranda_src, os.path.join(products_media_dir, "kerala_kurta.jpg"))
    shutil.copy(veranda_src, os.path.join(categories_media_dir, "heritage_collection.jpg"))

if gen_kurta and os.path.exists(gen_kurta):
    shutil.copy(gen_kurta, os.path.join(products_media_dir, "indigo_kurta.png"))
else:
    # Fallback to veranda if generated not found
    shutil.copy(veranda_src, os.path.join(products_media_dir, "indigo_kurta.png"))

if gen_lehenga and os.path.exists(gen_lehenga):
    shutil.copy(gen_lehenga, os.path.join(products_media_dir, "floral_lehenga.png"))
    shutil.copy(gen_lehenga, os.path.join(categories_media_dir, "seasonal_wears.jpg"))
else:
    shutil.copy(veranda_src, os.path.join(products_media_dir, "floral_lehenga.png"))
    shutil.copy(veranda_src, os.path.join(categories_media_dir, "seasonal_wears.jpg"))

if gen_kaftan and os.path.exists(gen_kaftan):
    shutil.copy(gen_kaftan, os.path.join(products_media_dir, "linen_kaftan.png"))
    shutil.copy(gen_kaftan, os.path.join(categories_media_dir, "slow_fashion.jpg"))
else:
    shutil.copy(veranda_src, os.path.join(products_media_dir, "linen_kaftan.png"))
    shutil.copy(veranda_src, os.path.join(categories_media_dir, "slow_fashion.jpg"))

if os.path.exists(logo_src):
    shutil.copy(logo_src, os.path.join(categories_media_dir, "cicada_wears.jpg"))

print("Media files seeded.")

# Create Users
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@cicadarise.com', 'admin123')
    admin.first_name = "Cicada Admin"
    admin.save()
    print("Superuser 'admin' created (password: admin123).")
else:
    admin = User.objects.get(username='admin')

if not User.objects.filter(username='customer').exists():
    customer = User.objects.create_user('customer', 'customer@gmail.com', 'customer123')
    customer.first_name = "Anjali"
    customer.last_name = "Nair"
    customer.save()
    
    # Update profile
    profile = customer.profile
    profile.phone = "+919447771056"
    profile.address = "joy's residency, electronic city, bangalore"
    profile.city = "karnataka"
    profile.state = "bangalore"
    profile.pin_code = "682016"
    profile.save()
    print("Customer 'customer' created (password: customer123).")
else:
    customer = User.objects.get(username='customer')

# Create Categories
cats_data = [
    {"name": "Heritage Collection", "desc": "A curated edit of elegant statement pieces inspired by refined silhouettes and premium detailing.", "image": "categories/heritage_collection.jpg"},
    {"name": "Cicada Wears", "desc": "Signature premium styles selected for modern comfort, graceful form, and elevated everyday dressing.", "image": "categories/cicada_wears.jpg"},
    {"name": "Seasonal Wears", "desc": "Lightweight seasonal collections chosen for changing occasions and the modern woman's active wardrobe.", "image": "categories/seasonal_wears.jpg"},
    {"name": "Curated Essentials", "desc": "Minimalist wardrobe staples selected for effortless comfort, quality feel, and polished daily style.", "image": "categories/slow_fashion.jpg"}
]

categories = {}
for cat in cats_data:
    obj, created = Category.objects.get_or_create(
        name=cat["name"],
        defaults={"description": cat["desc"], "image": cat["image"]}
    )
    categories[cat["name"]] = obj
    print(f"Category '{cat['name']}' ready.")

# Create Products
products_data = [
    {
        "name": "Heritage Gold Anarkali",
        "sku": "CR-2026-KKH",
        "category": "Heritage Collection",
        "desc": "An elegant ivory Anarkali set with premium golden detail and a flowing silhouette designed for timeless femininity and confident occasions.",
        "base_price": 8999.00,
        "is_featured": True,
        "is_seasonal": False,
        "is_cicada_wear": True,
        "image": kerala_kurta_path,
        "variants": [
            {"size": "S", "color": "Heritage Gold", "stock": 12},
            {"size": "M", "color": "Heritage Gold", "stock": 8},
            {"size": "L", "color": "Heritage Gold", "stock": 10},
            {"size": "XL", "color": "Heritage Gold", "stock": 2}, # Low stock
        ]
    },
    {
        "name": "Aahana Indigo Printed Kurta Set",
        "sku": "CR-2026-AHK",
        "category": "Cicada Wears",
        "desc": "Made from breathable cotton with a refined indigo print and delicate floral vine pattern. A soft, comfortable fit designed for easy summer styling.",
        "base_price": 4500.00,
        "is_featured": True,
        "is_seasonal": False,
        "is_cicada_wear": True,
        "image": indigo_kurta_path,
        "variants": [
            {"size": "S", "color": "Indigo Blue", "stock": 15},
            {"size": "M", "color": "Indigo Blue", "stock": 20},
            {"size": "L", "color": "Indigo Blue", "stock": 5}, # Low stock
            {"size": "S", "color": "Crimson Red", "stock": 4}, # Low stock
            {"size": "M", "color": "Crimson Red", "stock": 1}, # Critical stock
        ]
    },
    {
        "name": "Vrindavan Floral Lehenga",
        "sku": "CR-2026-VFL",
        "category": "Seasonal Wears",
        "desc": "A lightweight ivory-cream lehenga in pure silk, detailed with pastel watercolor floral prints and premium gold thread accents. A romantic garment that dances in the breeze.",
        "base_price": 12500.00,
        "is_featured": True,
        "is_seasonal": True,
        "is_cicada_wear": False,
        "image": floral_lehenga_path,
        "variants": [
            {"size": "M", "color": "Ivory Cream", "stock": 8},
            {"size": "L", "color": "Ivory Cream", "stock": 6},
            {"size": "XL", "color": "Ivory Cream", "stock": 3}, # Low stock
        ]
    },
    {
        "name": "Cocoon Linen Kaftan",
        "sku": "CR-2026-CLK",
        "category": "Curated Essentials",
        "desc": "Embodying the theme of refinement and cocoon-like ease, this loose-draped oatmeal kaftan is spun from 100% organic linen. It features deep side pockets and soft side slits for a modern look.",
        "base_price": 3200.00,
        "is_featured": False,
        "is_seasonal": False,
        "is_cicada_wear": False,
        "image": linen_kaftan_path,
        "variants": [
            {"size": "S", "color": "Oatmeal Cream", "stock": 2}, # Low stock
            {"size": "M", "color": "Oatmeal Cream", "stock": 3}, # Low stock
            {"size": "L", "color": "Oatmeal Cream", "stock": 1}, # Critical stock
        ]
    }
]

for prod in products_data:
    obj, created = Product.objects.get_or_create(
        sku=prod["sku"],
        defaults={
            "name": prod["name"],
            "category": categories[prod["category"]],
            "description": prod["desc"],
            "base_price": prod["base_price"],
            "is_featured": prod["is_featured"],
            "is_seasonal": prod["is_seasonal"],
            "is_cicada_wear": prod["is_cicada_wear"]
        }
    )
    print(f"Product '{prod['name']}' ready.")

    # Image
    ProductImage.objects.get_or_create(
        product=obj,
        image=prod["image"],
        defaults={"is_primary": True}
    )

    # Variants
    for var in prod["variants"]:
        ProductVariant.objects.get_or_create(
            product=obj,
            size=var["size"],
            color=var["color"],
            defaults={"stock": var["stock"]}
        )

# Add reviews
kerala_anarkali = Product.objects.get(sku="CR-2026-KKH")
Review.objects.get_or_create(
    product=kerala_anarkali,
    user=customer,
    defaults={
        "rating": 5,
        "comment": "This is the most elegant dress I have ever worn! The premium gold border is stunning and the fit is perfect.",
        "is_approved": True
    }
)
Review.objects.get_or_create(
    product=kerala_anarkali,
    user=admin,
    defaults={
        "rating": 5,
        "comment": "Absolute masterpiece of the collection. The premium fabric feels extremely premium.",
        "is_approved": True
    }
)

aahana_kurta = Product.objects.get(sku="CR-2026-AHK")
Review.objects.get_or_create(
    product=aahana_kurta,
    user=customer,
    defaults={
        "rating": 4,
        "comment": "Gorgeous indigo print. The colors are very vibrant. Took a day extra to arrive but totally worth it.",
        "is_approved": True
    }
)

# Unapproved review for testing moderation
Review.objects.get_or_create(
    product=aahana_kurta,
    user=customer,
    comment="Spam comment test for moderation.",
    defaults={
        "rating": 1,
        "is_approved": False
    }
)

print("Reviews seeded.")
print("Database seeding completed successfully.")
