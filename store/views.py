import urllib.parse
import io
import logging
from decimal import Decimal
from functools import wraps

logger = logging.getLogger('store')
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Avg, Count
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import (
    Category, Product, ProductVariant, ProductImage,
    CustomerProfile, Wishlist, Cart, CartItem, Order, OrderItem, Review,
    RestockHistory, HomepageSettings, Contact
)
from .forms import UserRegisterForm, UserProfileForm, CustomerProfileForm, ReviewForm

# Custom decorator for strict staff authorization
def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff:
            messages.error(request, "Access Denied: Staff credentials required.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Helper to format WhatsApp phone numbers correctly
def format_whatsapp_number(phone):
    cleaned = ''.join(c for c in phone if c.isdigit())
    if len(cleaned) == 10:
        return f"91{cleaned}"
    return cleaned

# ----------------- SHOPPING VIEWS -----------------

def home(request):
    featured_products = Product.objects.filter(is_featured=True).prefetch_related('images')[:4]
    seasonal_products = Product.objects.filter(is_seasonal=True).prefetch_related('images')[:4]
    cicada_products = Product.objects.filter(is_cicada_wear=True).prefetch_related('images')[:4]
    categories = Category.objects.filter(is_active=True)
    
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
        
    return render(request, 'store/home.html', {
        'featured_products': featured_products,
        'seasonal_products': seasonal_products,
        'cicada_products': cicada_products,
        'categories': categories,
        'brand_settings': brand_settings
    })

def shop(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    sort_by = request.GET.get('sort', '')

    products = Product.objects.all().prefetch_related('images')

    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) | 
            Q(sku__icontains=query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('base_price')
    elif sort_by == 'price_high':
        products = products.order_by('-base_price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('-is_featured')

    categories = Category.objects.filter(is_active=True)
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)

    return render(request, 'store/shop.html', {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'query': query,
        'sort_by': sort_by,
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    variants = product.variants.all()
    approved_reviews = product.reviews.filter(is_approved=True)
    
    action = request.GET.get('action')
    if action == 'add_to_cart' and request.user.is_authenticated:
        variant_id = request.GET.get('variant')
        qty = int(request.GET.get('quantity', 1))
        if variant_id:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            variant = get_object_or_404(ProductVariant, id=variant_id)
            from store.models import CartItem
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, product=product, variant=variant,
                defaults={'quantity': qty}
            )
            if not created:
                cart_item.quantity += qty
                cart_item.save()
            messages.success(request, f"Added '{product.name} ({variant.size})' to your bag successfully!")
            return redirect('product_detail', slug=slug)
    
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    review_form = ReviewForm()
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user
            review.is_approved = False
            review.save()
            messages.success(request, "Thank you! Your review has been submitted for moderation.")
            return redirect('product_detail', slug=slug)

    return render(request, 'store/product_detail.html', {
        'product': product,
        'variants': variants,
        'reviews': approved_reviews,
        'in_wishlist': in_wishlist,
        'review_form': review_form,
    })

def seasonal_wears(request):
    products = Product.objects.filter(is_seasonal=True).prefetch_related('images')
    return render(request, 'store/seasonal_wears.html', {'products': products})

def cicada_wears(request):
    products = Product.objects.filter(is_cicada_wear=True).prefetch_related('images')
    return render(request, 'store/cicada_wears.html', {'products': products})

def about(request):
    brand_settings = HomepageSettings.objects.first()
    return render(request, 'store/about.html', {'brand_settings': brand_settings})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        
        if name and email and subject and message:
            Contact.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message,
                status='New'
            )
            messages.success(request, "Your message has been sent. We will get back to you shortly!")
        else:
            messages.error(request, "Please fill in all required fields.")
        return redirect('contact')
    return render(request, 'store/contact.html')


# ----------------- WISHLIST & CART VIEWS -----------------

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product)
    
    if wishlist_item.exists():
        wishlist_item.delete()
        added = False
        message = "Removed from Wishlist"
    else:
        Wishlist.objects.create(user=request.user, product=product)
        added = True
        message = "Added to Wishlist"
        
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    if request.headers.get('HX-Request'):
        response = HttpResponse(
            f'<i class="{"fas text-danger" if added else "far"} fa-heart"></i>'
        )
        response['HX-Trigger'] = f'{{"updateWishlistCount": {wishlist_count}}}'
        return response
        
    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'shop'))

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
    shipping = cart.shipping_charge
    total = cart.total_price + shipping
    return render(request, 'store/cart.html', {
        'cart': cart,
        'shipping_charge': shipping,
        'shipping_enabled': brand_settings.shipping_enabled,
        'total_estimated': total
    })

@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get('variant')
    quantity = int(request.POST.get('quantity', 1))
    
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
    else:
        variant = product.variants.first()
        
    if not variant:
        messages.error(request, "This product is currently unavailable.")
        return redirect('product_detail', slug=product.slug)
        
    if variant.stock < quantity:
        messages.error(request, f"Sorry, only {variant.stock} units available.")
        return redirect('product_detail', slug=product.slug)
        
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=variant,
        defaults={'quantity': quantity}
    )
    
    if not item_created:
        if cart_item.quantity + quantity > variant.stock:
            cart_item.quantity = variant.stock
            messages.warning(request, f"Adjusted quantity to maximum available stock ({variant.stock}).")
        else:
            cart_item.quantity += quantity
        cart_item.save()
    else:
        messages.success(request, f"Added {product.name} to Cart.")
        
    cart_count = cart.items_count
    
    if request.headers.get('HX-Request'):
        response = HttpResponse("Added to Cart Successfully!")
        response['HX-Trigger'] = f'{{"updateCartCount": {cart_count}}}'
        return response
        
    return redirect('cart')

