from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings

def about(request):
    return render(request, 'about.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        send_mail(
            subject=f"Liên hệ từ {name}",
            message=message,
            from_email=email,
            recipient_list=[settings.EMAIL_HOST_USER],
        )
        return render(request, 'contact.html', {'success': True})

    return render(request, 'contact.html')

