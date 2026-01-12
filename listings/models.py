"""
Models for the ALX Travel App listings system.
Defines Property, Booking, and Review models with appropriate relationships.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class CustomUser(AbstractUser):
    role = models.CharField(
        max_length=20, 
        choices=[('host', 'Host'), ('guest', 'Guest')],
        default = 'guest'
    )


class Listing(models.Model):
    """
    Property/Listing model representing accommodations available for booking.
    
    Relationships:
    - Belongs to a User (host) via host_id
    - Has many Bookings
    - Has many Reviews
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )
    
    name = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="Property name/title"
    )
    
    description = models.TextField(
        null=False,
        blank=False,
        help_text="Detailed description of the property"
    )

    host = models.ForeignKey(
        CustomUser,
        on_delete=models.DO_NOTHING,
        related_name = 'owner'
    )

    location = models.CharField(
        max_length=255,
        null=False,
        blank=False,
        help_text="Property location/address"
    )
    
    pricepernight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        validators=[MinValueValidator(0.01)],
        help_text="Price per night in USD"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when property was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when property was last updated"
    )
    
    class Meta:
        db_table = 'properties'
        verbose_name = 'Property'
        verbose_name_plural = 'Properties'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['id']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.location}"
    
    def get_average_rating(self):
        """Calculate average rating from all reviews"""
        reviews = self.reviews.all()
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return None
    
    def get_total_reviews(self):
        """Get total number of reviews"""
        return self.reviews.count()
    
    def is_available(self, start_date, end_date):
        """Check if property is available for given date range"""
        conflicting_bookings = self.bookings.filter(
            models.Q(start_date__lte=end_date) & models.Q(end_date__gte=start_date),
            status__in=['pending', 'confirmed']
        )
        return not conflicting_bookings.exists()


class Booking(models.Model):
    """
    Booking model representing a reservation for a property.
    
    Relationships:
    - Belongs to a Property via property_id
    - Belongs to a User (guest) via user_id
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Unique identifier for the booking"
    )
    
    property = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='bookings',
        help_text="The property being booked"
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.DO_NOTHING,
        related_name='bookings',
        help_text="The user making the booking"
    )
    
    start_date = models.DateField(
        null=False,
        blank=False,
        help_text="Check-in date"
    )
    
    end_date = models.DateField(
        null=False,
        blank=False,
        help_text="Check-out date"
    )
    
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        validators=[MinValueValidator(0.01)],
        help_text="Total price for the entire stay"
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        null=False,
        db_index=True,
        help_text="Current status of the booking"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when booking was created"
    )
    
    class Meta:
        db_table = 'bookings'
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['property']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F('start_date')),
                name='end_date_after_start_date'
            ),
            models.CheckConstraint(
                check=models.Q(total_price__gt=0),
                name='total_price_positive'
            ),
        ]
    
    def __str__(self):
        return f"Booking {self.booking_id} - {self.property.name} ({self.status})"
    
    def clean(self):
        """Validate booking dates and availability"""
        from django.core.exceptions import ValidationError
        
        # Validate end_date is after start_date
        if self.end_date <= self.start_date:
            raise ValidationError({
                'end_date': 'End date must be after start date.'
            })
        
        # Validate dates are not in the past
        if self.start_date < timezone.now().date():
            raise ValidationError({
                'start_date': 'Start date cannot be in the past.'
            })
        
        # Check property availability (exclude current booking if updating)
        if not self.property.is_available(self.start_date, self.end_date):
            if self._state.adding or not Booking.objects.filter(
                booking_id=self.booking_id,
                start_date=self.start_date,
                end_date=self.end_date
            ).exists():
                raise ValidationError({
                    'property': 'Property is not available for the selected dates.'
                })
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def calculate_total_price(self):
        """Calculate total price based on number of nights and price per night"""
        nights = (self.end_date - self.start_date).days
        return nights * self.property.pricepernight
    
    def get_number_of_nights(self):
        """Get number of nights for this booking"""
        return (self.end_date - self.start_date).days
    
    def can_cancel(self):
        """Check if booking can be canceled"""
        return self.status in ['pending', 'confirmed'] and self.start_date > timezone.now().date()


class Review(models.Model):
    """
    Review model representing guest feedback for a property.
    
    Relationships:
    - Belongs to a Property via property_id
    - Belongs to a User (reviewer) via user_id
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Unique identifier for the review"
    )
    
    property = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The property being reviewed"
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The user writing the review"
    )
    
    rating = models.IntegerField(
        null=False,
        validators=[
            MinValueValidator(1, message="Rating must be at least 1"),
            MaxValueValidator(5, message="Rating must be at most 5")
        ],
        help_text="Rating from 1 to 5 stars"
    )
    
    comment = models.TextField(
        null=False,
        blank=False,
        help_text="Review comment/feedback"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when review was created"
    )
    
    class Meta:
        db_table = 'reviews'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['property']),
            models.Index(fields=['user']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='rating_range_1_to_5'
            ),
            # Ensure user can only review a property once
            models.UniqueConstraint(
                fields=['property', 'user'],
                name='unique_user_property_review'
            ),
        ]
    
    def __str__(self):
        return f"Review by {self.user.email} for {self.property.name} - {self.rating}★"
    
    def clean(self):
        """Validate that user has completed a booking before reviewing"""
        from django.core.exceptions import ValidationError
        
        # Check if user has a confirmed booking for this property
        completed_bookings = Booking.objects.filter(
            user=self.user,
            property=self.property,
            status='confirmed',
            end_date__lt=timezone.now().date()
        )
        
        if not completed_bookings.exists():
            raise ValidationError({
                'user': 'You can only review properties you have stayed at.'
            })
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.full_clean()
        super().save(*args, **kwargs)



class Payment(models.Model):
    """
    Payment model representing payment details for a booking

    Relationship:
    - ManytoOne with the booking model

    """

    CREATED='CREATED'
    PROCESSING='PROCESSING'
    COMPLETE='COMPLETE'
    FAILED='FAILED'

    PAYMENT_STATUS=[
        (CREATED, 'Created'),
        (FAILED, 'Failed'),
        (PROCESSING, 'Processing'),
        (COMPLETE, 'Complete')
    ]


    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    booking_ref = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.FloatField()
    currency = models.CharField(max_length=25, default='ETB')
    email = models.EmailField()
    phone_number = models.CharField(max_length=25)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(
        max_length=50,
        choices=PAYMENT_STATUS,
        default=CREATED
    )
    response_dump = models.JSONField(default=dict, blank=True) 
    checkout_url = models.URLField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.first_name} - {self.last_name} | {self.amount}"
    
    def serialize(self) -> dict:
        return {
            'amount': self.amount,
            'currency': self.currency,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'description': self.description,
            'status': self.status,
            'checkout_url': self.checkout_url
        }
