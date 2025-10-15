# KTPM-SShop

Trang web bán đồ thể thao

# Chức năng chính của web
<I>User

1. Đăng nhập / Đăng ký
2. Tìm kiếm
3. Thêm sản phẩm vào giỏ hàng
4. Thanh toán (Checkout)
5. Xem đơn hàng
6. Đánh giá sản phẩm

<II>Superuser - Admin
1. Quản lý sản phẩm (Shop)
2. Quản lý đơn hàng
3. Quản lý người dùng
4. Quản lý đánh giá
5. Quản lý giỏ hàng

# Run the project

1. clone this repo

```bash
git clone <this_repo>
```

2. install virtualenv

```bash
pip install virtualenv
```

3. create new virtual environment

```bash
py -m venv venv
```

4. activate the new virtual

```bash
.\venv\Scripts\activate
```

5. install requirements.txt

```bash
pip install -r requirements.txt
```

6. run local server to begin

```bash
py manage.py runserver
```

7.  go live with [localhost:8000](http://localhost:8000/)

 <br>

# To login with superuser and access admin panel

1.  run on terminal

```bash
py manage.py createsuperuser
```

2.  create new admin user
3.  go to [localhost:8000/admin](http://localhost:8000/admin)
