from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import Account
from shop.models import Product, Category
from .models import Order

class OrderTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Tạo user và login
        self.user = Account.objects.create_user(
            'testuser', 'test', 'user', 'test@user.com', 'pass123'
        )
        self.client.login(email='test@user.com', password='pass123')
        
        # Setup sản phẩm để mua
        self.category = Category.objects.create(name="Mũ", slug="mu")
        self.product = Product.objects.create(
            product_name="Mũ len", slug="mu-len", price=50, stock=100, category=self.category
        )

    # Integration Test: Đặt hàng (Place Order)
    def test_place_order(self):
        # 1. Thêm hàng vào giỏ trước
        self.client.get(reverse('add_cart', args=[self.product.id]))
        
        # 2. Submit form checkout
        url = reverse('place_order')
        data = {
            'first_name': 'Nguyen',
            'last_name': 'Van A',
            'phone': '0909123456',
            'email': 'test@user.com',
            'address_line_1': '123 Street',
            'city': 'HCM',
            'country': 'Vietnam',
            'order_note': 'Giao nhanh'
        }
        response = self.client.post(url, data)
        
        # 3. Kiểm tra xem Order đã được lưu vào DB chưa
        self.assertTrue(Order.objects.filter(email='test@user.com').exists())
        order = Order.objects.get(email='test@user.com')
        self.assertEqual(order.first_name, 'Nguyen')