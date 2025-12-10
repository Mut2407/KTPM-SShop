from django.test import TestCase, Client
from django.urls import reverse
from .models import Account

# ============================================================================
# 1. UNIT TEST: Kiểm tra logic nội tại của Model Account
# ============================================================================
class AccountUnitTest(TestCase):
    def test_account_model_str(self):
        """1. Test hàm __str__ trả về email"""
        user = Account.objects.create_user(
            first_name='Unit', last_name='Test', username='unittest', email='unit@test.com', password='123'
        )
        self.assertEqual(str(user), 'unit@test.com')

    def test_create_user_is_inactive_by_default(self):
        """2. Test user mới tạo (thường) phải ở trạng thái chưa kích hoạt (cần xác thực email)"""
        user = Account.objects.create_user(
            first_name='A', last_name='B', username='ab', email='ab@gmail.com', password='123'
        )
        self.assertFalse(user.is_active)

    def test_create_superuser_permissions(self):
        """3. Test tạo superuser phải có đủ quyền admin"""
        admin = Account.objects.create_superuser(
            first_name='Admin', last_name='User', username='admin', email='admin@test.com', password='123'
        )
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superadmin)


# ============================================================================
# 2. INTEGRATION TEST: Kiểm tra URL -> View -> Database
# ============================================================================
class AccountIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.user_data = {
            'first_name': 'Integ', 'last_name': 'Test', 'email': 'integ@example.com',
            'Phone_number': '0123456789', 'password': 'password123', 'repeat_password': 'password123'
        }

    def test_register_view_success(self):
        """1. Test submit form đăng ký hợp lệ"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertTrue(Account.objects.filter(email='integ@example.com').exists())
        self.assertEqual(response.status_code, 302) # Redirect về login hoặc thông báo

    def test_login_view_success(self):
        """2. Test đăng nhập thành công"""
        # Tạo user và kích hoạt trước
        user = Account.objects.create_user('F', 'L', 'user', 'login@test.com', 'pass123')
        user.is_active = True
        user.save()

        response = self.client.post(self.login_url, {'email': 'login@test.com', 'password': 'pass123'})
        self.assertEqual(response.status_code, 302) # Redirect tới dashboard
        self.assertTrue('_auth_user_id' in self.client.session) # Session đã được tạo

    def test_register_duplicate_email_fail(self):
        """3. Test đăng ký thất bại khi email đã tồn tại"""
        Account.objects.create_user('F', 'L', 'exist', 'integ@example.com', '123') 
        response = self.client.post(self.register_url, self.user_data) # Đăng ký trùng email
        self.assertEqual(response.status_code, 200) 



# ============================================================================
# 3. SYSTEM TEST: Kịch bản người dùng
# ============================================================================
class AccountSystemTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('accounts:dashboard')
        self.login_url = reverse('accounts:login')
        # Tạo user sẵn cho các kịch bản login
        self.user = Account.objects.create_user('Sys', 'Tem', 'sys', 'sys@test.com', '123')
        self.user.is_active = True
        self.user.save()

    def test_full_authentication_flow(self):
        """1. Kịch bản: Đăng nhập -> Dashboard -> Đăng xuất"""
        # Login
        self.client.post(self.login_url, {'email': 'sys@test.com', 'password': '123'})
        # Vào dashboard
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sys')
        # Logout
        self.client.get(reverse('accounts:logout'))
        # Vào lại dashboard bị chặn
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)

    def test_login_failed_flow(self):
        """2. Kịch bản: Nhập sai mật khẩu -> Hệ thống báo lỗi"""
        response = self.client.post(self.login_url, {'email': 'sys@test.com', 'password': 'WRONG_PASSWORD'})
        self.assertEqual(response.status_code, 200) # Vẫn ở trang login
        self.assertContains(response, 'Invalid') 

    def test_anonymous_access_dashboard_flow(self):
        """3. Kịch bản: Cố tình vào Dashboard khi chưa đăng nhập -> Bị đá về Login"""
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertIn(self.login_url, response.url) # trang login