from django.test import TestCase, Client
from django.urls import reverse
from shop.models import Product, Category
from cart.models import Cart, CartItem

# ============================================================================
# 1. UNIT TEST: Kiểm tra logic tính toán nội tại (Models)
# ============================================================================
class CartUnitTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Áo", slug="ao")
        self.product = Product.objects.create(
            name="Áo Thun Basic",
            slug="ao-thun-basic",
            price=200,
            stock=50,
            category=self.category,
            image='photos/products/test.jpg'
        )
        self.cart = Cart.objects.create(cart_id="test_cart_id")

    def test_cart_item_sub_total(self):
        """Test tính tổng tiền của một dòng sản phẩm (Price * Quantity)"""
        cart_item = CartItem.objects.create(
            product=self.product,
            cart=self.cart,
            quantity=3
        )
        # 200 * 3 = 600
        self.assertEqual(cart_item.sub_total(), 600)

    def test_cart_str_representation(self):
        self.assertEqual(str(self.cart), "test_cart_id")


# ============================================================================
# 2. INTEGRATION TEST: Kiểm tra tương tác Views & URLs lẻ
# ============================================================================
class CartIntegrationTests(TestCase):
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
        self.add_cart_url = reverse('cart:add_cart', args=[self.product.id])
        self.cart_url = reverse('cart:cart')

    def test_add_to_cart_guest_user(self):
        """Test khách thêm hàng: Session được tạo, Redirect 302, DB cập nhật"""
        response = self.client.get(self.add_cart_url)
        
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertTrue(CartItem.objects.filter(product=self.product, quantity=1).exists())

    def test_cart_view_displays_items(self):
        """Test trang giỏ hàng hiển thị đúng sản phẩm và giá"""
        self.client.get(self.add_cart_url) 
        
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quần Jean")
        self.assertContains(response, "525")

    def test_remove_item_from_cart(self):
        """Test giảm số lượng item"""
        # Thêm 2 lần
        self.client.get(self.add_cart_url)
        self.client.get(self.add_cart_url)
        
        cart_item = CartItem.objects.filter(product=self.product).last()
        
        # Giảm 1
        remove_url = reverse('cart:remove_cart', args=[self.product.id, cart_item.id])
        self.client.get(remove_url)
        
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 1)


# ============================================================================
# 3. SYSTEM TEST: Kiểm tra luồng đi trọn vẹn (End-to-End Flow)
# ============================================================================
class CartSystemTest(TestCase):
    """
    Kịch bản: 
    Thêm SP A -> Thêm SP B -> Xem giỏ -> Thêm tiếp SP A -> Xóa hẳn SP B -> Kiểm tra tổng tiền
    """
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Phụ kiện", slug="phu-kien")
        
        # Sản phẩm 1: Mũ (Giá 100)
        self.product_1 = Product.objects.create(
            name="Mũ Snapback", slug="mu-snapback", price=100, stock=50, category=self.category, image='p1.jpg'
        )
        # Sản phẩm 2: Kính (Giá 200)
        self.product_2 = Product.objects.create(
            name="Kính Râm", slug="kinh-ram", price=200, stock=50, category=self.category, image='p2.jpg'
        )
        self.cart_url = reverse('cart:cart')

    def test_full_shopping_cart_flow(self):
        print("\n[System Test] 1. Adding Hat ($100)...")
        self.client.get(reverse('cart:add_cart', args=[self.product_1.id]))

        
        print("[System Test] 2. Adding Glasses ($200)...")
        self.client.get(reverse('cart:add_cart', args=[self.product_2.id]))

        
        print("[System Test] 3. Verifying Cart Page content...")
        response = self.client.get(self.cart_url)
        self.assertContains(response, "Mũ Snapback")
        self.assertContains(response, "Kính Râm")
        

        print("[System Test] 4. Incrementing Hat quantity...")
        self.client.get(reverse('cart:add_cart', args=[self.product_1.id]))
        
        item_1 = CartItem.objects.get(product=self.product_1)
        self.assertEqual(item_1.quantity, 2)

        print("[System Test] 5. Removing Glasses completely...")
        item_2 = CartItem.objects.get(product=self.product_2)
        remove_all_url = reverse('cart:remove_cart_item', args=[self.product_2.id, item_2.id])
        self.client.get(remove_all_url)
        
        print("[System Test] 6. Verifying Final State...")
        response = self.client.get(self.cart_url)
        
        # Kính phải mất, Mũ còn nguyên
        self.assertNotContains(response, "Kính Râm")
        self.assertContains(response, "Mũ Snapback")
        self.assertContains(response, "219")
        print("[System Test] Cart Flow Completed Successfully")