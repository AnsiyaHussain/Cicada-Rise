from django.contrib import admin
from .models import (
    Category, Product, ProductImage, ProductVariant,
    CustomerProfile, Wishlist, Cart, CartItem, Order, OrderItem, Review,
    RestockHistory, HomepageSettings, Contact
)

# Inline models to make product management easier
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 3

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'base_price', 'sale_price', 'total_stock', 'is_featured', 'is_seasonal', 'is_cicada_wear')
    list_filter = ('category', 'is_featured', 'is_seasonal', 'is_cicada_wear')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'color', 'stock', 'price_override', 'price')
    list_filter = ('size', 'color')
    search_fields = ('product__name', 'product__sku', 'color')

@admin.register(RestockHistory)
class RestockHistoryAdmin(admin.ModelAdmin):
    list_display = ('variant', 'quantity_added', 'restocked_by', 'restocked_at')
    list_filter = ('restocked_at',)
    search_fields = ('variant__product__name', 'variant__product__sku')

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'state')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'items_count', 'total_price')
    inlines = [CartItemInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_phone', 'total_amount', 'status', 'order_date', 'wa_message_sent')
    list_filter = ('status', 'wa_message_sent', 'order_date')
    search_fields = ('customer_name', 'customer_phone', 'shipping_address')
    inlines = [OrderItemInline]

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'is_approved', 'is_featured', 'created_at')
    list_filter = ('is_approved', 'is_featured', 'rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'comment')
    actions = ['approve_reviews', 'disapprove_reviews', 'feature_reviews', 'unfeature_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_reviews.short_description = "Disapprove selected reviews"

    def feature_reviews(self, request, queryset):
        queryset.update(is_featured=True)
    feature_reviews.short_description = "Feature selected reviews"

    def unfeature_reviews(self, request, queryset):
        queryset.update(is_featured=False)
    unfeature_reviews.short_description = "Unfeature selected reviews"

@admin.register(HomepageSettings)
class HomepageSettingsAdmin(admin.ModelAdmin):
    list_display = ('whatsapp_number', 'bank_holder', 'bank_account', 'bank_ifsc', 'bank_branch')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'phone', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at', 'message')
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message', {
            'fields': ('subject', 'message')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

