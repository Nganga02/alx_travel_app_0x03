from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView


from . import serializers
from .models import Listing, Booking, Payment
from .service import ChapaAPIService
from .tasks import send_booking_confirmation_email



class ListingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ListingSerializer
    queryset = Listing.objects.all()

    #Using 'detail = True' inidcates retrieving a specific object
    @action(detail=True, methods = ['get'])
    def availability(self, request, pk=None):
        listing = self.get_object()
        start = request.query_params.get('start_date')
        end = request.query_params.get('end_date')

        return Response({
            'property_name': listing.name,
            'is_available': listing.is_available(start, end)
        })


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings.
    Supports CRUD operations.
    """
    queryset = Booking.objects.all()
    serializer_class = serializers.BookingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        Optionally attach the authenticated user to the booking
        """
        booking=serializer.save(user=self.request.user)

        send_booking_confirmation_email.delay(
            recipient_email=booking.user.email,
            booking_id=booking.id,
        )


class PaymentView(APIView):
    """
    Initialize a payment with Chapa
    """

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)

        serializer = serializers.PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = serializer.save(
            booking_ref=booking,
            status=Payment.CREATED
        )

        chapa_response = ChapaAPIService.send_request(payment)

        if chapa_response.get("status") != "success":
            payment.status = Payment.FAILED
            payment.save()

            return Response(
                {
                    "error": "Payment initialization failed",
                    "details": chapa_response
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "checkout_url": payment.checkout_url,
                "payment_id": payment.id
            },
            status=status.HTTP_201_CREATED
        )
    


class VerifyPaymentView(APIView):
    """
    Verify payment status with Chapa
    """

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)

        response = ChapaAPIService.verify_payment(payment)
        print('************api service************')
        print(response)

        if response.data.get("status") == "success":
            payment.status = Payment.COMPLETE
        else:
            payment.status = Payment.FAILED

        payment.response_dump = response
        payment.save()

        return Response(
            {
                "payment_id": payment.id,
                "status": payment.status,
                "gateway_response": response
            },
            status=status.HTTP_200_OK
        )
