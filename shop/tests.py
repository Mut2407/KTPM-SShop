from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Product, Category

# ============================================================================
# 1. UNIT TEST: Kiểm tra Model Sản phẩm và Danh mục
# ============================================================================
class ShopUnitTest(TestCase):
    def setUp(self):
        # Tạo dữ liệu mẫu dùng chung
        self.category = Category.objects.create(
            name='Giày', slug='giay'
        )
        image_file = SimpleUploadedFile('test.jpg', b'filecontent', content_type='image/jpeg')
        self.product = Product.objects.create(
            name='Nike Air', 
            slug='nike-air', 
            price=100, 
            stock=10, 
            category=self.category,
            is_available=True,
            image=image_file
        )

    def test_category_str(self):
        """1. Test tên hiển thị của Category"""
        self.assertEqual(str(self.category), 'Giày')

    def test_product_str(self):
        """2. Test tên hiển thị của Product"""
        self.assertEqual(str(self.product), 'Nike Air')

    def test_product_availability(self):
        """3. Test logic sản phẩm có sẵn hay không"""
        self.assertTrue(self.product.is_available)
        self.product.stock = 0
        # Tùy logic của bạn, có thể cần hàm check stock, ở đây test gán trị đơn giản
        self.assertEqual(self.product.stock, 0)


# ============================================================================
# 2. INTEGRATION TEST: Kiểm tra URL và Views hiển thị sản phẩm
# ============================================================================
class ShopIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Áo', slug='ao')
        image_file = SimpleUploadedFile('test2.jpg', b'filecontent', content_type='image/jpeg')
        self.product = Product.objects.create(
            name='Áo Thun', slug='ao-thun', price=50, stock=5, 
            category=self.category, is_available=True, image=image_file
        )
        self.shop_url = reverse('shop:shop')
        self.product_detail_url = reverse('shop:product_details', args=[self.category.slug, self.product.slug])

    def test_shop_page_status(self):
        """1. Test trang cửa hàng load thành công (200 OK)"""
        response = self.client.get(self.shop_url)
        self.assertEqual(response.status_code, 200)

    def test_product_detail_view(self):
        """2. Test trang chi tiết sản phẩm hiển thị đúng nội dung"""
        response = self.client.get(self.product_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Áo Thun') # Kiểm tra tên sp có trong HTML

    def test_search_view(self):
        """3. Test chức năng tìm kiếm"""
        search_url = reverse('shop:search')
        response = self.client.get(search_url, {'keyword': 'Áo'})
        self.assertContains(response, 'Áo Thun')
        self.assertNotContains(response, 'Giày')


# ============================================================================
# 3. SYSTEM TEST: Mô phỏng hành trình xem hàng
# ============================================================================
class ShopSystemTest(TestCase):
    """Kịch bản: User vào trang chủ -> Vào trang shop -> Chọn danh mục -> Xem chi tiết"""
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Bóng đá', slug='bong-da')
        image_file = SimpleUploadedFile('test3.jpg', b'filecontent', content_type='image/jpeg')
        self.product = Product.objects.create(
            name='Banh WC', slug='banh-wc', price=200, stock=5, category=self.category, is_available=True, image=image_file
        )

    def test_browsing_flow(self):
        print("\n[Shop System Test] 1. User accessing Shop page...")
        response = self.client.get(reverse('shop:shop'))
        self.assertEqual(response.status_code, 200)

        print("[Shop System Test] 2. User filtering by Category...")
        cat_url = reverse('shop:categries', args=[self.category.slug])
        response = self.client.get(cat_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Banh WC')

        print("[Shop System Test] 3. User clicking Product Detail...")
        detail_url = reverse('shop:product_details', args=[self.category.slug, self.product.slug])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '200') # Kiểm tra giá tiền hiển thị