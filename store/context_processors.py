from .models import Cart, Wishlist

def cart_and_wishlist(request):
    if request.user.is_authenticated:
        # Get or create cart to avoid errors
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.items_count
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    else:
        cart_count = 0
        wishlist_count = 0
        
    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count
    }
