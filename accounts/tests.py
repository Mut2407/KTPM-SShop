from django.test import TestCase, Client
from django.urls import reverse
from .models import Account

class AccountTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Namespace là 'accounts' nên phải dùng 'accounts:register'
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        
        # DỮ LIỆU ĐÃ ĐƯỢC SỬA CHO KHỚP VỚI FORMS.PY
        self.user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'Phone_number': '0123456789',   # Thêm trường này (lưu ý chữ P hoa như trong model/form)
            'password': 'password123',
            'repeat_password': 'password123' # Sửa từ 'confirm_password' thành 'repeat_password'
        }

    def test_account_model_str(self):
        """Test model __str__ method"""
        user = Account.objects.create_user(
            first_name='A', last_name='B', username='ab', email='ab@gmail.com', password='123'
        )
        self.assertEqual(str(user), 'ab@gmail.com')

    def test_register_view_success(self):
        """Test register view creates a user"""
        response = self.client.post(self.register_url, self.user_data)
        
        # Debug: Nếu vẫn lỗi, in ra lỗi form để kiểm tra
        if response.context and 'forms' in response.context:
            print(response.context['forms'].errors)

        # Kiểm tra user đã được tạo chưa
        self.assertTrue(Account.objects.filter(email='test@example.com').exists())
        
        # Kiểm tra redirect (Mã 302)
        self.assertEqual(response.status_code, 302)