from django.urls import path
from .views import checkout, payment_success, payment_cancel, process_payment

urlpatterns = [
    path('', checkout, name='checkout'),
    path('payment/success/', payment_success, name='payment_success'),
    path('payment/cancel/', payment_cancel, name='payment_cancel'),
    path('process-payment/', process_payment, name='process_payment'),
]