from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('seasonal-wears/', views.seasonal_wears, name='seasonal_wears'),
    path('cicada-wears/', views.cicada_wears, name='cicada_wears'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    
    # Wishlist & Cart
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # WhatsApp Buy Now / Checkout
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('cart/checkout/', views.checkout_cart, name='checkout_cart'),
    
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('auth/google-login/', views.google_login_verify, name='google_login_verify'),
    
    # Custom Premium ERP Admin Dashboard
    path('dashboard/', views.dashboard_overview, name='admin_dashboard'),
    path('dashboard/profile/', views.dashboard_admin_profile, name='dashboard_admin_profile'),
    path('dashboard/profile/change-password/', views.dashboard_change_password, name='dashboard_change_password'),
    path('dashboard/contacted-users/', views.dashboard_contacted_users, name='dashboard_contacted_users'),
    path('dashboard/contacted-users/update-status/<int:contact_id>/', views.dashboard_update_contact_status, name='dashboard_update_contact_status'),
    path('dashboard/orders/', views.dashboard_orders, name='dashboard_orders'),
    path('dashboard/orders/pdf/', views.export_orders_pdf, name='dashboard_orders_pdf'),
    path('dashboard/orders/whatsapp/', views.dashboard_whatsapp_orders, name='dashboard_whatsapp_orders'),
    path('dashboard/orders/<int:order_id>/', views.dashboard_order_detail, name='dashboard_order_detail'),
    path('dashboard/orders/<int:order_id>/pdf/', views.export_order_detail_pdf, name='dashboard_order_detail_pdf'),
    path('dashboard/orders/delete/<int:order_id>/', views.dashboard_order_delete, name='dashboard_order_delete'),
    path('dashboard/orders/clear-cancelled/', views.dashboard_clear_cancelled_orders, name='dashboard_clear_cancelled_orders'),
    path('dashboard/orders/update-status/<int:order_id>/', views.dashboard_update_order_status, name='dashboard_update_order_status'),
    path('dashboard/products/', views.dashboard_products, name='dashboard_products'),
    path('dashboard/products/delete/<int:product_id>/', views.dashboard_product_delete, name='dashboard_product_delete'),
    path('dashboard/products/image/primary/<int:image_id>/', views.dashboard_set_primary_image, name='dashboard_set_primary_image'),
    path('dashboard/products/image/delete/<int:image_id>/', views.dashboard_delete_image, name='dashboard_delete_image'),
    path('dashboard/inventory/', views.dashboard_inventory, name='dashboard_inventory'),
    path('dashboard/inventory/restock/<int:variant_id>/', views.dashboard_restock, name='dashboard_restock'),
    path('dashboard/customers/', views.dashboard_customers, name='dashboard_customers'),
    path('dashboard/customers/<int:profile_id>/', views.dashboard_customer_detail, name='dashboard_customer_detail'),
    path('dashboard/reviews/', views.dashboard_reviews, name='dashboard_reviews'),
    path('dashboard/moderate-review/<int:review_id>/', views.dashboard_moderate_review, name='dashboard_moderate_review'),
    path('dashboard/toggle-category/<int:category_id>/', views.dashboard_toggle_category, name='dashboard_toggle_category'),
    path('dashboard/content/', views.dashboard_content, name='dashboard_content'),
]
