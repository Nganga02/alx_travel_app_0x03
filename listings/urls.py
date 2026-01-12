from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ListingViewSet, PaymentView, VerifyPaymentView

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')


urlpatterns = [
    path("",include(router.urls)),
    path(
        "bookings/<uuid:booking_id>/pay/",
        PaymentView.as_view(),
        name="initiate-payment"
    ),
    path(
        "payments/<uuid:payment_id>/verify/",
        VerifyPaymentView.as_view(),
        name="verify-payment"
    ),
]

