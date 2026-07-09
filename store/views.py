import urllib.parse
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Avg, Count
from django.conf import settings
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User

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
    featured_products = Product.objects.filter(is_featured=True)[:4]
    seasonal_products = Product.objects.filter(is_seasonal=True)[:4]
    cicada_products = Product.objects.filter(is_cicada_wear=True)[:4]
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

    products = Product.objects.all()

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
    products = Product.objects.filter(is_seasonal=True)
    return render(request, 'store/seasonal_wears.html', {'products': products})

def cicada_wears(request):
    products = Product.objects.filter(is_cicada_wear=True)
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
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
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
    return render(request, 'store/cart.html', {'cart': cart})

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
        html = f"""
        <div id="cart-item-qty-{item_id}" hx-swap-oob="true">{cart_item.quantity if cart_item.id and cart_item.quantity else 0}</div>
        <div id="cart-item-subtotal-{item_id}" hx-swap-oob="true">₹{cart_item.subtotal:,.2f}</div>
        <div id="cart-total-price" hx-swap-oob="true">₹{cart.total_price:,.2f}</div>
        <div id="cart-total-price-summary" hx-swap-oob="true">₹{cart.total_price:,.2f}</div>
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
@require_POST
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variant_id = request.POST.get('variant')
    quantity = int(request.POST.get('quantity', 1))
    
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
        
    # Decrement stock
    variant.stock -= quantity
    variant.save()
    
    # Create Order record
    order = Order.objects.create(
        user=request.user,
        customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        customer_phone=profile.phone,
        shipping_address=f"{profile.address}, {profile.city}, {profile.state} - {profile.pin_code}",
        total_amount=variant.price * quantity,
        status='New'
    )
    
    OrderItem.objects.create(
        order=order,
        product=product,
        variant=variant,
        quantity=quantity,
        price=variant.price
    )
    
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
        
    whatsapp_phone = format_whatsapp_number(brand_settings.whatsapp_number)
    customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    
    msg_template = (
        "Hello Cicada Rise! I would like to place an order:\n\n"
        "✨ *ORDER DETAILS* ✨\n"
        "• *Product Name*: {prod_name}\n"
        "• *Product Code (SKU)*: {prod_sku}\n"
        "• *Size*: {size}\n"
        "• *Color*: {color}\n"
        "• *Quantity*: {qty}\n"
        "• *Total Value*: ₹{price:,.2f}\n\n"
        "👤 *CUSTOMER DETAILS*\n"
        "• *Name*: {cust_name}\n"
        "• *Phone*: {cust_phone}\n"
        "• *Shipping*: {cust_addr}\n\n"
        "🏦 *DIRECT BANK TRANSFER DETAILS* 🏦\n"
        "• *Bank*: SBI\n"
        "• *Account Holder*: {bank_holder}\n"
        "• *Account Number*: {bank_acc}\n"
        "• *IFSC Code*: {bank_ifsc}\n"
        "• *Branch*: {bank_branch}\n\n"
        "*Please complete the bank transfer of ₹{price:,.2f} and share the transaction snapshot here to confirm your order.*"
    )
    
    msg = msg_template.format(
        prod_name=product.name,
        prod_sku=product.sku,
        size=variant.size,
        color=variant.color,
        qty=quantity,
        price=variant.price * quantity,
        cust_name=customer_name,
        cust_phone=profile.phone,
        cust_addr=f"{profile.city}, {profile.state}",
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
            
    order = Order.objects.create(
        user=request.user,
        customer_name=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
        customer_phone=profile.phone,
        shipping_address=f"{profile.address}, {profile.city}, {profile.state} - {profile.pin_code}",
        total_amount=cart.total_price,
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
        if item.variant:
            item.variant.stock -= item.quantity
            item.variant.save()
            
        items_summary.append(
            f"• *{item.product.name}* ({item.variant.size if item.variant else 'N/A'}/{item.variant.color if item.variant else 'N/A'})\n"
            f"  Code: {item.product.sku} | Qty: {item.quantity} | Subtotal: ₹{item.subtotal:,.2f}"
        )
        
    summary_text = "\n".join(items_summary)
    
    brand_settings = HomepageSettings.objects.first()
    if not brand_settings:
        brand_settings = HomepageSettings.objects.create()
        
    whatsapp_phone = format_whatsapp_number(brand_settings.whatsapp_number)
    customer_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    
    msg_template = (
        "Hello Cicada Rise! I would like to place a Cart Order:\n\n"
        "✨ *ORDER DETAILS* ✨\n"
        "{summary}\n\n"
        "⭐ *ORDER TOTAL*: ₹{total:,.2f}\n\n"
        "👤 *CUSTOMER DETAILS*\n"
        "• *Name*: {cust_name}\n"
        "• *Phone*: {cust_phone}\n"
        "• *Shipping*: {cust_addr}\n\n"
        "🏦 *DIRECT BANK TRANSFER DETAILS* 🏦\n"
        "• *Bank*: SBI\n"
        "• *Account Holder*: {bank_holder}\n"
        "• *Account Number*: {bank_acc}\n"
        "• *IFSC Code*: {bank_ifsc}\n"
        "• *Branch*: {bank_branch}\n\n"
        "*Please complete the bank transfer of ₹{total:,.2f} and share the transaction snapshot here to confirm your order.*"
    )
    
    msg = msg_template.format(
        summary=summary_text,
        total=cart.total_price,
        cust_name=customer_name,
        cust_phone=profile.phone,
        cust_addr=f"{profile.city}, {profile.state}",
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
            
    return render(request, 'store/login.html')

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
            
            login(request, user)
            Cart.objects.create(user=user)
            messages.success(request, "Registration successful! Welcome to Cicada Rise.")
            return redirect('home')
            
    return render(request, 'store/register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

@login_required
def profile_view(request):
    user_form = UserProfileForm(instance=request.user)
    profile_form = CustomerProfileForm(instance=request.user.profile)
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = CustomerProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profile')
            
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
    
    orders = Order.objects.filter(status__in=['New', 'Pending'])
    
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
def dashboard_products(request):
    products = Product.objects.all().prefetch_related('variants', 'images')
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        cat_id = request.POST.get('category')
        price = request.POST.get('base_price')
        sale_price = request.POST.get('sale_price') or None
        collection = request.POST.get('collection')
        desc = request.POST.get('description')
        fabric = request.POST.get('fabric_details')
        care = request.POST.get('care_instructions')
        
        is_featured = 'is_featured' in request.POST
        is_seasonal = 'is_seasonal' in request.POST
        is_cicada_wear = 'is_cicada_wear' in request.POST
        
        category = get_object_or_404(Category, id=cat_id)
        
        if product_id:
            product = get_object_or_404(Product, id=product_id)
            product.name = name
            product.sku = sku
            product.category = category
            product.base_price = price
            product.sale_price = sale_price
            product.collection = collection
            product.description = desc
            product.fabric_details = fabric
            product.care_instructions = care
            product.is_featured = is_featured
            product.is_seasonal = is_seasonal
            product.is_cicada_wear = is_cicada_wear
            product.save()
            messages.success(request, f"Product '{name}' updated successfully.")
        else:
            initial_stock = int(request.POST.get('initial_stock', 5) or 0)
            product = Product.objects.create(
                name=name, sku=sku, category=category,
                base_price=price, sale_price=sale_price, collection=collection,
                description=desc, fabric_details=fabric, care_instructions=care,
                is_featured=is_featured, is_seasonal=is_seasonal, is_cicada_wear=is_cicada_wear
            )
            for size in ['S', 'M', 'L', 'XL']:
                ProductVariant.objects.create(
                    product=product, size=size, color="Original Gold", stock=initial_stock
                )
            messages.success(request, f"New product '{name}' created successfully with initial stock of {initial_stock} per size.")
            
        images = request.FILES.getlist('images')
        for i, img in enumerate(images):
            ProductImage.objects.create(
                product=product,
                image=img,
                is_primary=(i == 0 and not product.images.filter(is_primary=True).exists())
            )
            
        return redirect('dashboard_products')
        
    return render(request, 'store/dashboard/products.html', {
        'products': products,
        'categories': categories,
        'collections': Product.COLLECTION_CHOICES,
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
    qty = int(request.POST.get('quantity', 0))
    if qty > 0:
        variant.stock += qty
        variant.save()
        
        RestockHistory.objects.create(
            variant=variant,
            quantity_added=qty,
            restocked_by=request.user
        )
        
    if request.headers.get('HX-Request'):
        low_stock_badge = ""
        if variant.stock <= 5:
             low_stock_badge = '<span class="badge bg-danger ms-1">Low Stock</span>'
             
        html = f"""
        <div hx-swap-oob="true" id="variant-stock-display-{variant_id}">
             {variant.stock}{low_stock_badge}
        </div>
        <div class="alert alert-success py-1 px-2 mb-0 mt-1" style="font-size:0.8rem;" id="restock-toast-{variant_id}">
             Added {qty} units!
             <script>
                 setTimeout(() => {{
                     document.getElementById('restock-toast-{variant_id}').remove();
                 }}, 2000);
             </script>
        </div>
        """
        return HttpResponse(html)
        
    messages.success(request, f"Restocked {qty} units successfully.")
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
        
        brand_settings.save()
        messages.success(request, "Brand and Homepage Settings updated successfully.")
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
