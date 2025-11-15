from django.test import TestCase
from django.urls import reverse
from accounts.models import Account

class RegisterLoginTest(TestCase):
    def setUp(self):
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.valid_user_data = {
            'first_name': 'Kỳ',
            'last_name': 'Vy',
            'phone_number': '0123456789',
            'email': 'kyvy@example.com',
            'password': '123456',
            'confirm_password': '123456'
        }

    def test_register_valid(self):
        response = self.client.post(self.register_url, self.valid_user_data)
        self.assertEqual(response.status_code, 302)  

    def test_register_invalid_email(self):
        data = self.valid_user_data.copy()
        data['email'] = 'saiemail'
        response = self.client.post(self.register_url, data)
        print(response.content.decode())
        self.assertContains(response, "Enter a valid email address", status_code=200)

    def test_login_valid(self):
        # Tạo user trước khi login
        Account.objects.create_user(
            first_name='Ky',
            last_name='Vy',
            phone_number='0123456789',
            email='doduckyvy2004@example.com',
            password='123456'
        )
        response = self.client.post(self.login_url, {
            'email': 'doduckyvy2004@example.com',
            'password': '123456'
        })
        self.assertEqual(response.status_code, 302)
