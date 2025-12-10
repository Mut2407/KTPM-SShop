from django.test import TestCase, Client
from django.urls import reverse
from .models import Post
from django.utils import timezone

class BlogTest(TestCase):
    def setUp(self):
        # Setup môi trường giả lập trình duyệt
        self.client = Client()
        
        # Tạo dữ liệu mẫu (Unit Test Data)
        self.post = Post.objects.create(
            title="Bài viết test",
            content="Nội dung bài viết mẫu",
            created_at=timezone.now()
        )

    # ---------------------------------------------------------
    # UNIT TEST: Kiểm tra logic của Model
    # ---------------------------------------------------------
    def test_post_model_str(self):
        """Kiểm tra hàm __str__ của model trả về đúng tiêu đề"""
        self.assertEqual(str(self.post), "Bài viết test")

    # ---------------------------------------------------------
    # INTEGRATION TEST: Kiểm tra Views và URLs
    # ---------------------------------------------------------
    def test_blog_list_view(self):
        """Kiểm tra trang danh sách bài viết (Blog List)"""
        # Vì app_name='blog' trong urls.py nên phải dùng 'blog:blog'
        response = self.client.get(reverse('blog:blog'))
        
        # 1. Kiểm tra HTTP Status Code = 200 (Thành công)
        self.assertEqual(response.status_code, 200)
        
        # 2. Kiểm tra nội dung bài viết có hiển thị không
        self.assertContains(response, "Bài viết test")
        self.assertContains(response, "Nội dung bài viết mẫu")