@login_required
@require_POST
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    action = request.POST.get('action')
    
    if action == 'increment':
        if cart_item.variant and cart_item.quantity < cart_item.variant.stock:
            cart_item.quantity += 1
            cart_item.save()
        else:
            return HttpResponse(status=400)
    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            
    cart = cart_item.cart
    cart_count = cart.items_count
    
    if request.headers.get('HX-Request'):
        brand_settings = HomepageSettings.objects.first()
        if not brand_settings:
            brand_settings = HomepageSettings.objects.create()
        shipping = brand_settings.shipping_charge if brand_settings.shipping_enabled else Decimal('0.00')
        total = cart.total_price + shipping
        
        html = f"""
        <div id="cart-item-qty-{item_id}" hx-swap-oob="true">{cart_item.quantity if cart_item.id and cart_item.quantity else 0}</div>
        <div id="cart-item-subtotal-{item_id}" hx-swap-oob="true">₹{cart_item.subtotal:,.2f}</div>
        <div id="cart-total-price" hx-swap-oob="true">₹{cart.total_price:,.2f}</div>
        <div id="cart-total-price-summary" hx-swap-oob="true">₹{total:,.2f}</div>
        """
        response = HttpResponse(html)
        response['HX-Trigger'] = f'{{"updateCartCount": {cart_count}}}'
        return response
        
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart = cart_item.cart
    cart_item.delete()
    cart_count = cart.items_count
    
    if request.headers.get('HX-Request'):
        response = HttpResponse("")
        response['HX-Trigger'] = f'{{"updateCartCount": {cart_count}, "reloadCart": true}}'
        return response
        
    messages.success(request, "Item removed from cart.")
    return redirect('cart')


# ----------------- WHATSAPP ORDER / BUY NOW WORKFLOW -----------------

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        variant_id = request.POST.get('variant')
        quantity = int(request.POST.get('quantity', 1))
    else:
        variant_id = request.GET.get('variant')
        quantity = int(request.GET.get('quantity', 1))
    
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
    else:
        variant = product.variants.first()
        
    if not variant:
        messages.error(request, "This variant is out of stock.")
        return redirect('product_detail', slug=product.slug)
        
    if variant.stock < quantity:
        messages.error(request, f"Only {variant.stock} units left in stock.")
        return redirect('product_detail', slug=product.slug)
        
    profile = request.user.profile
    if not profile.phone or not profile.address:
        messages.warning(request, "Please fill in your shipping details before buying.")
        return redirect('profile')
        
    # Create Order record
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
    if brand_settings.shipping_enabled:
        if product.shipping_charge and product.shipping_charge > 0:
            shipping = product.shipping_charge
        else:
            shipping = brand_settings.shipping_charge
    else:
        shipping = Decimal('0.00')
    subtotal = variant.price * quantity
    total = subtotal + shipping

    order = Order.objects.create(
        user=request.user,
        customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        customer_phone=profile.phone,
        shipping_address=f"{profile.address}, {profile.city}, {profile.state} - {profile.pin_code}",
        shipping_charge=shipping,
        total_amount=total,
        status='New'
    )
    
    OrderItem.objects.create(
        order=order,
        product=product,
        variant=variant,
        quantity=quantity,
        price=variant.price
    )
    
    whatsapp_phone = format_whatsapp_number(brand_settings.whatsapp_number)
    customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    
    msg_template = (
        "Hello Cicada Rise! I would like to place an order:\n\n"
        "✨ *ORDER DETAILS* ✨\n"
        "• *Product Name*: {prod_name}\n"
        "• *Product Code (SKU)*: {prod_sku}\n"
        "• *Size*: {size}\n"
        "• *Quantity*: {qty}\n"
        "• *Subtotal*: ₹{subtotal:,.2f}\n"
        "• *Shipping*: ₹{shipping:,.2f}\n"
        "• *Total Value*: ₹{total:,.2f}\n\n"
        "👤 *CUSTOMER DETAILS*\n"
        "• *Name*: {cust_name}\n"
        "• *Phone*: {cust_phone}\n"
        "• *Shipping Address*: {cust_addr}\n\n"
        "📲 *UPI QR CODE TO PAY* 📲\n"
        "Scan/Tap to pay: {qr_code_url}\n"
        "UPI ID: 9447771056@ptyes\n\n"
        "🏦 *DIRECT BANK TRANSFER DETAILS* 🏦\n"
        "• *Bank*: SBI\n"
        "• *Account Holder*: {bank_holder}\n"
        "• *Account Number*: {bank_acc}\n"
        "• *IFSC Code*: {bank_ifsc}\n"
        "• *Branch*: {bank_branch}\n\n"
        "*Please complete the payment of ₹{total:,.2f} using either the UPI QR code or bank transfer, and share the transaction screenshot here to confirm your order.*"
    )
    
    qr_code_url = request.build_absolute_uri('/static/store/images/upi_qr_code.jpg')
    cust_full_address = f"{profile.address}, {profile.city}, {profile.state} - {profile.pin_code}"
    
    msg = msg_template.format(
        prod_name=product.name,
        prod_sku=product.sku,
        size=variant.size,
        color=variant.color,
        qty=quantity,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        cust_name=customer_name,
        cust_phone=profile.phone,
        cust_addr=cust_full_address,
        qr_code_url=qr_code_url,
        bank_holder=brand_settings.bank_holder,
        bank_acc=brand_settings.bank_account,
        bank_ifsc=brand_settings.bank_ifsc,
        bank_branch=brand_settings.bank_branch
    )
    
    encoded_msg = urllib.parse.quote(msg)
    wa_url = f"https://api.whatsapp.com/send?phone={whatsapp_phone}&text={encoded_msg}"
    
    order.wa_message_sent = True
    order.save()
    
    return redirect(wa_url)

