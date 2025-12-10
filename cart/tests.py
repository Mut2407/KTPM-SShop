from django.test import TestCase, Client
from django.urls import reverse
from shop.models import Product, Category
from .models import Cart, CartItem

class CartUnitTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='P1', slug='p1', price=10, category=self.category,
            stock=10, image='photos/products/test.jpg'
        )
        self.cart = Cart.objects.create(cart_id='12345')

    def test_cart_creation(self):
        """1. Test tạo giỏ hàng thành công"""
        self.assertEqual(self.cart.cart_id, '12345')

    def test_cart_item_subtotal(self):
        """2. Test tính tổng tiền của một item (số lượng * đơn giá)"""
        item = CartItem.objects.create(product=self.product, cart=self.cart, quantity=2)
        # Giả sử trong model CartItem bạn có hàm sub_total()
        self.assertEqual(item.sub_total(), 20) 

    def test_cart_item_active(self):
        """3. Test mặc định item trong giỏ hàng là active"""
        item = CartItem.objects.create(product=self.product, cart=self.cart, quantity=1)
        self.assertTrue(item.is_active)


class CartIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            name='P1', slug='p1', price=100, category=self.category,
            stock=10, image='photos/products/test.jpg'
        )
        self.add_cart_url = reverse('cart:add_cart', args=[self.product.id])
        self.cart_url = reverse('cart:cart')

    def test_add_to_cart(self):
        """1. Test request thêm sản phẩm vào giỏ"""
        response = self.client.post(self.add_cart_url)
        # Thường sẽ redirect về trang cart (302)
        self.assertEqual(response.status_code, 302)
        
        # Kiểm tra session key và Cart tương ứng đã được tạo
        session = self.client.session
        self.assertIsNotNone(session.session_key)
        self.assertTrue(Cart.objects.filter(cart_id=session.session_key).exists())

    def test_cart_page_display(self):
        """2. Test trang giỏ hàng hiển thị đúng sản phẩm đã thêm"""
        self.client.post(self.add_cart_url) # Thêm trước
        response = self.client.get(self.cart_url)
        self.assertContains(response, 'P1') # Tên sản phẩm
        self.assertContains(response, '100') # Giá tiền

    def test_empty_cart(self):
        """3. Test trang giỏ hàng khi chưa có gì"""
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        # Kiểm tra thông báo giỏ hàng trống (tùy text trong template của bạn)
        self.assertContains(response, 'Your Cart Is Empty')


class CartSystemTest(TestCase):
    """Kịch bản: Thêm vào giỏ -> Tăng số lượng -> Xóa khỏi giỏ"""
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Gym', slug='gym')
        self.product = Product.objects.create(
            name='Tạ tay', slug='ta-tay', price=50, category=self.category,
            stock=10, image='photos/products/test.jpg'
        )

    def test_cart_manipulation_flow(self):
        add_url = reverse('cart:add_cart', args=[self.product.id])
        cart_url = reverse('cart:cart')

        print("\n[Cart System Test] 1. Adding Item to Cart...")
        self.client.post(add_url)
        response = self.client.get(cart_url)
        self.assertContains(response, 'Tạ tay')

        print("[Cart System Test] 2. Adding Same Item Again (Quantity Increase)...")
        self.client.post(add_url)
        item = CartItem.objects.get(product=self.product)
        self.assertEqual(item.quantity, 2)

        print("[Cart System Test] 3. Removing Item from Cart...")
        remove_url = reverse('cart:remove_cart_item', args=[self.product.id, item.id]) # Giả định URL xóa
        self.client.get(remove_url)
        
        # Kiểm tra item đã biến mất khỏi DB hoặc quantity = 0
        self.assertFalse(CartItem.objects.filter(id=item.id).exists())