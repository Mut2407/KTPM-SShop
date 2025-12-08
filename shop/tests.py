from django.test import TestCase, Client
from django.urls import reverse
from .models import Product, Category

class ShopTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Giày", slug="giay")
        self.product = Product.objects.create(
            product_name="Nike Air",
            slug="nike-air",
            price=200,
            stock=10,
            category=self.category,
            is_available=True
        )

    # Unit Test: Kiểm tra tính toán trong Model
    def test_product_price(self):
        self.assertEqual(self.product.price, 200)
        self.assertTrue(self.product.is_available)

    # Integration Test: Kiểm tra View chi tiết sản phẩm
    def test_product_detail_view(self):
        # Giả sử url name là 'product_detail'
        url = reverse('product_detail', args=[self.category.slug, self.product.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Kiểm tra xem tên sản phẩm có hiện trên HTML không
        self.assertContains(response, "Nike Air")