@login_required
@require_POST
def checkout_cart(request):
    cart = get_object_or_404(Cart, user=request.user)
    if cart.items_count == 0:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')
        
    profile = request.user.profile
    if not profile.phone or not profile.address:
        messages.warning(request, "Please fill in your shipping details before checking out.")
        return redirect('profile')
        
    for item in cart.items.all():
        if item.variant and item.variant.stock < item.quantity:
            messages.error(request, f"Sorry, '{item.product.name} ({item.variant.size})' only has {item.variant.stock} left. Please adjust your cart.")
            return redirect('cart')
            
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
    shipping = cart.shipping_charge
    subtotal = cart.total_price
    total = subtotal + shipping

    order = Order.objects.create(
        user=request.user,
        customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        customer_phone=profile.phone,
        shipping_address=f"{profile.address}, {profile.city}, {profile.state} - {profile.pin_code}",
        shipping_charge=shipping,
        total_amount=total,
        status='New'
    )
    
    items_summary = []
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            quantity=item.quantity,
            price=item.price
        )
        pass
            
        items_summary.append(
            f"• *{item.product.name}* ({item.variant.size if item.variant else 'N/A'}/{item.variant.color if item.variant else 'N/A'})\n"
            f"  Code: {item.product.sku} | Qty: {item.quantity} | Subtotal: ₹{item.subtotal:,.2f}"
        )
        
    summary_text = "\n".join(items_summary)
    
    whatsapp_phone = format_whatsapp_number(brand_settings.whatsapp_number)
    customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    
    msg_template = (
        "Hello Cicada Rise! I would like to place a Cart Order:\n\n"
        "✨ *ORDER DETAILS* ✨\n"
        "{summary}\n\n"
        "• *Subtotal*: ₹{subtotal:,.2f}\n"
        "• *Shipping*: ₹{shipping:,.2f}\n"
        "⭐ *ORDER TOTAL*: ₹{total:,.2f}\n\n"
        "👤 *CUSTOMER DETAILS*\n"
        "• *Name*: {cust_name}\n"
        "• *Phone*: {cust_phone}\n"
        "• *Shipping Address*: {cust_addr}\n\n"
        "📲 *UPI QR CODE TO PAY* 📲\n"
        "Scan/Tap to pay: {qr_code_url}\n"
        "UPI ID: 9447771056@ptyes\n\n"
        "🏦 *DIRECT BANK TRANSFER DETAILS* 🏦\n"
        "• *Bank*: SBI\n"
        "• *Account Holder*: {bank_holder}\n"
        "• *Account Number*: {bank_acc}\n"
        "• *IFSC Code*: {bank_ifsc}\n"
        "• *Branch*: {bank_branch}\n\n"
        "*Please complete the payment of ₹{total:,.2f} using either the UPI QR code or bank transfer, and share the transaction screenshot here to confirm your order.*"
    )
    
    qr_code_url = request.build_absolute_uri('/static/store/images/upi_qr_code.jpg')
    cust_full_address = f"{profile.address}, {profile.city}, {profile.state} - {profile.pin_code}"
    
    msg = msg_template.format(
        summary=summary_text,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        cust_name=customer_name,
        cust_phone=profile.phone,
        cust_addr=cust_full_address,
        qr_code_url=qr_code_url,
        bank_holder=brand_settings.bank_holder,
        bank_acc=brand_settings.bank_account,
        bank_ifsc=brand_settings.bank_ifsc,
        bank_branch=brand_settings.bank_branch
    )
    
    cart.items.all().delete()
    
    encoded_msg = urllib.parse.quote(msg)
    wa_url = f"https://api.whatsapp.com/send?phone={whatsapp_phone}&text={encoded_msg}"
    
    order.wa_message_sent = True
    order.save()
    
    return redirect(wa_url)


# ----------------- AUTHENTICATION VIEWS -----------------

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')
        
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            Cart.objects.get_or_create(user=user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            
            # separation of role redirects
            if user.is_staff:
                return redirect('admin_dashboard')
            return redirect(request.GET.get('next', 'home'))
        else:
            messages.error(request, "Invalid username or password.")
            
    google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    if not google_client_id:
        import os
        google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        
    return render(request, 'store/login.html', {'google_client_id': google_client_id})

def register_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')
        
    form = UserRegisterForm()
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            Cart.objects.create(user=user)
            messages.success(request, "Registration successful! Please log in with your credentials.")
            return redirect('login')
            
    google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    if not google_client_id:
        import os
        google_client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        
    return render(request, 'store/register.html', {'form': form, 'google_client_id': google_client_id})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

@csrf_exempt
def google_login_verify(request):
    import urllib.request
    import json
    from django.http import JsonResponse
    from django.contrib import messages
    from django.conf import settings
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id_token = data.get('credential')
            next_url = data.get('next', 'home')
            from django.shortcuts import resolve_url
            try:
                next_url = resolve_url(next_url)
            except Exception:
                if not next_url.startswith('/'):
                    next_url = '/'
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid request payload.'}, status=400)
            
        if not id_token:
            return JsonResponse({'success': False, 'error': 'No credential token provided.'}, status=400)
            
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                token_info = json.loads(response.read().decode())
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to verify token: {str(e)}'}, status=400)
            
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        if not client_id:
            import os
            client_id = os.environ.get('GOOGLE_CLIENT_ID')
            
        if client_id and token_info.get('aud') != client_id:
            return JsonResponse({'success': False, 'error': 'Audience verification failed.'}, status=400)
            
        if token_info.get('email_verified') not in ('true', True):
            return JsonResponse({'success': False, 'error': 'Google email is not verified.'}, status=400)
            
        email = token_info.get('email')
        first_name = token_info.get('given_name', '')
        last_name = token_info.get('family_name', '')
        
        user = User.objects.filter(email=email).first()
        if not user:
            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                import random
                username = f"{username}_{random.randint(100, 999)}"
                
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            Cart.objects.get_or_create(user=user)
        else:
            Cart.objects.get_or_create(user=user)
            
        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
        if user.is_staff:
            from django.shortcuts import resolve_url
            next_url = resolve_url('admin_dashboard')
        return JsonResponse({'success': True, 'redirect_url': next_url})
        
    return JsonResponse({'success': False, 'error': 'Only POST method is allowed.'}, status=405)

@login_required
def profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    user_form = UserProfileForm(instance=request.user)
    profile_form = CustomerProfileForm(instance=profile)
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = CustomerProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your account and shipping details have been saved successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Please check and correct the errors in your details form.")
            
    return render(request, 'store/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'orders': orders,
    })


# ----------------- PREMIUM LUXURY ERP DASHBOARD VIEWS -----------------

