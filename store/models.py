from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    COLLECTION_CHOICES = [
        ("Heritage Collection", "Heritage Collection"),
        ("Cicada Signature", "Cicada Signature"),
        ("Curated Essentials", "Curated Essentials")
    ]
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, verbose_name="Product Code")
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Promotional discounted price")
    
    # Redesign specs
    fabric_details = models.TextField(blank=True)
    care_instructions = models.TextField(blank=True)
    collection = models.CharField(max_length=100, default="Cicada Signature", choices=COLLECTION_CHOICES)
    
    is_featured = models.BooleanField(default=False)
    is_seasonal = models.BooleanField(default=False)
    is_cicada_wear = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def total_stock(self):
        return sum(variant.stock for variant in self.variants.all())

    @property
    def average_rating(self):
        approved_reviews = self.reviews.filter(is_approved=True)
        if approved_reviews.exists():
            return round(sum(r.rating for r in approved_reviews) / approved_reviews.count(), 1)
        return 0.0

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=5, choices=SIZE_CHOICES)
    color = models.CharField(max_length=50)
    stock = models.IntegerField(default=0)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Set if price differs from base price")

    class Meta:
        unique_together = ('product', 'size', 'color')

    def __str__(self):
        return f"{self.product.name} - Size: {self.size}, Color: {self.color} (Stock: {self.stock})"

    @property
    def price(self):
        if self.price_override is not None:
            return self.price_override
        if self.product.sale_price is not None:
            return self.product.sale_price
        return self.product.base_price

class RestockHistory(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='restock_logs')
    quantity_added = models.IntegerField()
    restocked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    restocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-restocked_at']
        verbose_name_plural = "Restock Histories"

    def __str__(self):
        return f"Restocked {self.quantity_added} units for {self.variant.product.name} ({self.variant.size}/{self.variant.color})"

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pin_code = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def total_spending(self):
        completed_orders = self.user.orders.filter(status='Delivered')
        if not completed_orders.exists():
            # Fallback to confirmed/shipped orders if no Delivered orders exist yet
            completed_orders = self.user.orders.filter(status__in=['Confirmed', 'Shipped', 'Delivered'])
        return sum(o.total_amount for o in completed_orders)

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        variant_desc = f" ({self.variant.size}/{self.variant.color})" if self.variant else ""
        return f"{self.quantity} x {self.product.name}{variant_desc} in {self.cart.user.username}'s Cart"

    @property
    def price(self):
        if self.variant:
            return self.variant.price
        if self.product.sale_price is not None:
            return self.product.sale_price
        return self.product.base_price

    @property
    def subtotal(self):
        return self.price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=15)
    shipping_address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='New', choices=STATUS_CHOICES)
    order_date = models.DateTimeField(auto_now_add=True)
    wa_message_sent = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Order #{self.id} by {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'} in Order #{self.order.id}"

    @property
    def subtotal(self):
        return self.price * self.quantity

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review ({self.rating}*) by {self.user.username} for {self.product.name}"

class HomepageSettings(models.Model):
    # Brand Configuration settings
    whatsapp_number = models.CharField(max_length=20, default="9447771056")
    bank_holder = models.CharField(max_length=100, default="Fathima Haris")
    bank_account = models.CharField(max_length=50, default="36137088305")
    bank_ifsc = models.CharField(max_length=20, default="SBIN0012890")
    bank_branch = models.CharField(max_length=100, default="Annamanada")
    
    # Homepage Configurable details
    hero_title = models.CharField(max_length=200, default="Thoughtfully Curated Fashion. Modern Elegance.")
    hero_subtitle = models.TextField(default="Cicada Rise handpicks premium women's clothing from trusted wholesale partners, offering elegant seasonal pieces that feel timeless, comfortable, and polished.")
    about_title = models.CharField(max_length=200, default="Every Woman Has a Season to Rise")
    about_text = models.TextField(default="Cicada Rise was created to bring premium women's fashion into a refined, thoughtfully curated edit. Every collection is selected with care for quality, comfort, and confidence.")

    class Meta:
        verbose_name_plural = "Homepage Settings"

    def __str__(self):
        return "Brand configuration & Settings"

class Contact(models.Model):
    """Store contact form submissions from users"""
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Resolved', 'Resolved'),
        ('Spam', 'Spam'),
    ]
    
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Contact Messages"
    
    def __str__(self):
        return f"{self.name} - {self.subject}"
