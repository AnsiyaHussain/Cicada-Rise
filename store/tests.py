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