@staff_required
def dashboard_overview(request):
    total_products = Product.objects.count()
    active_products = Product.objects.filter(category__is_active=True).count()
    
    out_of_stock = ProductVariant.objects.filter(stock=0).count()
    low_stock = ProductVariant.objects.filter(stock__lte=5, stock__gt=0).count()
    
    total_customers = User.objects.filter(is_staff=False).count()
    total_orders = Order.objects.count()
    
    pending_orders = Order.objects.filter(status__in=['New', 'Pending']).count()
    confirmed_orders = Order.objects.filter(status='Confirmed').count()
    shipped_orders = Order.objects.filter(status='Shipped').count()
    delivered_orders = Order.objects.filter(status='Delivered').count()
    
    monthly_rev = Order.objects.filter(status__in=['Confirmed', 'Packed', 'Shipped', 'Delivered']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0.00
    
    best_sellers = Product.objects.annotate(
        sales_qty=Sum('orderitem__quantity'),
        sales_val=Sum('orderitem__price')
    ).filter(sales_qty__gt=0).order_by('-sales_qty')[:5]
    
    recent_registrations = User.objects.filter(is_staff=False).order_by('-date_joined')[:5]
    low_stock_variants = ProductVariant.objects.filter(stock__lte=5).select_related('product')
    
    return render(request, 'store/dashboard/analytics.html', {
        'total_products': total_products,
        'active_products': active_products,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'monthly_rev': monthly_rev,
        'best_sellers': best_sellers,
        'recent_registrations': recent_registrations,
        'low_stock_variants': low_stock_variants,
    })

@staff_required
def dashboard_admin_profile(request):
    """Display admin profile and personal details"""
    admin_user = request.user
    staff_count = User.objects.filter(is_staff=True).count()
    total_contacts = Contact.objects.count()
    unread_contacts = Contact.objects.filter(status='New').count()
    
    return render(request, 'store/dashboard/admin_profile.html', {
        'admin_user': admin_user,
        'staff_count': staff_count,
        'total_contacts': total_contacts,
        'unread_contacts': unread_contacts,
    })

@staff_required
def dashboard_change_password(request):
    """Handle admin password change"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        user = request.user
        
        # Validate current password
        if not user.check_password(current_password):
            return JsonResponse({'success': False, 'error': 'Current password is incorrect.'}, status=400)
        
        # Validate new passwords match
        if new_password != confirm_password:
            return JsonResponse({'success': False, 'error': 'New passwords do not match.'}, status=400)
        
        # Validate password length
        if len(new_password) < 6:
            return JsonResponse({'success': False, 'error': 'Password must be at least 6 characters long.'}, status=400)
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        return JsonResponse({'success': True, 'message': 'Password changed successfully. Please log in again.'})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@staff_required
def dashboard_contacted_users(request):
    """Display all contacted users and manage contact status"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    contacts = Contact.objects.all().order_by('-created_at')
    
    if status_filter:
        contacts = contacts.filter(status=status_filter)
    
    if search_query:
        contacts = contacts.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    contact_status_choices = Contact._meta.get_field('status').choices
    new_count = Contact.objects.filter(status='New').count()
    contacted_count = Contact.objects.filter(status='Contacted').count()
    resolved_count = Contact.objects.filter(status='Resolved').count()
    
    return render(request, 'store/dashboard/contacted_users.html', {
        'contacts': contacts,
        'status_filter': status_filter,
        'search_query': search_query,
        'contact_status_choices': contact_status_choices,
        'new_count': new_count,
        'contacted_count': contacted_count,
        'resolved_count': resolved_count,
    })

@staff_required
def dashboard_update_contact_status(request, contact_id):
    """Update contact status"""
    contact = get_object_or_404(Contact, id=contact_id)
    new_status = request.POST.get('status')
    
    if new_status and new_status in dict(Contact._meta.get_field('status').choices):
        contact.status = new_status
        contact.save()
        messages.success(request, f"Contact status updated to {new_status}")
    
    return redirect('dashboard_contacted_users')

@staff_required
def dashboard_orders(request):
    # Handle bulk status updates
    if request.method == 'POST':
        bulk_status = request.POST.get('bulk_status')
        order_ids = request.POST.getlist('order_ids')
        
        if bulk_status and order_ids:
            updated_count = Order.objects.filter(id__in=order_ids).update(status=bulk_status)
            messages.success(request, f"Updated {updated_count} order(s) to status: {bulk_status}")
        else:
            messages.error(request, "Please select orders and a status.")
        
        return redirect('dashboard_orders')
    
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-order_date')
    
    orders = Order.objects.all().prefetch_related('items__product__images', 'items__variant')
    
    if query:
        orders = orders.filter(
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query) |
            Q(id__icontains=query.replace('#CR-', ''))
        )
        
    if status_filter:
        orders = orders.filter(status=status_filter)
        
    orders = orders.order_by(sort_by)
    status_choices = Order.STATUS_CHOICES
    
    return render(request, 'store/dashboard/orders.html', {
        'orders': orders,
        'query': query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'status_choices': status_choices,
        'is_whatsapp_view': False
    })

@staff_required
def dashboard_whatsapp_orders(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-order_date')
    
    orders = Order.objects.filter(status__in=['New', 'Pending']).prefetch_related('items__product__images', 'items__variant')
    
    if query:
        orders = orders.filter(
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )
        
    orders = orders.order_by(sort_by)
    
    return render(request, 'store/dashboard/orders.html', {
        'orders': orders,
        'query': query,
        'sort_by': sort_by,
        'is_whatsapp_view': True
    })

@staff_required
def dashboard_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all().select_related('product', 'variant')
    
    steps = ['New', 'Pending', 'Confirmed', 'Packed', 'Shipped', 'Delivered']
    active_step = -1
    if order.status in steps:
        active_step = steps.index(order.status)
        
    return render(request, 'store/dashboard/order_detail.html', {
        'order': order,
        'order_items': order_items,
        'steps': steps,
        'active_step': active_step,
    })

@staff_required
@require_POST
def dashboard_update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    notes = request.POST.get('notes')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        
    if notes is not None:
        order.admin_notes = notes

    shipping_input = request.POST.get('shipping_charge')
    if shipping_input is not None and shipping_input != '':
        try:
            new_shipping = Decimal(shipping_input)
            if new_shipping >= 0:
                diff = new_shipping - order.shipping_charge
                order.shipping_charge = new_shipping
                order.total_amount += diff
        except (ValueError, TypeError):
            pass
        
    order.save()
    
    if request.headers.get('HX-Request'):
        status_colors = {
            'New': 'info',
            'Pending': 'warning',
            'Confirmed': 'primary',
            'Packed': 'secondary',
            'Shipped': 'dark',
            'Delivered': 'success',
            'Cancelled': 'danger'
        }
        
        monthly_rev = Order.objects.filter(status__in=['Confirmed', 'Packed', 'Shipped', 'Delivered']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0.00
        pending_orders = Order.objects.filter(status__in=['New', 'Pending']).count()
        
        html = f"""
        <span class="badge bg-{status_colors.get(order.status, 'secondary')}" id="order-status-badge-{{ order.id }}">
            {order.status}
        </span>
        <span hx-swap-oob="true" id="sales-metric-total">₹{monthly_rev:,.2f}</span>
        <span hx-swap-oob="true" id="sales-metric-pending">{pending_orders}</span>
        <div class="alert alert-success py-1 px-2 mb-0 mt-1" id="order-toast-{order.id}">
             Order status updated!
             <script>
                 setTimeout(() => {{
                     document.getElementById('order-toast-{order.id}').remove();
                 }}, 2000);
             </script>
        </div>
        """
        return HttpResponse(html)
        
    messages.success(request, "Order status updated successfully.")
    return redirect('dashboard_order_detail', order_id=order.id)

@staff_required
def export_orders_pdf(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-order_date')

    orders = Order.objects.all()
    if query:
        orders = orders.filter(
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query) |
            Q(id__icontains=query.replace('#CR-', ''))
        )
    if status_filter:
        orders = orders.filter(status=status_filter)
    orders = orders.order_by(sort_by)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#5B1A14'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        spaceAfter=12
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#161616')
    )

    elements = []
    elements.append(Paragraph("CICADA RISE - ORDERS SUMMARY REPORT", title_style))
    filter_text = f"Search Keyword: '{query or 'All'}' | Status Filter: '{status_filter or 'All'}' | Total Orders: {orders.count()}"
    elements.append(Paragraph(filter_text, subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#C8A16A'), spaceAfter=12))

    data = [
        [
            Paragraph("Order ID", table_header_style),
            Paragraph("Date", table_header_style),
            Paragraph("Customer Name", table_header_style),
            Paragraph("Phone Number", table_header_style),
            Paragraph("Status", table_header_style),
            Paragraph("Total Price", table_header_style)
        ]
    ]

    total_sum = 0.0
    for order in orders:
        total_sum += float(order.total_amount)
        data.append([
            Paragraph(f"#CR-{order.id}", table_cell_style),
            Paragraph(order.order_date.strftime("%d %b %Y %H:%M"), table_cell_style),
            Paragraph(order.customer_name, table_cell_style),
            Paragraph(order.customer_phone, table_cell_style),
            Paragraph(order.status, table_cell_style),
            Paragraph(f"Rs. {order.total_amount:,.2f}", table_cell_style)
        ])

    data.append([
        Paragraph("<b>GRAND TOTAL</b>", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph(f"<b>{orders.count()} Orders</b>", table_cell_style),
        Paragraph(f"<b>Rs. {total_sum:,.2f}</b>", table_cell_style)
    ])

    t = Table(data, colWidths=[65, 95, 140, 90, 75, 75])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5B1A14')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#D6B48C')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F3ED')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#C8A16A')),
    ]))

    elements.append(t)
    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Cicada_Rise_Orders_Report.pdf"'
    return response

