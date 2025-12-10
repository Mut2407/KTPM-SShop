from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import Account
from .models import Product, Category, ReviewRating

# ============================================================================
# 1. UNIT TEST: Kiểm tra logic tính toán trong Model
# ============================================================================
class ShopUnitTest(TestCase):
    def setUp(self):
        # Tạo Category
        self.category = Category.objects.create(name="Giày", slug="giay")
        
        # Tạo Product với ảnh giả lập
        image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
        uploaded_image = SimpleUploadedFile("small.gif", image_content, content_type="image/gif")

        self.product = Product.objects.create(
            name="Nike Air",
            slug="nike-air",
            price=200.00,
            stock=10,
            category=self.category,
            is_available=True,
            image=uploaded_image
        )

        # Tạo User để test Review
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser', email='test@user.com', password='password123'
        )

    def test_product_model_str(self):
        """Test __str__ trả về tên sản phẩm"""
        self.assertEqual(str(self.product), "Nike Air")

    def test_review_rating_calculation(self):
        """Test tính điểm trung bình và đếm số lượng review"""
        # Tạo 2 review: 5 sao và 3 sao -> Trung bình = 4.0
        ReviewRating.objects.create(product=self.product, user=self.user, rating=5, status=True)
        ReviewRating.objects.create(product=self.product, user=self.user, rating=3, status=True)
        
        self.assertEqual(self.product.countReview(), 2)
        self.assertEqual(self.product.averageRating(), 4.0)


# ============================================================================
# 2. INTEGRATION TEST: Kiểm tra View và URL
# ============================================================================
class ShopIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Áo", slug="ao")
        self.product = Product.objects.create(
            name="Áo Thun", slug="ao-thun", price=100, stock=50, 
            category=self.category, is_available=True, image='test.jpg'
        )

    def test_home_view(self):
        """Test trang chủ hiển thị sản phẩm"""
        response = self.client.get(reverse('shop:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")

    def test_product_detail_view(self):
        """Test trang chi tiết sản phẩm"""
        url = reverse('shop:product_details', args=[self.category.slug, self.product.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Áo Thun")
        self.assertContains(response, "100") # Kiểm tra giá

    def test_search_view(self):
        """Test chức năng tìm kiếm"""
        url = reverse('shop:search')
        # Tìm thấy
        response = self.client.get(url, {'keyword': 'Thun'})
        self.assertContains(response, "Áo Thun")
        # Không tìm thấy
        response = self.client.get(url, {'keyword': 'XYZ'})
        self.assertNotContains(response, "Áo Thun")


# ============================================================================
# 3. SYSTEM TEST: Mô phỏng luồng người dùng thực tế
# ============================================================================
class ShopSystemTest(TestCase):
    """
    Kịch bản: 
    Khách tìm kiếm sản phẩm -> Xem chi tiết -> Đăng nhập -> Viết đánh giá 5 sao
    """
    def setUp(self):
        self.client = Client()
        
        # 1. Setup User & Active
        self.user = Account.objects.create_user('Sys', 'User', 'sysuser', 'sys@shop.com', 'pass123')
        self.user.is_active = True
        self.user.save()
        
        # 2. Setup Product
        self.category = Category.objects.create(name="Laptop", slug="laptop")
        self.product = Product.objects.create(
            name="Macbook Pro", slug="macbook-pro", price=2000, stock=5, 
            category=self.category, image='m.jpg'
        )

    def test_search_view_review_flow(self):
        # --- BƯỚC 1: TÌM KIẾM SẢN PHẨM ---
        print("\n[Shop System Test] 1. Searching for 'Macbook'...")
        search_url = reverse('shop:search')
        response = self.client.get(search_url, {'keyword': 'Macbook'})
        
        # Kiểm tra kết quả tìm kiếm có sản phẩm không
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Macbook Pro")

        # --- BƯỚC 2: XEM CHI TIẾT SẢN PHẨM ---
        print("[Shop System Test] 2. Viewing Product Details...")
        detail_url = reverse('shop:product_details', args=[self.category.slug, self.product.slug])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # --- BƯỚC 3: ĐĂNG NHẬP (Để review) ---
        print("[Shop System Test] 3. Logging in...")
        self.client.login(email='sys@shop.com', password='pass123')

        # --- BƯỚC 4: GỬI ĐÁNH GIÁ (REVIEW) ---
        print("[Shop System Test] 4. Posting a 5-star Review...")
        review_url = reverse('shop:review', args=[self.product.id])
        
        # Giả lập HTTP_REFERER vì view review sẽ redirect về trang trước đó
        header = {'HTTP_REFERER': detail_url}
        
        data = {
            'rating': 5,
            'review': 'Sản phẩm tuyệt vời, đáng tiền!'
        }
        response = self.client.post(review_url, data, **header)
        
        # Kiểm tra Redirect (302) sau khi post thành công
        self.assertEqual(response.status_code, 302)
        
        # --- BƯỚC 5: KIỂM TRA DỮ LIỆU ĐÃ LƯU ---
        print("[Shop System Test] 5. Verifying Review in Database...")
        # Kiểm tra xem review đã được lưu vào DB chưa
        self.assertTrue(ReviewRating.objects.filter(product=self.product, user=self.user, rating=5).exists())
        
        # Kiểm tra lại trang chi tiết xem review có hiện ra không
        response = self.client.get(detail_url)
        self.assertContains(response, 'Sản phẩm tuyệt vời')
        
        print("[Shop System Test] Shop Flow Successful ")