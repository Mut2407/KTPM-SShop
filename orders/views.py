import json
import datetime
import hashlib, hmac

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from cart.models import CartItem, Cart
from cart.views import _cart_id
from django.core.exceptions import ObjectDoesNotExist
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from shop.models import Product


from urllib.parse import urlencode
from django.conf import settings


def _validate_cart_stock_or_redirect(request, cart_items):
    """Ensure all cart items have available stock. Redirects with messages on failure.
    Returns None when ok, or a redirect response when invalid.
    """
    insufficient = []
    for item in cart_items:
        if item.product.stock == 0 or item.quantity > item.product.stock:
            insufficient.append((item.product, item.product.stock))
    if insufficient:
        for product, stock in insufficient:
            if stock == 0:
                messages.error(request, f'{product.name} đã hết hàng. Vui lòng xóa khỏi giỏ để tiếp tục.')
            else:
                messages.error(request, f'{product.name}: chỉ còn {stock} sản phẩm. Vui lòng điều chỉnh số lượng.')
        return redirect('cart:cart')
    return None

@login_required(login_url='accounts:login')
def payment_method(request):
    cart_items = CartItem.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.error(request, "Giỏ hàng trống.")
        return redirect("cart:cart")

    # Validate stock before choosing payment method
    resp = _validate_cart_stock_or_redirect(request, cart_items)
    if resp:
        return resp

    if request.method == "POST":
        method = request.POST.get("payment_method")

        # TÍNH TIỀN
        total_price = sum(item.product.price * item.quantity for item in cart_items)
        vat = round(total_price * 0.02, 2)
        handing = 15
        total = total_price + vat + handing

        # TẠO ORDER
        order = Order.objects.create(
            user=request.user,
            order_number=timezone.now().strftime("%Y%m%d%H%M%S"),
            order_total=total,
            tax=vat,
            status="PENDING",
        )

        # COD → HOÀN TẤT NGAY
        if method == "COD":
            return complete_cod_payment(request, order)

        # VNPAY → CHUYỂN TỚI TRANG THANH TOÁN
        if method == "VNPAY":
            return redirect(f"/orders/vnpay-payment/?order_number={order.order_number}")

    return render(request, 'shop/orders/payment_method.html')


@login_required(login_url = 'accounts:login')
def checkout(request,total=0, total_price=0, quantity=0, cart_items=None):
    tax = 0.00
    handing = 0.00

    # ----- Tính toán giỏ hàng -----
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total_price += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity

    except ObjectDoesNotExist:
        pass

    tax = round(((2 * total_price) / 100), 2)
    handing = 15.00
    grand_total = total_price + tax
    total = float(grand_total) + handing

    # ----------XỬ LÝ POST THANH TOÁN ----------
    if request.method == "POST":
        # Validate stock before creating order
        ci = CartItem.objects.filter(user=request.user) if request.user.is_authenticated else cart_items
        resp = _validate_cart_stock_or_redirect(request, ci)
        if resp:
            return resp
        # Tạo order trước khi chuyển đến VNPAY Fake
        order = Order.objects.create(
            user = request.user if request.user.is_authenticated else None,
            order_number = timezone.now().strftime("%Y%m%d%H%M%S"),
            order_total = total,
            tax = tax,
            status = "PENDING"
        )

        # URL → Fake VNPAY
        vnpay_url = f"/orders/vnpay_payment/?order_number={order.order_number}"
        return redirect(vnpay_url)

    # ---------- Trả về HTML nếu là GET ----------
    context = {
        'total_price': total_price,
        'quantity': quantity,
        'cart_items': cart_items,
        'handing': handing,
        'vat': tax,
        'order_total': total,
    }
    return render(request, 'shop/orders/checkout/checkout.html', context)


