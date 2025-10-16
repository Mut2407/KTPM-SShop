from django.test import TestCase
from django.urls import reverse

class RegisterLoginTest(TestCase):

    def test_register_valid(self):
        """Kiểm tra đăng ký hợp lệ"""
        response = self.client.post(reverse('register'), {
            'username': 'user1',
            'email': 'user1@gmail.com',
            'password1': '12345678',
            'password2': '12345678'
        })
        # Kết quả mong đợi: chuyển hướng (302) đến trang đăng nhập
        self.assertEqual(response.status_code, 302)

    def test_register_invalid_email(self):
        """Kiểm tra email sai định dạng"""
        response = self.client.post(reverse('register'), {
            'username': 'user2',
            'email': 'abc@xyz',  # sai định dạng
            'password1': '12345678',
            'password2': '12345678'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email không hợp lệ")

    def test_login_valid(self):
        """Kiểm tra đăng nhập hợp lệ"""
        self.client.post(reverse('register'), {
            'username': 'user1',
            'email': 'user1@gmail.com',
            'password1': '12345678',
            'password2': '12345678'
        })
        response = self.client.post(reverse('login'), {
            'username': 'user1',
            'password': '12345678'
        })
        self.assertEqual(response.status_code, 302)
