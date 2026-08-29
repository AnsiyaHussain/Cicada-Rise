from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from store.models import Category, Product, ProductVariant, ProductImage, Review, Order, RestockHistory, HomepageSettings

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

    def test_admin_changing_product_shipping_charge(self):
        """1. Tests admin changing a product's shipping charge."""
        self.client.login(username='adminuser', password='adminpassword')
        response = self.client.post(reverse('dashboard_products'), {
            'product_id': self.product.id,
            'name': self.product.name,
            'sku': self.product.sku,
            'category': self.category.id,
            'base_price': '5000.00',
            'shipping_charge': '120.00',
            'collection': 'Cicada Signature',
            'description': 'Updated desc',
            'sizes': ['S'],
            'stock_S': '10'
        })
        self.assertRedirects(response, reverse('dashboard_products'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.shipping_charge, 120.00)

    def test_correct_shipping_appearing_in_checkout(self):
        """2. Tests correct shipping appearing in checkout."""
        from decimal import Decimal
        self.product.shipping_charge = Decimal('90.00')
        self.product.save()

        # Fill profile for user
        profile = self.user.profile
        profile.phone = "9447771056"
        profile.address = "123 Main St"
        profile.city = "Bangalore"
        profile.state = "Karnataka"
        profile.pin_code = "560001"
        profile.save()

        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('buy_now', args=[self.product.id]), {
            'variant_id': self.variant_s.id,
            'quantity': 1
        })
        self.assertEqual(response.status_code, 302)
        latest_order = Order.objects.latest('id')
        self.assertEqual(latest_order.shipping_charge, Decimal('90.00'))
        self.assertEqual(latest_order.total_amount, Decimal('5090.00'))

    def test_client_side_shipping_price_tampering_ignored(self):
        """3. Tests client-side shipping-price tampering being ignored."""
        from decimal import Decimal
        self.product.base_price = Decimal('3000.00')
        self.product.shipping_charge = Decimal('70.00')
        self.product.save()

        profile = self.user.profile
        profile.phone = "9447771056"
        profile.address = "123 Main St"
        profile.save()

        self.client.login(username='testuser', password='testpassword')
        # Attempt to tamper with price and shipping in POST payload
        response = self.client.post(reverse('buy_now', args=[self.product.id]), {
            'variant_id': self.variant_s.id,
            'quantity': 1,
            'price': '1.00',
            'shipping_charge': '0.00'
        })
        self.assertEqual(response.status_code, 302)
        latest_order = Order.objects.latest('id')
        # Server must use DB values (3000.00 + 70.00)
        self.assertEqual(latest_order.shipping_charge, Decimal('70.00'))
        self.assertEqual(latest_order.total_amount, Decimal('3070.00'))

    def test_multiple_products_shipping_calculation(self):
        """4. Tests multiple distinct products in cart combined shipping."""
        from decimal import Decimal
        from store.models import Cart, CartItem

        self.product.shipping_charge = Decimal('70.00')
        self.product.save()

        product2 = Product.objects.create(
            category=self.category,
            name="Silk Kurta",
            sku="CR-TEST-SK",
            description="Silk Kurta desc",
            base_price=2000.00,
            shipping_charge=Decimal('50.00')
        )
        variant2 = ProductVariant.objects.create(product=product2, size="M", color="Red", stock=5)

        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, variant=self.variant_s, quantity=1)
        CartItem.objects.create(cart=cart, product=product2, variant=variant2, quantity=1)

        # Total shipping should be 70 + 50 = 120.00
        self.assertEqual(cart.shipping_charge, Decimal('120.00'))

    def test_product_quantity_greater_than_one(self):
        """5. Tests product quantity > 1 does not multiply shipping charge."""
        from decimal import Decimal
        from store.models import Cart, CartItem

        self.product.shipping_charge = Decimal('80.00')
        self.product.save()

        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, variant=self.variant_s, quantity=3)

        # Shipping charge for qty 3 of same product remains base rate 80.00
        self.assertEqual(cart.shipping_charge, Decimal('80.00'))

    def test_historical_orders_retaining_original_shipping(self):
        """6. Tests historical orders retaining their original shipping charge after product updates."""
        from decimal import Decimal
        order = Order.objects.create(
            user=self.user,
            customer_name="Historical Order Client",
            customer_phone="9447771056",
            shipping_address="Test Address",
            shipping_charge=Decimal('70.00'),
            total_amount=Decimal('5070.00'),
            status="Confirmed"
        )
        # Admin updates product shipping charge later
        self.product.shipping_charge = Decimal('150.00')
        self.product.save()

        # Past order must retain 70.00
        order.refresh_from_db()
        self.assertEqual(order.shipping_charge, Decimal('70.00'))
        self.assertEqual(order.total_amount, Decimal('5070.00'))

    def test_product_creation_and_persistence(self):
        """Tests product creation via dashboard POST and persistence in PostgreSQL."""
        self.client.login(username='adminuser', password='adminpassword')
        response = self.client.post(reverse('dashboard_products'), {
            'name': 'Cicada Test Product',
            'sku': 'CR-TEST-001',
            'category': self.category.id,
            'base_price': '1499.00',
            'sale_price': '1399.00',
            'shipping_charge': '90.00',
            'collection': 'Cicada Signature',
            'description': 'Luxury test garment',
            'fabric_details': 'Pure Silk',
            'care_instructions': 'Dry Clean',
            'sizes': ['S', 'M'],
            'stock_S': '10',
            'stock_M': '5'
        })
        self.assertRedirects(response, reverse('dashboard_products'))

        # Verify database-backed queryset
        prod = Product.objects.filter(sku='CR-TEST-001').first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.name, 'Cicada Test Product')
        self.assertEqual(prod.base_price, Decimal('1499.00'))
        self.assertEqual(prod.sale_price, Decimal('1399.00'))
        self.assertEqual(prod.shipping_charge, Decimal('90.00'))
        self.assertEqual(prod.total_stock, 15)

    def test_duplicate_sku_friendly_error(self):
        """Tests that submitting a duplicate SKU produces a friendly message without 500 error."""
        self.client.login(username='adminuser', password='adminpassword')
        response = self.client.post(reverse('dashboard_products'), {
            'name': 'Duplicate SKU Product',
            'sku': self.product.sku, # existing SKU
            'category': self.category.id,
            'base_price': '1000.00',
            'shipping_charge': '50.00',
            'sizes': ['S']
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = [m.message for m in response.context['messages']]
        self.assertTrue(any("already exists" in m for m in messages))

    def test_similar_names_unique_slugs(self):
        """Tests that products with identical names generate unique collision-proof slugs."""
        prod1 = Product.objects.create(category=self.category, name="Silk Kaftan", base_price=1000)
        prod2 = Product.objects.create(category=self.category, name="Silk Kaftan", base_price=1000)
        prod3 = Product.objects.create(category=self.category, name="Silk Kaftan", base_price=1000)

        self.assertEqual(prod1.slug, 'silk-kaftan')
        self.assertEqual(prod2.slug, 'silk-kaftan-1')
        self.assertEqual(prod3.slug, 'silk-kaftan-2')

    def test_invalid_price_and_shipping_handling(self):
        """Tests that negative or invalid price and shipping values return validation error redirects."""
        self.client.login(username='adminuser', password='adminpassword')
        
        # Negative base price
        resp = self.client.post(reverse('dashboard_products'), {
            'name': 'Invalid Price',
            'category': self.category.id,
            'base_price': '-500.00',
            'sizes': ['S']
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any("cannot be negative" in m.message for m in resp.context['messages']))

        # Negative shipping
        resp = self.client.post(reverse('dashboard_products'), {
            'name': 'Invalid Shipping',
            'category': self.category.id,
            'base_price': '500.00',
            'shipping_charge': '-20.00',
            'sizes': ['S']
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any("cannot be negative" in m.message for m in resp.context['messages']))

    def test_image_upload_handling(self):
        """Tests uploading an image during product creation."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='adminuser', password='adminpassword')
        
        # 1x1 8-bit GIF image
        gif_bytes = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00'
            b'\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        )
        dummy_img = SimpleUploadedFile('test_image.gif', gif_bytes, content_type='image/gif')

        response = self.client.post(reverse('dashboard_products'), {
            'name': 'Image Upload Product',
            'sku': 'CR-IMG-001',
            'category': self.category.id,
            'base_price': '2500.00',
            'shipping_charge': '70.00',
            'sizes': ['S'],
            'images': [dummy_img]
        })
        self.assertRedirects(response, reverse('dashboard_products'))

        prod = Product.objects.filter(sku='CR-IMG-001').first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.images.count(), 1)

    def test_dashboard_set_primary_image_and_delete_image(self):
        """Tests selecting a primary image and deleting an individual image from a product."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.login(username='adminuser', password='adminpassword')
        
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        img1_file = SimpleUploadedFile('img1.gif', gif_bytes, content_type='image/gif')
        img2_file = SimpleUploadedFile('img2.gif', gif_bytes, content_type='image/gif')

        prod = Product.objects.create(
            name="Multi Image Test Product",
            sku="CR-MULTI-001",
            category=self.category,
            base_price=Decimal("1500.00")
        )
        img1 = ProductImage.objects.create(product=prod, image=img1_file, is_primary=True)
        img2 = ProductImage.objects.create(product=prod, image=img2_file, is_primary=False)

        self.assertEqual(prod.images.count(), 2)
        self.assertTrue(img1.is_primary)
        self.assertFalse(img2.is_primary)

        # Test set primary image view
        resp = self.client.post(reverse('dashboard_set_primary_image', args=[img2.id]), follow=True)
        self.assertEqual(resp.status_code, 200)
        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_primary)
        self.assertTrue(img2.is_primary)
        self.assertEqual(prod.primary_image_url, img2.image.url)

        # Test delete image view
        resp_del = self.client.post(reverse('dashboard_delete_image', args=[img2.id]), follow=True)
        self.assertEqual(resp_del.status_code, 200)
        self.assertEqual(prod.images.count(), 1)
        img1.refresh_from_db()
        self.assertTrue(img1.is_primary)
        self.assertEqual(prod.primary_image_url, img1.image.url)