@login_required(login_url = 'accounts:login')
def payment(request, total=0, quantity=0):
    current_user = request.user
    handing = 15.0
    # if the cart cout less than 0 , redirect to shop page 
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0 :
        return redirect('shop:shop')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = round(((2 * total)/100), 2)

    grand_total = total + tax
    handing = 15.00
    total = float(grand_total) + handing
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # shop all the billing information inside Order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address = form.cleaned_data['address']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") #20210305
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()


            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'handing': handing,
                'vat': tax,
                'order_total': total,
            }
            return render(request, 'shop/orders/checkout/payment.html', context)
        else:
            messages.error(request, 'YOur information not Vailed')
            return redirect('orders:checkout')
            
    else:
        return redirect('shop:shop')


def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    
    # Validate stock before capturing payment and creating order products
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        if item.product.stock == 0 or item.quantity > item.product.stock:
            return JsonResponse({'error': 'Sản phẩm hết hàng hoặc không đủ số lượng.'}, status=400)

    # Store transation details inside payment model 
    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        status = body['status'],
        amount_paid = order.order_total,
    )
    
    payment.save()

    order.payment = payment
    order.is_ordered = True
    order.save()
    
    # Move the cart item to OrderProduct table 
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        orderproduct = OrderProduct()
        orderproduct.order_id = order.id
        orderproduct.payment = payment
        orderproduct.user_id = request.user.id
        orderproduct.product_id = item.product_id
        orderproduct.quantity = item.quantity
        orderproduct.product_price = item.product.price
        orderproduct.ordered = True
        orderproduct.save()
        
        # add variation to OrderProduct table
        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variation.all()
        orderproduct = OrderProduct.objects.get(id=orderproduct.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

        
        # Reduce the quantity of the sold products
        product = Product.objects.get(id=item.product_id)
        # Reduce the quantity of the sold products safely
        product.stock = max(0, product.stock - item.quantity)
        product.save()

    # Clear Cart 
    CartItem.objects.filter(user=request.user).delete()

    
    # Send order recieved email to cutomer 
    #subject = 'Thank you for your order!'
    #message = render_to_string('shop/orders/checkout/payment_recieved_email.html', {
    #    'user': request.user,
    #    'order':order,
    #})
    #to_email = request.user.email
    #send_email = EmailMessage(subject, message, to=[to_email])
    #send_email.send()
#
    #
    ## Send order recieved email to admin account 
    #subject = 'Thank you for your order!'
    #message = render_to_string('shop/orders/checkout/payment_recieved_email.html', {
    #    'user': request.user,
    #    'order':order,
    #})
    #to_email = request.user.email
    #send_email = EmailMessage(subject, message, to=['eshopsuppo@gmail.com'])
    #send_email.send()

    # Send order number and transation id back to sendDate method via JavaResponse
    data = {
            'order_number': order.order_number,
            'transID': payment.payment_id,
        }
    return JsonResponse(data)


# def order_completed(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotall = 0
        for i in ordered_products:
            subtotall += i.product_price * i.quantity
        subtotal = round(subtotall, 2)
        payment = Payment.objects.get(payment_id=transID)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': payment.payment_id,
            'payment': payment,
            'subtotal': subtotal,
        }
        return render(request, 'shop/orders/order_completed/order_completed.html', context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('shop:shop')
    
def order_completed(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    order = get_object_or_404(Order, order_number=order_number, is_ordered=True)
    ordered_products = OrderProduct.objects.filter(order_id=order.id)
    payment = get_object_or_404(Payment, payment_id=transID)

    subtotal = sum([item.product_price * item.quantity for item in ordered_products])

    context = {
        'order': order,
        'ordered_products': ordered_products,
        'order_number': order.order_number,
        'transID': payment.payment_id,
        'payment': payment,
        'subtotal': round(subtotal, 2),
    }
    return render(request, 'shop/orders/order_completed/order_completed.html', context)

@login_required(login_url='accounts:login')
def vnpay_payment(request):
    order_number = request.GET.get("order_number")

    # Lấy đơn hàng trong DB (nếu bạn có model Order)
    order = Order.objects.get(order_number=order_number)

    return_url = request.build_absolute_uri("/orders/vnpay-return/")

    context = {
        "order_number": order_number,
        "order_description": "Thanh toán đơn hàng #" + order_number,
        "amount": int(order.order_total),  # tổng tiền cần thanh toán
        "return_url": return_url,
    }

    return render(request, "shop/orders/vnpay_payment.html", context)


@login_required(login_url='accounts:login')
def vnpay_return(request):
    response_code = request.GET.get("vnp_ResponseCode")
    order_number = request.GET.get("vnp_TxnRef")

    try:
        order = Order.objects.get(order_number=order_number)
    except:
        return redirect("/?payment=notfound")

    # Code 00 = Thanh toán thành công
    if response_code == "00":
        # Validate stock again before finalizing
        cart_items = CartItem.objects.filter(user=request.user)
        resp = _validate_cart_stock_or_redirect(request, cart_items)
        if resp:
            order.status = "FAILED"
            order.save()
            return resp

        # ---- ĐÁNH DẤU ĐƠN HÀNG ĐÃ MUA ----
        order.status = "PAID"
        order.is_ordered = True     #  <<<<<< IMPORTANT
        order.save()

        # ---- CHUYỂN SẢN PHẨM TỪ CART -> ORDER PRODUCT ----
        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            OrderProduct.objects.create(
                order=order,
                user=request.user,
                product=item.product,
                quantity=item.quantity,
                product_price=item.product.price,
                ordered=True
            )

            # Giảm kho sản phẩm
            product = item.product
            product.stock = max(0, product.stock - item.quantity)
            product.save()

        # Xóa giỏ hàng sau khi đặt hàng
        CartItem.objects.filter(user=request.user).delete()

        return redirect("/")
    else:
        order.status = "FAILED"
        order.save()
        return redirect("/?payment=failed")


def complete_cod_payment(request, order):
    cart_items = CartItem.objects.filter(user=request.user)

    resp = _validate_cart_stock_or_redirect(request, cart_items)
    if resp:
        order.status = "FAILED"
        order.save()
        return resp

    payment = Payment.objects.create(
        user=request.user,
        payment_method="COD",
        payment_id=f"COD-{order.order_number}",
        status="SUCCESS",
        amount_paid=order.order_total,
    )

    order.payment = payment
    order.is_ordered = True
    order.status = "PAID"
    order.save()

    for item in cart_items:
        OrderProduct.objects.create(
            order=order,
            payment=payment,
            user=request.user,
            product=item.product,
            quantity=item.quantity,
            product_price=item.product.price,
            ordered=True,
        )

        product = item.product
        product.stock -= item.quantity
        product.save()

    cart_items.delete()

    messages.success(request, "Thanh toán COD thành công!")
    return redirect("/")


@login_required(login_url='accounts:login')
def cod_payment(request):
    # Handle AJAX POST from payment.html
    if request.method == 'POST':
        try:
            payload = {}
            if request.body:
                payload = json.loads(request.body)
            order_number = payload.get('order_number')

            if order_number:
                order = Order.objects.filter(user=request.user, order_number=order_number, is_ordered=False).first()
            else:
                order = Order.objects.filter(user=request.user, is_ordered=False, status="PENDING").order_by('-id').first()

            if not order:
                return JsonResponse({'status': 'error', 'message': 'Không tìm thấy đơn hàng để thanh toán COD.'}, status=400)

            # Complete COD payment using helper (returns a RedirectResponse we ignore)
            complete_cod_payment(request, order)

            # Build order info for client modal and redirect to order completed page
            payment_id = f"COD-{order.order_number}"
            redirect_url = f"/orders/order_completed/?order_number={order.order_number}&payment_id={payment_id}"

            items_count = OrderProduct.objects.filter(order=order).count()

            return JsonResponse({
                'status': 'success',
                'redirect_url': redirect_url,
                'order_number': order.order_number,
                'amount': float(order.order_total),
                'items': items_count,
                'payment_id': payment_id,
                'payment_method': 'COD'
            })
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Thanh toán COD thất bại.'}, status=500)

    # Fallback: redirect to checkout when not POST
    return redirect('orders:checkout')
