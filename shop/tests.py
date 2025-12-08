from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Account
from .models import Product, Category, ReviewRating

class ShopUnitTest(TestCase):
    """
    Unit Test: Kiểm tra logic của Models và các phương thức tính toán
    """
    def setUp(self):
        # 1. Tạo Category
        self.category = Category.objects.create(
            name="Giày",
            slug="giay"
        )
        
        # 2. Tạo Product (Sửa lỗi: dùng 'name' thay vì 'product_name')
        # Tạo ảnh giả lập nhỏ để tránh lỗi ImageField
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
        uploaded_image = SimpleUploadedFile("small.gif", image_content, content_type="image/gif")

        self.product = Product.objects.create(
            name="Nike Air",        # <--- Đã sửa thành 'name'
            slug="nike-air",
            price=200.00,
            stock=10,
            category=self.category,
            is_available=True,
            image=uploaded_image
        )

        # 3. Tạo User để viết Review
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser', email='test@user.com', password='password123'
        )

    def test_product_model_str(self):
        """Kiểm tra __str__ trả về tên sản phẩm"""
        self.assertEqual(str(self.product), "Nike Air")

    def test_category_model_str(self):
        """Kiểm tra __str__ trả về tên danh mục"""
        self.assertEqual(str(self.category), "Giày")

    def test_product_url_resolution(self):
        """Kiểm tra hàm lấy URL chi tiết sản phẩm trong Model"""
        # Lưu ý: Trong models.py của bạn hàm tên là get_prodcut_details_url (có thể bạn gõ sai chữ product)
        expected_url = f'/shop/{self.category.slug}/{self.product.slug}/'
        self.assertEqual(self.product.get_prodcut_details_url(), expected_url)

    def test_review_rating_calculation(self):
        """Kiểm tra logic tính điểm trung bình (averageRating) và số lượng review"""
        # Tạo 2 review: 1 cái 5 sao, 1 cái 3 sao -> TB = 4.0
        ReviewRating.objects.create(product=self.product, user=self.user, rating=5, status=True)
        ReviewRating.objects.create(product=self.product, user=self.user, rating=3, status=True)
        
        self.assertEqual(self.product.countReview(), 2)
        self.assertEqual(self.product.averageRating(), 4.0)


class ShopIntegrationTest(TestCase):
    """
    Integration Test: Kiểm tra Views và URLs
    """
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Áo", slug="ao")
        self.product = Product.objects.create(
            name="Áo Thun",
            slug="ao-thun",
            price=100,
            stock=50,
            category=self.category,
            is_available=True,
            image='test.jpg'
        )

    def test_home_view(self):
        """Kiểm tra trang chủ hiển thị sản phẩm"""
        url = reverse('shop:home') # namespace 'shop'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")
        self.assertTemplateUsed(response, 'shop/index.html')

    def test_shop_view(self):
        """Kiểm tra trang cửa hàng (Store Page)"""
        url = reverse('shop:shop')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")

    def test_shop_category_view(self):
        """Kiểm tra lọc sản phẩm theo danh mục"""
        # URL: /shop/ao/
        # Lưu ý: trong urls.py bạn đặt name='categries' (thiếu chữ o)
        url = reverse('shop:categries', args=[self.category.slug]) 
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")

    def test_product_detail_view(self):
        """Kiểm tra trang chi tiết sản phẩm"""
        url = reverse('shop:product_details', args=[self.category.slug, self.product.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")
        self.assertContains(response, "100") # Kiểm tra giá tiền

    def test_search_view(self):
        """Kiểm tra chức năng tìm kiếm"""
        url = reverse('shop:search')
        
        # 1. Tìm từ khóa có tồn tại
        response = self.client.get(url, {'keyword': 'Thun'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")
        
        # 2. Tìm từ khóa không tồn tại
        response = self.client.get(url, {'keyword': 'XYZABC'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Áo Thun")