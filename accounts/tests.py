from django.test import TestCase, Client
from django.urls import reverse
from .models import Account

# ============================================================================
# 1. UNIT TEST: Kiểm tra logic nội tại của Model/Function
# ============================================================================
class AccountUnitTest(TestCase):
    def test_account_model_str(self):
        """Test hàm __str__ của Model Account"""
        user = Account.objects.create_user(
            first_name='Unit', last_name='Test', username='unittest', email='unit@test.com', password='123'
        )
        # Kiểm tra xem string representation có phải là email không
        self.assertEqual(str(user), 'unit@test.com')

    def test_create_user_is_inactive_by_default(self):
        """Test user mới tạo phải ở trạng thái chưa kích hoạt"""
        user = Account.objects.create_user(
            first_name='A', last_name='B', username='ab', email='ab@gmail.com', password='123'
        )
        self.assertFalse(user.is_active)


# ============================================================================
# 2. INTEGRATION TEST: Kiểm tra sự tương tác giữa URL -> View -> Database
# ============================================================================
class AccountIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Lưu ý: Dùng namespace 'accounts:' như đã sửa trước đó
        self.register_url = reverse('accounts:register')
        
        self.user_data = {
            'first_name': 'Integ',
            'last_name': 'Test',
            'email': 'integ@example.com',
            'Phone_number': '0123456789',
            'password': 'password123',
            'repeat_password': 'password123'
        }

    def test_register_view_success(self):
        """Test việc submit form đăng ký thành công"""
        response = self.client.post(self.register_url, self.user_data)
        
        # 1. Kiểm tra User đã được lưu vào DB chưa
        self.assertTrue(Account.objects.filter(email='integ@example.com').exists())
        
        # 2. Kiểm tra phản hồi là Redirect (302)
        self.assertEqual(response.status_code, 302)


# ============================================================================
# 3. SYSTEM TEST (END-TO-END): Mô phỏng hành trình trọn vẹn của User
# ============================================================================
class AccountSystemTest(TestCase):
    """
    Kịch bản: 
    Khách -> Đăng ký -> (Hệ thống gửi mail) -> (User click link kích hoạt) -> Đăng nhập -> Vào Dashboard -> Logout
    """
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.dashboard_url = reverse('accounts:dashboard')
        self.logout_url = reverse('accounts:logout')

        self.sys_user_data = {
            'first_name': 'System',
            'last_name': 'User',
            'email': 'system@example.com',
            'Phone_number': '0987654321',
            'password': 'password123',
            'repeat_password': 'password123'
        }

    def test_full_authentication_flow(self):
        # --- BƯỚC 1: ĐĂNG KÝ (Register) ---
        print("\n[System Test] 1. User Registering...")
        self.client.post(self.register_url, self.sys_user_data)
        
        # Lấy user từ DB ra
        user = Account.objects.get(email='system@example.com')
        
        # --- BƯỚC 2: GIẢ LẬP KÍCH HOẠT (Activate) ---
        # Thực tế user sẽ click link email, trong test ta set trực tiếp
        print("[System Test] 2. Simulating Email Activation...")
        user.is_active = True
        user.save()

        # --- BƯỚC 3: ĐĂNG NHẬP (Login) ---
        print("[System Test] 3. User Logging in...")
        response = self.client.post(self.login_url, {
            'email': 'system@example.com',
            'password': 'password123'
        })
        
        # Kiểm tra login thành công (thường redirect về Dashboard hoặc trang trước đó)
        self.assertEqual(response.status_code, 302)

        # --- BƯỚC 4: TRUY CẬP DASHBOARD ---
        # Vì session client vẫn giữ trạng thái login, ta request vào trang dashboard
        print("[System Test] 4. Accessing Dashboard...")
        response = self.client.get(self.dashboard_url)
        
        # Phải vào được (Code 200), nếu chưa login sẽ bị redirect (302)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System User') # Kiểm tra tên hiển thị

        # --- BƯỚC 5: ĐĂNG XUẤT (Logout) ---
        print("[System Test] 5. User Logging out...")
        self.client.get(self.logout_url)
        
        # --- BƯỚC 6: KIỂM TRA LẠI (Re-check) ---
        # Sau khi logout, truy cập lại dashboard phải bị chặn (Redirect 302 về Login)
        response = self.client.get(self.dashboard_url)
        self.assertNotEqual(response.status_code, 200)
        print("[System Test] Flow Completed Successfully ")