from django.test import TestCase, Client, override_settings # Thêm override_settings
from django.urls import reverse
from django.conf import settings # Import settings
from accounts.models import Account
from shop.models import Product, Category
from .models import Order, Payment

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


class OrderIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # --- FIX QUAN TRỌNG: Đồng bộ tên cookie với Middleware ---
        settings.SESSION_COOKIE_NAME = 'user_sessionid'
        # ---------------------------------------------------------

        # 1. Tạo User
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser', email='test@user.com', password='pass123'
        )
        self.user.is_active = True 
        self.user.save()

        # Đăng nhập
        self.client.login(email='test@user.com', password='pass123')
        
        # 2. Setup Sản phẩm
        self.category = Category.objects.create(name="Mũ", slug="mu")
        self.product = Product.objects.create(
            name="Mũ len", 
            slug="mu-len", 
            price=50, 
            stock=100, 
            category=self.category,
            image='photos/products/test.jpg'
        )

    def test_checkout_view_status(self):
        """Kiểm tra trang checkout có truy cập được không"""
        add_cart_url = reverse('cart:add_cart', args=[self.product.id])
        self.client.get(add_cart_url)
        
        url = reverse('orders:checkout')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)

    def test_place_order_submission(self):
        """Test quy trình điền form thông tin thanh toán"""
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
        order = Order.objects.filter(email='test@user.com').last()
        self.assertEqual(order.order_total, 66.0)