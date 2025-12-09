import json
import datetime
import hashlib, hmac
from urllib.parse import urlencode, quote_plus

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from cart.models import CartItem, Cart
from cart.views import _cart_id
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
from shop.models import Product

@login_required(login_url='accounts:login')
def payment_method(request):
    return render(request, 'shop/orders/payment_method.html',)

@login_required(login_url='accounts:login')
def checkout(request, total=0, total_price=0, quantity=0, cart_items=None):
    tax = 0.00
    handing = 0.00
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total_price += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        total = total_price + 10
    except ObjectDoesNotExist:
        pass 
    
    tax = round(((2 * float(total_price))/100), 2)
    grand_total = float(total_price) + tax
    handing = 15.00
    total = grand_total + handing
    
    context = {
        'total_price': total_price, 'quantity': quantity, 'cart_items': cart_items,
        'handing': handing, 'vat': tax, 'order_total': total,
    }
    return render(request, 'shop/orders/checkout/checkout.html', context)

@login_required(login_url='accounts:login')
def payment(request, total=0, quantity=0):
    current_user = request.user
    handing = 15.0
    cart_items = CartItem.objects.filter(user=current_user)
    if cart_items.count() <= 0: return redirect('shop:shop')
    
    grand_total = 0; tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
    
    total_float = float(total)
    tax = round(((2 * total_float)/100), 2)

    final_total = total_float + tax + 15.00
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
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
            data.order_total = final_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            
            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime("%Y%m%d") 
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)
            context = {
                'order': order,
                'cart_items': cart_items,
                'handing': handing,
                'vat': tax,
                'order_total': final_total,
            }
            return render(request, 'shop/orders/checkout/payment.html', context)
        else:
            messages.error(request, 'Your information is not valid')
            return redirect('orders:checkout')
    else:
        return redirect('shop:shop')

# logic vnpay
@login_required(login_url='accounts:login')
def vnpay_payment(request):
    order_number = request.GET.get('order_number')
    order = get_object_or_404(Order, user=request.user, is_ordered=False, order_number=order_number)

    VNP_TMN_CODE = settings.VNPAY_TMN_CODE.strip()
    VNP_HASH_SECRET = settings.VNPAY_HASH_SECRET.strip()
    VNP_URL = settings.VNPAY_URL.strip()
    VNP_RETURN_URL = settings.VNPAY_RETURN_URL.strip()

    amount = int(round(order.order_total * 25000 * 100))
    ipaddr = '127.0.0.1'
    order_desc = f"Order_{order.order_number}" 

    input_data = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': VNP_TMN_CODE,
        'vnp_Amount': str(amount),
        'vnp_CreateDate': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
        'vnp_CurrCode': 'VND',
        'vnp_IpAddr': ipaddr,
        'vnp_Locale': 'vn',
        'vnp_OrderInfo': order_desc,
        'vnp_OrderType': 'other',
        'vnp_ReturnUrl': VNP_RETURN_URL,
        'vnp_TxnRef': order.order_number,
    }

    sorted_data = sorted(input_data.items())
    hash_data = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in sorted_data])
    
    secure_hash = hmac.new(
        VNP_HASH_SECRET.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    query_string = urlencode(sorted_data, quote_via=quote_plus)
    payment_url = f"{VNP_URL}?{query_string}&vnp_SecureHash={secure_hash}"
    return redirect(payment_url)

@login_required(login_url='accounts:login')
def vnpay_return(request):
    inputData = request.GET
    if not inputData: return redirect('shop:shop')
    
    VNP_HASH_SECRET = settings.VNPAY_HASH_SECRET.strip()
    vnp_SecureHash = inputData.get('vnp_SecureHash')
    vnp_ResponseCode = inputData.get('vnp_ResponseCode')
    vnp_TxnRef = inputData.get('vnp_TxnRef') 
    vnp_TransactionNo = inputData.get('vnp_TransactionNo')
    
    data = {}
    for key in inputData.keys():
        if key.startswith('vnp_') and key not in ['vnp_SecureHash', 'vnp_SecureHashType']:
            data[key] = inputData[key]
    sorted_data = sorted(data.items())
    hash_data = '&'.join([f"{k}={v}" for k, v in sorted_data])
    
    secure_hash = hmac.new(
        VNP_HASH_SECRET.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    if secure_hash == vnp_SecureHash:
        if vnp_ResponseCode == '00':
            try:
                order = Order.objects.get(order_number=vnp_TxnRef, is_ordered=False)
                payment = Payment.objects.create(
                    user=request.user, payment_id=vnp_TransactionNo, payment_method='VNPay',
                    status='Completed', amount_paid=order.order_total,
                )
                order.payment = payment
                order.is_ordered = True
                order.save()
                
                _move_cart_to_order(request, order, payment)
                
                return redirect(f'/orders/order_completed/?order_number={order.order_number}&payment_id={payment.payment_id}')
            except Order.DoesNotExist:
                return redirect('shop:shop')
        else:
            messages.error(request, 'Giao dịch không thành công.')
            return redirect('orders:checkout')
    else:
        messages.error(request, 'Sai chữ ký.')
        return redirect('orders:checkout')

# logic cod payment
@login_required(login_url='accounts:login')
def cod_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_number = data.get('order_number')
            
            order = Order.objects.get(user=request.user, order_number=order_number, is_ordered=False)
            
            payment = Payment.objects.create(
                user=request.user,
                payment_id=f"COD-{order_number}", 
                payment_method='COD',
                status='Pending',
                amount_paid=order.order_total,
            )
            
            order.payment = payment
            order.is_ordered = True
            order.save()
            
            _move_cart_to_order(request, order, payment)
            
            redirect_url = f"/orders/order_completed/?order_number={order.order_number}&payment_id={payment.payment_id}"
            return JsonResponse({'status': 'success', 'redirect_url': redirect_url})
            
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return redirect('orders:checkout')

def _move_cart_to_order(request, order, payment):
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        orderproduct = OrderProduct.objects.create(
            order=order, payment=payment, user=request.user,
            product=item.product, quantity=item.quantity,
            product_price=item.product.price, ordered=True,
        )
        orderproduct.variations.set(item.variation.all())
        orderproduct.save()
        
        item.product.stock -= item.quantity
        item.product.save()
    
    cart_items.delete()

def order_completed(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        payment = Payment.objects.get(payment_id=transID)
        subtotal = sum([item.product_price * item.quantity for item in ordered_products])
        context = {
            'order': order, 'ordered_products': ordered_products, 'order_number': order.order_number,
            'transID': payment.payment_id, 'payment': payment, 'subtotal': round(subtotal, 2),
        }
        return render(request, 'shop/orders/order_completed/order_completed.html', context)
    except Exception:
        return redirect('shop:shop')