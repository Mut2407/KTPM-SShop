import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from accounts.models import Account
from shop.models import Product, Category
from .models import Order, Payment, OrderProduct

# ============================================================================
# 1. UNIT TEST
# ============================================================================
class OrderUnitTest(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Unit', last_name='Test', username='unit_test', email='unit@test.com', password='123'
        )
        self.order = Order.objects.create(
            user=self.user,
            order_number='2023120801',
            first_name='Nguyen',
            last_name='Van A',
            phone='0909000111',
            email='unit@test.com',
            address='123 Duong ABC',
            city='HCM',
            country='Vietnam',
            order_total=100.0,
            tax=2.0,
            status='New',
            ip='127.0.0.1'
        )

    def test_order_model_str(self):
        self.assertEqual(str(self.order), 'Nguyen')

    def test_full_name_method(self):
        self.assertEqual(self.order.full_name(), 'Nguyen Van A')


# ============================================================================
# 2. INTEGRATION TEST
# ============================================================================
class OrderIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        settings.SESSION_COOKIE_NAME = 'user_sessionid'

        # 1. Tạo User
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser', email='test@user.com', password='pass123'
        )
        self.user.is_active = True 
        self.user.save()
        self.client.login(email='test@user.com', password='pass123')
        
        # 2. Setup Sản phẩm
        self.category = Category.objects.create(name="Mũ", slug="mu")
        self.product = Product.objects.create(
            name="Mũ len", slug="mu-len", price=50, stock=100, category=self.category, image='test.jpg'
        )

    def test_checkout_view_status(self):
        self.client.get(reverse('cart:add_cart', args=[self.product.id]))
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)

    def test_place_order_submission(self):
        self.client.get(reverse('cart:add_cart', args=[self.product.id]))
        url = reverse('orders:payment') 
        data = {
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'phone': '0909123456',
            'email': 'test@user.com',
            'address': '123 Street',
            'city': 'HCM',
            'state': 'Quan 1',
            'country': 'Vietnam',
            'order_note': 'Giao nhanh'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.filter(email='test@user.com').exists())


# ============================================================================
# 3. SYSTEM TEST (NEW)
# ============================================================================
class OrderSystemTest(TestCase):
    """
    Kịch bản: Mua hàng -> Checkout -> Thanh toán COD -> Kiểm tra đơn hàng đã tạo
    """
    def setUp(self):
        self.client = Client()
        settings.SESSION_COOKIE_NAME = 'user_sessionid'
        
        # User & Login
        self.user = Account.objects.create_user('Sys', 'User', 'sysuser', 'sys@test.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        self.client.login(email='sys@test.com', password='pass123')

        # Product
        self.cat = Category.objects.create(name="Ao", slug="ao")
        self.prod = Product.objects.create(name="Ao Thun", slug="ao-thun", price=200, stock=10, category=self.cat, image='p.jpg')

    def test_full_order_flow(self):
        print("\n[Order System Test] 1. Adding product to cart...")
        self.client.get(reverse('cart:add_cart', args=[self.prod.id]))

        print("[Order System Test] 2. Submitting Billing Info...")
        self.client.post(reverse('orders:payment'), {
            'first_name': 'Sys', 'last_name': 'User', 'email': 'sys@test.com',
            'phone': '0909', 'address': '123 St', 'city': 'HCM', 'state': 'Q1', 'country': 'VN',
            'order_note': 'Note'
        })
        
        # Lấy order vừa tạo (chưa thanh toán) từ DB
        order = Order.objects.get(email='sys@test.com', is_ordered=False)
        
        print("[Order System Test] 3. Selecting COD Payment Method...")
        
        # --- SỬA ĐỔI QUAN TRỌNG ---
        # Thay vì gọi 'payment_method' (tạo order mới), ta gọi 'cod_payment' (update order cũ)
        # View cod_payment yêu cầu dữ liệu JSON chứa order_number
        
        payment_url = reverse('orders:cod_payment')
        data = {'order_number': order.order_number}
        
        # Gửi request dạng JSON
        response = self.client.post(
            payment_url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200) # Expect JSON success response
        # --------------------------
        
        print("[Order System Test] 4. Verifying Order Completion...")
        order.refresh_from_db()
        
        # Kiểm tra trạng thái đã đặt hàng
        self.assertTrue(order.is_ordered, "Đơn hàng phải chuyển trạng thái is_ordered=True")
        self.assertEqual(order.status, 'Pending') 
        
        # Kiểm tra OrderProduct được tạo ra (chuyển từ Cart sang)
        self.assertTrue(OrderProduct.objects.filter(order=order).exists())
        
        # Kiểm tra giỏ hàng đã bị xóa sau khi mua
        from cart.models import CartItem
        self.assertFalse(CartItem.objects.filter(user=self.user).exists(), "Giỏ hàng phải trống sau khi thanh toán")
        
        print("[Order System Test] Order Flow Successful ")