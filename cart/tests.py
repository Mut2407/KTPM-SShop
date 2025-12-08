from django.test import TestCase, Client
from django.urls import reverse
from shop.models import Product, Category, Variation
from cart.models import Cart, CartItem
from accounts.models import Account

class CartUnitTests(TestCase):
    """
    Unit Test: Kiểm tra các phương thức logic trong models.py
    """
    def setUp(self):
        # Tạo dữ liệu giả lập
        self.category = Category.objects.create(name="Áo", slug="ao")
        self.product = Product.objects.create(
            name="Áo Thun Basic", # Lưu ý: Model của bạn dùng 'name', không phải 'product_name'
            slug="ao-thun-basic",
            price=200,            # Giá 200
            stock=50,
            category=self.category,
            image='photos/products/test.jpg'
        )
        self.cart = Cart.objects.create(cart_id="test_cart_id")

    def test_cart_item_sub_total(self):
        # Tạo một CartItem với số lượng là 3
        cart_item = CartItem.objects.create(
            product=self.product,
            cart=self.cart,
            quantity=3
        )
        # Kiểm tra logic: sub_total = price * quantity = 200 * 3 = 600
        self.assertEqual(cart_item.sub_total(), 600)

    def test_cart_str_representation(self):
        # Kiểm tra hàm __str__ của Cart
        self.assertEqual(str(self.cart), "test_cart_id")


class CartIntegrationTests(TestCase):
    """
    Integration Test: Kiểm tra luồng hoạt động (Views, URLs)
    """
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Quần", slug="quan")
        self.product = Product.objects.create(
            name="Quần Jean",
            slug="quan-jean",
            price=500,
            stock=20,
            category=self.category,
            image='photos/products/jean.jpg'
        )
        # URL thêm vào giỏ (Bạn cần kiểm tra file cart/urls.py để chắc chắn namespace là 'cart')
        self.add_cart_url = reverse('cart:add_cart', args=[self.product.id])
        self.cart_url = reverse('cart:cart')

    def test_add_to_cart_guest_user(self):
        """
        Test khách vãng lai (chưa login) thêm hàng vào giỏ
        """
        response = self.client.get(self.add_cart_url)
        
        # 1. Kiểm tra session đã được tạo cart_id chưa
        session = self.client.session
        # Note: logic _cart_id trong views.py lấy session_key, cần request kích hoạt session trước
        
        # 2. Kiểm tra redirect về trang giỏ hàng (Mã 302)
        self.assertEqual(response.status_code, 302)
        
        # 3. Kiểm tra xem CartItem đã được tạo trong Database chưa
        # Vì chưa login, cart được link qua cart_id (session)
        # Chúng ta kiểm tra đơn giản là có CartItem nào chứa product này không
        self.assertTrue(CartItem.objects.filter(product=self.product, quantity=1).exists())

    def test_cart_view_displays_items(self):
        """
        Test trang giỏ hàng hiển thị đúng sản phẩm đã thêm
        """
        # Thêm sản phẩm trước
        self.client.get(self.add_cart_url)
        
        # Truy cập trang giỏ hàng
        response = self.client.get(self.cart_url)
        
        # Kiểm tra mã 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Kiểm tra tên sản phẩm có hiển thị trong HTML không
        self.assertContains(response, "Quần Jean")
        
        # Kiểm tra tổng tiền (500 + thuế + phí ship)
        # Logic trong views.py: tax = 2% * 500 = 10; handling = 15; Total = 500 + 10 + 15 = 525
        # Kiểm tra con số 525 có xuất hiện không
        self.assertContains(response, "525")

    def test_remove_item_from_cart(self):
        """
        Test chức năng giảm số lượng/xóa item
        """
        # Thêm vào giỏ hàng 2 lần để số lượng là 2
        self.client.get(self.add_cart_url)
        self.client.get(self.add_cart_url)
        
        # Lấy cart_item vừa tạo
        cart_item = CartItem.objects.filter(product=self.product).last()
        self.assertEqual(cart_item.quantity, 2)
        
        # Gọi URL remove_cart (giảm số lượng)
        remove_url = reverse('cart:remove_cart', args=[self.product.id, cart_item.id])
        self.client.get(remove_url)
        
        # Kiểm tra lại số lượng còn 1
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)