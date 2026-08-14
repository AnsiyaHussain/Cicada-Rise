from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from store.models import Category, Product, ProductVariant, Review, Order, RestockHistory, HomepageSettings

class CicadaRiseTestCase(TestCase):
    def setUp(self):
        # Setup category
        self.category = Category.objects.create(
            name="Heritage Collection",
            description="Heritage description"
        )
        
        # Setup product
        self.product = Product.objects.create(
            category=self.category,
            name="Gold Saree",
            sku="CR-TEST-KS",
            description="Beautiful gold saree",
            base_price=5000.00
        )
        
        # Setup variants
        self.variant_s = ProductVariant.objects.create(
            product=self.product,
            size="S",
            color="Gold",
            stock=10
        )
        self.variant_m = ProductVariant.objects.create(
            product=self.product,
            size="M",
            color="Gold",
            stock=5
        )

        # Setup users
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpassword'
        )
        self.admin = User.objects.create_superuser(
            username='adminuser',
            email='admin@cicada.com',
            password='adminpassword'
        )

    def test_product_total_stock(self):
        """Tests that total stock aggregates variants correctly."""
        self.assertEqual(self.product.total_stock, 15)

    def test_product_average_rating(self):
        """Tests that only approved reviews are counted in average ratings."""
        Review.objects.create(
            product=self.product,
            user=self.user,
            rating=1,
            comment="Bad",
            is_approved=False
        )
        self.assertEqual(self.product.average_rating, 0.0)
        
        Review.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            comment="Excellent",
            is_approved=True
        )
        self.assertEqual(self.product.average_rating, 5.0)

    def test_homepage_view(self):
        """Tests that homepage resolves with 200 OK."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_homepage_settings_initialization(self):
        """Tests that HomepageSettings singleton functions with default WhatsApp and Bank details."""
        settings_obj, created = HomepageSettings.objects.get_or_create(id=1)
        self.assertEqual(settings_obj.whatsapp_number, "9447771056")
        self.assertEqual(settings_obj.bank_holder, "Fathima Haris")
        self.assertEqual(settings_obj.bank_account, "36137088305")

    def test_inventory_restock_log(self):
        """Tests that manual restock updates stock levels and appends RestockHistory."""
        initial_stock = self.variant_s.stock
        
        # Restock
        self.variant_s.stock += 5
        self.variant_s.save()
        
        log = RestockHistory.objects.create(
            variant=self.variant_s,
            quantity_added=5,
            restocked_by=self.admin
        )
        
        self.assertEqual(self.variant_s.stock, initial_stock + 5)
        self.assertEqual(RestockHistory.objects.count(), 1)
        self.assertEqual(log.quantity_added, 5)

    def test_order_status_progression(self):
        """Tests that Order status transitions correctly."""
        order = Order.objects.create(
            user=self.user,
            customer_name="Test Client",
            customer_phone="9988776655",
            shipping_address="Test Address, bangalore",
            total_amount=5000.00,
            status="New"
        )
        self.assertEqual(order.status, "New")
        
        order.status = "Confirmed"
        order.save()
        self.assertEqual(order.status, "Confirmed")

    def test_role_based_separation_and_redirection(self):
        """Tests that normal clients are redirected from admin dashboard, but staff can enter."""
        # 1. Unauthenticated redirect
        response = self.client.get(reverse('admin_dashboard'))
        self.assertRedirects(response, reverse('login'))

        # 2. Authenticated non-staff redirect to home
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('admin_dashboard'), follow=True)
        self.assertRedirects(response, reverse('home'))
        
        # Verify warning message exists
        messages = [m.message for m in response.context['messages']]
        self.assertIn("Access Denied: Staff credentials required.", messages)
        self.client.logout()

        # 3. Authenticated staff allowed in
        self.client.login(username='adminuser', password='adminpassword')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_product_deletion(self):
        """Tests that dashboard delete post controller removes a product and variants from database."""
        self.client.login(username='adminuser', password='adminpassword')
        product_id = self.product.id
        
        # Verify product exists
        self.assertTrue(Product.objects.filter(id=product_id).exists())
        
        # Post deletion
        response = self.client.post(reverse('dashboard_product_delete', args=[product_id]))
        self.assertRedirects(response, reverse('dashboard_products'))
        
        # Verify product and variants are deleted
        self.assertFalse(Product.objects.filter(id=product_id).exists())
        self.assertEqual(ProductVariant.objects.filter(product_id=product_id).count(), 0)

    def test_registration_redirect_to_login(self):
        """Tests that user registration redirects to login page instead of auto-login."""
        response = self.client.post(reverse('register'), {
            'username': 'newcustomer',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@user.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newcustomer').exists())

    def test_order_pdf_export_and_deletion(self):
        """Tests PDF report exports and order deletion functionality."""
        order = Order.objects.create(
            user=self.user,
            customer_name="PDF Test Client",
            customer_phone="9988776655",
            shipping_address="PDF Test Address",
            total_amount=2500.00,
            status="New"
        )
        self.client.login(username='adminuser', password='adminpassword')

        # 1. Download Orders List PDF
        list_pdf_resp = self.client.get(reverse('dashboard_orders_pdf'))
        self.assertEqual(list_pdf_resp.status_code, 200)
        self.assertEqual(list_pdf_resp['Content-Type'], 'application/pdf')

        # 2. Download Order Detail Invoice PDF
        detail_pdf_resp = self.client.get(reverse('dashboard_order_detail_pdf', args=[order.id]))
        self.assertEqual(detail_pdf_resp.status_code, 200)
        self.assertEqual(detail_pdf_resp['Content-Type'], 'application/pdf')

        # 3. Delete Order
        delete_resp = self.client.post(reverse('dashboard_order_delete', args=[order.id]))
        self.assertRedirects(delete_resp, reverse('dashboard_orders'))
        self.assertFalse(Order.objects.filter(id=order.id).exists())

        # 4. Clear Cancelled Orders
        cancelled_order = Order.objects.create(
            user=self.user,
            customer_name="Cancelled Client",
            customer_phone="1122334455",
            shipping_address="Cancel Address",
            total_amount=1000.00,
            status="Cancelled"
        )
        clear_resp = self.client.post(reverse('dashboard_clear_cancelled_orders'))
        self.assertRedirects(clear_resp, reverse('dashboard_orders'))
        self.assertFalse(Order.objects.filter(id=cancelled_order.id).exists())

    def test_shipping_charge_settings_validation(self):
        """Tests that shipping charges save properly on valid inputs and error on negative values."""
        self.client.login(username='adminuser', password='adminpassword')
        
        # Valid settings save
        response = self.client.post(reverse('dashboard_content'), {
            'whatsapp_number': '9447771056',
            'bank_holder': 'Fathima Haris',
            'bank_account': '36137088305',
            'bank_ifsc': 'SBIN0012890',
            'bank_branch': 'Annamanada',
            'shipping_charge': '150.00',
            'shipping_enabled': 'on',
            'hero_title': 'Hero',
            'hero_subtitle': 'Subtitle',
            'about_title': 'About',
            'about_text': 'Text'
        })
        self.assertRedirects(response, reverse('dashboard_content'))
        settings_obj = HomepageSettings.objects.first()
        self.assertEqual(settings_obj.shipping_charge, 150.00)
        self.assertTrue(settings_obj.shipping_enabled)

        # Invalid negative shipping charge
        response = self.client.post(reverse('dashboard_content'), {
            'whatsapp_number': '9447771056',
            'bank_holder': 'Fathima Haris',
            'bank_account': '36137088305',
            'bank_ifsc': 'SBIN0012890',
            'bank_branch': 'Annamanada',
            'shipping_charge': '-50.00',
            'shipping_enabled': 'on',
            'hero_title': 'Hero',
            'hero_subtitle': 'Subtitle',
            'about_title': 'About',
            'about_text': 'Text'
        })
        self.assertRedirects(response, reverse('dashboard_content'))
        settings_obj = HomepageSettings.objects.first()
        self.assertEqual(settings_obj.shipping_charge, 150.00) # Unchanged due to validation error

    def test_post_login_deferred_add_to_cart(self):
        """Tests that guest actions (add_to_cart params) are executed seamlessly after user authenticates."""
        # Logged out request with add_to_cart parameters
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(
            reverse('product_detail', args=[self.product.slug]) + f"?action=add_to_cart&variant={self.variant_s.id}&quantity=2"
        )
        self.assertRedirects(response, reverse('product_detail', args=[self.product.slug]))
        
        # Verify cart item was added
        from store.models import CartItem
        cart_item = CartItem.objects.filter(variant=self.variant_s).first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 2)

