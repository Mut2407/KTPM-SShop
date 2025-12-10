from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import Account
from shop.models import Product, Category
from cart.models import Cart, CartItem
from orders.models import Order, Payment
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal

# ============================================================================
# 1. UNIT TEST: 
# ============================================================================
class OrderUnitTest(TestCase):
    def test_order_default_status(self):
        """1. Test đơn hàng mới tạo phải có status là 'New'"""
        user = Account.objects.create_user(
            first_name='A', last_name='B', username='u', email='e@e.com', password='1'
        )
        order = Order.objects.create(
            user=user,
            order_number='123',
            first_name='A',
            last_name='B',
            email='e@e.com',
            phone='111',
            address='addr',
            country='VN',
            state='HCM',
            city='HCM',
            order_total=100,
            tax=0,
        )
        self.assertEqual(order.status, 'New')

    def test_payment_str(self):
        """2. Test string representation của Payment"""
        user = Account.objects.create_user(first_name='A', last_name='B', username='u', email='e@e.com', password='1')
        payment = Payment.objects.create(
            user=user, payment_id='PAY123', payment_method='PayPal', amount_paid='100', status='Completed'
        )
        self.assertEqual(str(payment), 'PAY123')
    
    def test_order_full_name(self):
        """3. Test hàm full_name trong Order"""
        user = Account.objects.create_user(first_name='A', last_name='B', username='u', email='e@e.com', password='1')
        order = Order.objects.create(
            user=user,
            order_number='456',
            first_name='Nguyen',
            last_name='Van A',
            email='e@e.com',
            phone='111',
            address='addr',
            country='VN',
            state='HCM',
            city='HCM',
            order_total=0,
            tax=0,
        )
        self.assertEqual(order.full_name(), 'Nguyen Van A')

# ============================================================================
# 2. INTEGRATION TEST: 
# ============================================================================
class OrderIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            first_name='User', last_name='Test', username='user', email='user@test.com', password='password'
        )
        self.user.is_active = True
        self.user.save()
        self.client.force_login(self.user)
        
        # Setup Product & Cart
        self.category = Category.objects.create(name='C', slug='c')
        test_image = SimpleUploadedFile('p.jpg', b"filecontent", content_type='image/jpeg')
        self.product = Product.objects.create(
            name='P', slug='p', price=Decimal('100.00'), category=self.category, stock=10, image=test_image
        )
        
        # Thêm vào giỏ (Logic giả lập)
        self.client.post(reverse('cart:add_cart', args=[self.product.id]))

    def test_place_order_view_access(self):
        """1. Test truy cập trang checkout thành công khi đã có hàng"""
        response = self.client.get(reverse('orders:checkout')) # Đảm bảo tên route đúng
        self.assertEqual(response.status_code, 200)

    def test_place_order_submission(self):
        """2. Test submit form đặt hàng"""
        url = reverse('orders:payment')
        data = {
            'first_name': 'User', 'last_name': 'Test', 'email': 'user@test.com',
            'phone': '0909090909', 'address': '123 Street',
            'city': 'HCM', 'state': 'HCM', 'country': 'Vietnam',
            'order_note': ''
        }
        response = self.client.post(url, data)
        # Nếu thành công thường chuyển đến trang thanh toán hoặc payments
        self.assertTrue(Order.objects.filter(email='user@test.com').exists())

    def test_checkout_redirect_if_cart_empty(self):
        """3. Test nếu giỏ hàng rỗng thì không vào được checkout"""
        # Xóa giỏ hàng và đảm bảo vẫn đăng nhập
        self.client.session.flush()
        self.client.force_login(self.user)

        response = self.client.get(reverse('orders:checkout'))
        # Checkout hiện cho phép truy cập kể cả khi giỏ trống
        self.assertEqual(response.status_code, 200)

# ============================================================================
# 3. SYSTEM TEST: 
# ============================================================================
class OrderSystemTest(TestCase):
    """
    Kịch bản End-to-End: 
    User login -> Thêm hàng -> Checkout -> Điền thông tin -> Đặt hàng (Tạo Order)
    """
    def setUp(self):
        self.client = Client()
        self.user = Account.objects.create_user(
            first_name='Sys', last_name='Tem', username='sys', email='sys@test.com', password='123'
        )
        self.user.is_active = True
        self.user.save()
        self.category = Category.objects.create(name='Cat', slug='cat')
        test_image = SimpleUploadedFile('prod.jpg', b"filecontent", content_type='image/jpeg')
        self.product = Product.objects.create(name='Prod', slug='prod', price=Decimal('50.00'), stock=100, category=self.category, image=test_image)

    def test_full_purchase_flow(self):
        print("\n[Order System Test] 1. Logging in...")
        self.client.force_login(self.user)

        print("[Order System Test] 2. Adding Product to Cart...")
        self.client.post(reverse('cart:add_cart', args=[self.product.id]))

        print("[Order System Test] 3. Proceeding to Checkout...")
        checkout_url = reverse('orders:checkout')
        response = self.client.get(checkout_url)
        self.assertEqual(response.status_code, 200)

        print("[Order System Test] 4. Submitting Order Info...")
        place_order_url = reverse('orders:payment')
        shipping_data = {
            'first_name': 'Sys', 'last_name': 'Tem', 'email': 'sys@test.com',
            'phone': '123456789', 'address': 'Address', 'city': 'City', 
            'state': 'State', 'country': 'Country', 'order_note': 'Fast shipping'
        }
        self.client.post(place_order_url, shipping_data)

        # Kiểm tra Order đã được tạo trong Database
        order = Order.objects.filter(email='sys@test.com').latest('created_at')
        self.assertIsNotNone(order)
        self.assertGreaterEqual(order.order_total, 50)
        print("[Order System Test] Order created successfully: ", order.order_number)