@staff_required
def export_order_detail_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all().select_related('product', 'variant')
    brand_settings = HomepageSettings.objects.first()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#5B1A14'),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#C8A16A'),
        spaceAfter=15
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#5B1A14'),
        spaceAfter=4
    )
    normal_text = ParagraphStyle(
        'NormalText',
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor('#333333'),
        leading=12
    )
    table_header_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=colors.white
    )
    table_cell_style = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#161616')
    )

    elements = []
    elements.append(Paragraph("CICADA RISE - OFFICIAL INVOICE", title_style))
    elements.append(Paragraph("Wear The Story Of You | Luxury Slow Fashion ERP", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#C8A16A'), spaceAfter=12))

    order_info = f"""
    <b>Order Ref:</b> #CR-{order.id}<br/>
    <b>Date Placed:</b> {order.order_date.strftime("%d %B %Y, %I:%M %p")}<br/>
    <b>Current Status:</b> {order.status}<br/>
    <b>WhatsApp Sent:</b> {'Yes' if order.wa_message_sent else 'No'}
    """
    customer_info = f"""
    <b>Customer Name:</b> {order.customer_name}<br/>
    <b>Contact Phone:</b> {order.customer_phone}<br/>
    <b>Shipping Address:</b> {order.shipping_address}
    """

    meta_table_data = [
        [
            Paragraph("<b>ORDER METADATA</b>", section_heading),
            Paragraph("<b>CUSTOMER & DELIVERY DETAILS</b>", section_heading)
        ],
        [
            Paragraph(order_info, normal_text),
            Paragraph(customer_info, normal_text)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    items_data = [
        [
            Paragraph("Product Design", table_header_style),
            Paragraph("SKU Code", table_header_style),
            Paragraph("Size / Color", table_header_style),
            Paragraph("Qty", table_header_style),
            Paragraph("Unit Price", table_header_style),
            Paragraph("Subtotal", table_header_style)
        ]
    ]

    for item in order_items:
        p_name = item.product.name if item.product else "Deleted Product"
        sku = item.product.sku if item.product else "N/A"
        variant_desc = f"{item.variant.size} / {item.variant.color}" if item.variant else "N/A"
        items_data.append([
            Paragraph(p_name, table_cell_style),
            Paragraph(sku, table_cell_style),
            Paragraph(variant_desc, table_cell_style),
            Paragraph(str(item.quantity), table_cell_style),
            Paragraph(f"Rs. {item.price:,.2f}", table_cell_style),
            Paragraph(f"Rs. {item.subtotal:,.2f}", table_cell_style)
        ])

    subtotal_sum = sum(item.subtotal for item in order_items)
    if order.shipping_charge > 0:
        items_data.append([
            Paragraph("Subtotal", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph(f"Rs. {subtotal_sum:,.2f}", table_cell_style)
        ])
        items_data.append([
            Paragraph("Shipping Charge", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph("", table_cell_style),
            Paragraph(f"Rs. {order.shipping_charge:,.2f}", table_cell_style)
        ])

    items_data.append([
        Paragraph("<b>GRAND TOTAL</b>", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph("", table_cell_style),
        Paragraph(f"<b>Rs. {order.total_amount:,.2f}</b>", table_cell_style)
    ])

    items_table = Table(items_data, colWidths=[140, 80, 100, 40, 90, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5B1A14')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#D6B48C')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F3ED')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#C8A16A')),
    ]))

    elements.append(items_table)
    elements.append(Spacer(1, 15))

    if brand_settings:
        bank_details = f"<b>Merchant Transfer Details:</b> Holder: {brand_settings.bank_holder} | Account: {brand_settings.bank_account} | IFSC: {brand_settings.bank_ifsc} | Branch: {brand_settings.bank_branch} | WhatsApp: +91 {brand_settings.whatsapp_number}"
        elements.append(Paragraph(bank_details, normal_text))
        elements.append(Spacer(1, 8))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#D6B48C'), spaceAfter=8))
    policy_note = "<i>Policy Note: Return or exchange requests must be filed within 24 hours of delivery receipt accompanied by an uninterrupted unboxing video recording.</i>"
    elements.append(Paragraph(policy_note, normal_text))

    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Cicada_Rise_Invoice_CR-{order.id}.pdf"'
    return response

@staff_required
@require_POST
def dashboard_order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_ref = f"#CR-{order.id}"
    order.delete()
    messages.success(request, f"Order {order_ref} has been permanently deleted.")
    return redirect('dashboard_orders')

@staff_required
@require_POST
def dashboard_clear_cancelled_orders(request):
    deleted_count, _ = Order.objects.filter(status='Cancelled').delete()
    messages.success(request, f"Successfully cleared {deleted_count} cancelled order(s) from system records.")
    return redirect('dashboard_orders')

@staff_required
def dashboard_products(request):
    products = Product.objects.all().prefetch_related('variants', 'images')
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        name = request.POST.get('name', '').strip()
        sku = request.POST.get('sku')
        if sku:
            sku = sku.strip()
        if not sku:
            sku = None

        logger.info(f"PRODUCT CREATE/UPDATE REQUEST — User: {request.user.username}, Action: {'EDIT' if product_id else 'CREATE'}, Name: '{name}', SKU: '{sku}'")

        # Validate uploaded image sizes (must be under 2 MB)
        uploaded_images = request.FILES.getlist('images')
        for img in uploaded_images:
            if img.size > 2 * 1024 * 1024:
                logger.warning(f"PRODUCT VALIDATION FAILED — Image '{img.name}' exceeds 2 MB ({img.size} bytes)")
                messages.error(request, f"Upload Failed: Image '{img.name}' is more than 2 MB. Please compress your images under 2 MB before uploading.")
                return redirect('dashboard_products')
                
        if not name:
            logger.warning("PRODUCT VALIDATION FAILED — Missing product name")
            messages.error(request, "Product name is required.")
            return redirect('dashboard_products')

        cat_id = request.POST.get('category')
        if not cat_id:
            logger.warning("PRODUCT VALIDATION FAILED — Missing category ID")
            messages.error(request, "Please select a valid category.")
            return redirect('dashboard_products')
            
        category = Category.objects.filter(id=cat_id).first()
        if not category:
            logger.warning(f"PRODUCT VALIDATION FAILED — Category ID {cat_id} not found in database")
            messages.error(request, "Selected category does not exist.")
            return redirect('dashboard_products')

        price = request.POST.get('base_price')
        sale_price = request.POST.get('sale_price')
        shipping_charge_input = request.POST.get('shipping_charge')
        collection = request.POST.get('collection') or "Cicada Signature"
        desc = request.POST.get('description') or ""
        fabric = request.POST.get('fabric_details') or ""
        care = request.POST.get('care_instructions') or ""
        
        # Validate base price
        try:
            base_price_val = Decimal(price)
            if base_price_val < 0:
                logger.warning(f"PRODUCT VALIDATION FAILED — Negative base price: {price}")
                messages.error(request, "Base price cannot be negative.")
                return redirect('dashboard_products')
        except (ValueError, TypeError, Exception):
            logger.warning(f"PRODUCT VALIDATION FAILED — Invalid base price input: {price}")
            messages.error(request, "Please enter a valid base price.")
            return redirect('dashboard_products')

        # Validate sale price if provided
        sale_price_val = None
        if sale_price and sale_price.strip():
            try:
                sale_price_val = Decimal(sale_price.strip())
                if sale_price_val < 0:
                    logger.warning(f"PRODUCT VALIDATION FAILED — Negative sale price: {sale_price}")
                    messages.error(request, "Sale price cannot be negative.")
                    return redirect('dashboard_products')
            except (ValueError, TypeError, Exception):
                logger.warning(f"PRODUCT VALIDATION FAILED — Invalid sale price input: {sale_price}")
                messages.error(request, "Please enter a valid sale price.")
                return redirect('dashboard_products')

        # Validate shipping charge
        shipping_val = Decimal('0.00')
        if shipping_charge_input is not None and shipping_charge_input.strip() != '':
            try:
                shipping_val = Decimal(shipping_charge_input.strip())
                if shipping_val < 0:
                    logger.warning(f"PRODUCT VALIDATION FAILED — Negative shipping charge: {shipping_charge_input}")
                    messages.error(request, "Shipping charge cannot be negative.")
                    return redirect('dashboard_products')
            except (ValueError, TypeError, Exception):
                logger.warning(f"PRODUCT VALIDATION FAILED — Invalid shipping charge input: {shipping_charge_input}")
                messages.error(request, "Please enter a valid shipping charge.")
                return redirect('dashboard_products')

        # Validate SKU uniqueness
        if sku:
            sku_query = Product.objects.filter(sku__iexact=sku)
            if product_id:
                sku_query = sku_query.exclude(id=product_id)
            if sku_query.exists():
                logger.warning(f"PRODUCT VALIDATION FAILED — Duplicate SKU '{sku}' already exists")
                messages.error(request, f"This SKU '{sku}' already exists. Please enter a unique SKU.")
                return redirect('dashboard_products')

        is_featured = 'is_featured' in request.POST
        is_seasonal = 'is_seasonal' in request.POST
        is_cicada_wear = 'is_cicada_wear' in request.POST
        
        selected_sizes = request.POST.getlist('sizes')
        all_possible_sizes = ['S', 'M', 'L', 'XL', 'XXL', '3XL']
        
        logger.info(f"VALIDATION PASSED — Starting DB transaction for '{name}' (Base Price: ₹{base_price_val}, Shipping: ₹{shipping_val})")

        try:
            from django.db import transaction
            with transaction.atomic():
                if product_id:
                    product = get_object_or_404(Product, id=product_id)
                    product.name = name
                    product.sku = sku
                    product.category = category
                    product.base_price = base_price_val
                    product.sale_price = sale_price_val
                    product.shipping_charge = shipping_val
                    product.collection = collection
                    product.description = desc
                    product.fabric_details = fabric
                    product.care_instructions = care
                    product.is_featured = is_featured
                    product.is_seasonal = is_seasonal
                    product.is_cicada_wear = is_cicada_wear
                    product.save()

                    for sz in all_possible_sizes:
                        if sz in selected_sizes:
                            stock_val = request.POST.get(f'stock_{sz}', 0)
                            try:
                                st_num = int(stock_val) if stock_val is not None and str(stock_val).strip() != '' else 0
                                if st_num < 0:
                                    st_num = 0
                            except ValueError:
                                st_num = 0
                            var, created = ProductVariant.objects.get_or_create(
                                product=product, size=sz, color="Original Gold",
                                defaults={'sku': f"{product.sku}-{sz}", 'stock': st_num}
                            )
                            var.stock = st_num
                            var.sku = f"{product.sku}-{sz}"
                            var.save()
                        else:
                            ProductVariant.objects.filter(product=product, size=sz).delete()

                    messages.success(request, f"Product '{name}' and size specifications updated successfully.")
                    logger.info(f"DATABASE UPDATE SUCCESS — Product ID: {product.id}, Name: '{product.name}', SKU: '{product.sku}'")
                else:
                    product = Product.objects.create(
                        name=name, sku=sku, category=category,
                        base_price=base_price_val, sale_price=sale_price_val, shipping_charge=shipping_val,
                        collection=collection, description=desc, fabric_details=fabric, care_instructions=care,
                        is_featured=is_featured, is_seasonal=is_seasonal, is_cicada_wear=is_cicada_wear
                    )
                    if not product.pk:
                        raise ValueError(f"Failed to obtain primary key for product '{name}'. Database insert failed.")

                    for sz in all_possible_sizes:
                        if sz in selected_sizes:
                            stock_val = request.POST.get(f'stock_{sz}', 5)
                            try:
                                st_num = int(stock_val) if stock_val is not None and str(stock_val).strip() != '' else 5
                                if st_num < 0:
                                    st_num = 5
                            except ValueError:
                                st_num = 5
                            ProductVariant.objects.create(
                                product=product, size=sz, color="Original Gold", stock=st_num, sku=f"{product.sku}-{sz}"
                            )
                    messages.success(request, f"Product '{name}' created successfully.")
                    logger.info(f"DATABASE CREATE SUCCESS — Product ID: {product.id}, Name: '{product.name}', SKU: '{product.sku}', Slug: '{product.slug}'")
                    
                images = request.FILES.getlist('images')
                for i, img in enumerate(images):
                    try:
                        from PIL import Image, ImageOps
                        import io
                        from django.core.files.base import ContentFile
                        import os
                        
                        img_io = io.BytesIO()
                        with Image.open(img) as pil_img:
                            if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
                                background = Image.new('RGB', pil_img.size, (255, 255, 255))
                                background.paste(pil_img, mask=pil_img.convert('RGBA').split()[3])
                                pil_img = background
                            elif pil_img.mode != 'RGB':
                                pil_img = pil_img.convert('RGB')
                            
                            resized_img = ImageOps.fit(pil_img, (800, 880), Image.Resampling.LANCZOS)
                            resized_img.save(img_io, format='JPEG', quality=85)
                        
                        base_name, _ = os.path.splitext(img.name)
                        new_name = f"{base_name}.jpg"
                        processed_img = ContentFile(img_io.getvalue(), name=new_name)
                    except Exception as img_err:
                        logger.warning(f"IMAGE PROCESSING WARNING — Could not standardize image '{img.name}': {str(img_err)}")
                        processed_img = img
                        
                    ProductImage.objects.create(
                        product=product,
                        image=processed_img,
                        is_primary=(i == 0 and not product.images.filter(is_primary=True).exists())
                    )
                    logger.info(f"IMAGE SAVED — Product ID: {product.id}, Image File: '{img.name}'")
        except Exception as e:
            logger.error(f"DATABASE TRANSACTION ERROR — Could not save product '{name}': {str(e)}", exc_info=True)
            messages.error(request, f"Database Error: Could not save product '{name}'. Details: {str(e)}")
            return redirect('dashboard_products')
            
        return redirect('dashboard_products')
        
    return render(request, 'store/dashboard/products.html', {
        'products': products,
        'categories': categories,
        'collections': Product.COLLECTION_CHOICES,
        'size_choices': ['S', 'M', 'L', 'XL', 'XXL', '3XL'],
    })

@staff_required
@require_POST
def dashboard_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product.delete()
    messages.success(request, f"Product '{product_name}' was successfully deleted.")
    return redirect('dashboard_products')

@staff_required
def dashboard_inventory(request):
    variants = ProductVariant.objects.all().select_related('product').order_by('product__name')
    restock_history = RestockHistory.objects.all().select_related('variant', 'variant__product', 'restocked_by')[:15]
    
    out_of_stock = ProductVariant.objects.filter(stock=0).count()
    low_stock = ProductVariant.objects.filter(stock__lte=5, stock__gt=0).count()
    
    return render(request, 'store/dashboard/inventory.html', {
        'variants': variants,
        'restock_history': restock_history,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
    })

@staff_required
@require_POST
def dashboard_restock(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    action = request.POST.get('action', 'add')
    
    if action == 'stock_out':
        variant.stock = 0
        variant.save()
        msg_text = "Marked Out of Stock!"
    elif action == 'set':
        set_stock = int(request.POST.get('set_stock', 0))
        variant.stock = max(0, set_stock)
        variant.save()
        msg_text = f"Set stock to {variant.stock}!"
    else:
        qty = int(request.POST.get('quantity', 0))
        if qty > 0:
            variant.stock += qty
            variant.save()
            RestockHistory.objects.create(
                variant=variant,
                quantity_added=qty,
                restocked_by=request.user
            )
            msg_text = f"Added {qty} units!"
        else:
            msg_text = "No stock change"
            
    if request.headers.get('HX-Request'):
        low_stock_badge = ""
        if variant.stock == 0:
            low_stock_badge = '<span class="badge bg-danger ms-1">Sold Out</span>'
        elif variant.stock <= 5:
            low_stock_badge = '<span class="badge bg-warning text-dark ms-1">Low Stock</span>'
             
        html = f"""
        <div hx-swap-oob="true" id="variant-stock-display-{variant_id}">
             {variant.stock}{low_stock_badge}
        </div>
        <div class="alert alert-success py-1 px-2 mb-0 mt-1" style="font-size:0.8rem;" id="restock-toast-{variant_id}">
             {msg_text}
             <script>
                 setTimeout(() => {{
                     document.getElementById('restock-toast-{variant_id}')?.remove();
                 }}, 2000);
             </script>
        </div>
        """
        return HttpResponse(html)
        
    messages.success(request, f"Updated stock for {variant.product.name} ({variant.size}).")
    return redirect('dashboard_inventory')

@staff_required
def dashboard_customers(request):
    query = request.GET.get('q', '')
    
    customers = CustomerProfile.objects.select_related('user').annotate(
        orders_count=Count('user__orders', distinct=True)
    )
    
    if query:
        customers = customers.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(phone__icontains=query)
        )
        
    return render(request, 'store/dashboard/customers.html', {
        'customers': customers,
        'query': query,
    })

@staff_required
def dashboard_customer_detail(request, profile_id):
    profile = get_object_or_404(CustomerProfile, id=profile_id)
    orders = Order.objects.filter(user=profile.user).order_by('-order_date')
    wishlist_items = Wishlist.objects.filter(user=profile.user).select_related('product')
    
    total_spending = sum(o.total_amount for o in orders if o.status in ['Confirmed', 'Packed', 'Shipped', 'Delivered'])
    
    timeline = []
    timeline.append({
        'date': profile.user.date_joined,
        'icon': 'fa-user-plus bg-info text-white',
        'title': 'Account Registered',
        'desc': f"Customer '{profile.user.username}' created an account on the site."
    })
    
    for order in orders:
        timeline.append({
            'date': order.order_date,
            'icon': 'fa-bag-shopping bg-primary text-white',
            'title': f"Placed Order #CR-{order.id}",
            'desc': f"Placed order inquiry for ₹{order.total_amount:,.2f} with status '{order.status}'."
        })
        
    for w in wishlist_items:
        timeline.append({
            'date': w.created_at,
            'icon': 'fa-heart bg-danger text-white',
            'title': f"Saved '{w.product.name}'",
            'desc': f"Added product design code '{w.product.sku}' to their wishlist."
        })
        
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, 'store/dashboard/customer_detail.html', {
        'profile': profile,
        'orders': orders,
        'wishlist_items': wishlist_items,
        'total_spending': total_spending,
        'timeline': timeline,
    })

@staff_required
def dashboard_reviews(request):
    reviews = Review.objects.all().select_related('product', 'user').order_by('-created_at')
    return render(request, 'store/dashboard/reviews.html', {
        'reviews': reviews,
    })

@staff_required
@require_POST
def dashboard_moderate_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    action = request.POST.get('action')
    
    if action == 'approve':
        review.is_approved = True
        review.save()
    elif action == 'feature':
        review.is_featured = not review.is_featured
        review.save()
    elif action == 'reject':
        review.is_approved = False
        review.save()
    elif action == 'delete':
        review.delete()
        
    if request.headers.get('HX-Request'):
        if action == 'delete':
            return HttpResponse("")
            
        btn_class = "btn-warning" if review.is_featured else "btn-outline-warning"
        btn_text = "Featured" if review.is_featured else "Feature"
        
        html = f"""
        <span class="badge bg-{"success" if review.is_approved else "secondary"}" id="review-status-badge-{review_id}">
            {"Approved" if review.is_approved else "Pending"}
        </span>
        <button hx-swap-oob="true" id="feature-btn-{review_id}" class="btn btn-xs {btn_class}" hx-post="/dashboard/moderate-review/{review_id}/" hx-vals='{{"action": "feature"}}'>
            {btn_text}
        </button>
        """
        return HttpResponse(html)
        
    messages.success(request, f"Review status updated.")
    return redirect('dashboard_reviews')

@staff_required
def dashboard_content(request):
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
        
    if request.method == 'POST':
        brand_settings.whatsapp_number = request.POST.get('whatsapp_number')
        brand_settings.bank_holder = request.POST.get('bank_holder')
        brand_settings.bank_account = request.POST.get('bank_account')
        brand_settings.bank_ifsc = request.POST.get('bank_ifsc')
        brand_settings.bank_branch = request.POST.get('bank_branch')
        
        brand_settings.hero_title = request.POST.get('hero_title')
        brand_settings.hero_subtitle = request.POST.get('hero_subtitle')
        brand_settings.about_title = request.POST.get('about_title')
        brand_settings.about_text = request.POST.get('about_text')
        
        # Shipping validation and save
        shipping_charge = request.POST.get('shipping_charge')
        shipping_enabled = request.POST.get('shipping_enabled') in ('on', 'true')
        try:
            shipping_val = Decimal(shipping_charge)
            if shipping_val < 0:
                messages.error(request, "Shipping charge cannot be negative.")
                return redirect('dashboard_content')
            brand_settings.shipping_charge = shipping_val
            brand_settings.shipping_enabled = shipping_enabled
        except (ValueError, TypeError):
            messages.error(request, "Invalid shipping charge input.")
            return redirect('dashboard_content')
            
        brand_settings.save()
        messages.success(request, "Brand, Homepage, and Shipping Settings updated successfully.")
        return redirect('dashboard_content')
        
    return render(request, 'store/dashboard/content.html', {
        'brand_settings': brand_settings,
    })

@staff_required
@require_POST
def dashboard_toggle_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_active = not category.is_active
    category.save()
    
    btn_class = "btn-success" if category.is_active else "btn-secondary"
    btn_text = "Active" if category.is_active else "Inactive"
    
    html = f"""
    <button class="btn btn-sm {btn_class}" 
            hx-post="/dashboard/toggle-category/{category_id}/" 
            hx-target="this" 
            hx-swap="outerHTML"
            id="toggle-category-btn-{category_id}">
        {btn_text}
    </button>
    """
    return HttpResponse(html)

@staff_required
@require_POST
def dashboard_set_primary_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    product = image.product
    ProductImage.objects.filter(product=product).update(is_primary=False)
    image.is_primary = True
    image.save()
    logger.info(f"SET PRIMARY IMAGE — Image ID: {image.id}, Product ID: {product.id}, Product: '{product.name}'")
    messages.success(request, f"Primary image updated for product '{product.name}'.")
    return redirect('dashboard_products')

@staff_required
@require_POST
def dashboard_delete_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    product = image.product
    was_primary = image.is_primary
    if image.image:
        try:
            image.image.delete(save=False)
        except Exception as e:
            logger.warning(f"Failed to delete image file from storage: {str(e)}")
    image.delete()
    
    if was_primary:
        next_image = product.images.first()
        if next_image:
            next_image.is_primary = True
            next_image.save()
            
    logger.info(f"DELETE IMAGE — Image ID: {image_id}, Product ID: {product.id}, Product: '{product.name}'")
    messages.success(request, f"Image removed from product '{product.name}'.")
    return redirect('dashboard_products')
