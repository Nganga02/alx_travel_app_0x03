"""
Serializers for the ALX Travel App listings system.
Handles serialization and deserialization of Listing, Booking, and Review models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import Listing, Booking, Review, Payment



class ListingSerializer(serializers.ModelSerializer):
    """
    Serializer for Listing/Listing model.
    Handles property creation, updates, and representation.
    """
    
    # Read-only fields
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Nested serializer for host information (read-only)
    host_email = serializers.EmailField(source='host.email', read_only=True)
    host_name = serializers.SerializerMethodField()
    
    # Computed fields
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'name',
            'location',
            'pricepernight',
            'total_reviews',
        ]
        read_only_fields = ['property_id', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'description': {'required': True, 'allow_blank': False},
            'location': {'required': True, 'allow_blank': False},
            'pricepernight': {'required': True, 'min_value': 0.01},
        }
    
    
    def get_average_rating(self, obj):
        """Get average rating for the property"""
        return obj.get_average_rating()
    
    def get_total_reviews(self, obj):
        """Get total number of reviews"""
        request = self.context.get("request")
        start_date = request.query_params.get("start_date")
        end_data = request.query_params.get('end_date')
        return obj.get_total_reviews()
    
    def validate_pricepernight(self, value):
        """Validate price per night is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price per night must be greater than 0")
        return value
    
    def create(self, validated_data):
        """Create a new property"""
        # Set host to current user if not provided
        if 'host' not in validated_data:
            validated_data['host'] = self.context['request'].user
        
        return Listing.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        """Update property details"""
        # Don't allow changing the host
        validated_data.pop('host', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking model.
    Handles booking creation, updates, and validation.
    """
    
    # Read-only fields
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    # Nested serializers (read-only for GET requests)
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_location = serializers.CharField(source='property.location', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    # Computed fields
    number_of_nights = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'property',
            'property_name',
            'property_location',
            'user',
            'user_email',
            'start_date',
            'end_date',
            'number_of_nights',
            'total_price',
            'status',
            'created_at',
        ]
        read_only_fields = ['booking_id', 'created_at', 'total_price']
        extra_kwargs = {
            'start_date': {'required': True},
            'end_date': {'required': True},
            'status': {'required': False},
        }
    
    def get_number_of_nights(self, obj):
        """Calculate number of nights"""
        return obj.get_number_of_nights()
    
    def validate(self, data):
        """Validate booking data"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        property_obj = data.get('property')
        
        # Validate dates
        if end_date <= start_date:
            raise serializers.ValidationError({
                'end_date': 'End date must be after start date'
            })
        
        # Validate start date is not in the past
        if start_date < timezone.now().date():
            raise serializers.ValidationError({
                'start_date': 'Start date cannot be in the past'
            })
        
        # Validate property availability
        if property_obj and not property_obj.is_available(start_date, end_date):
            raise serializers.ValidationError({
                'property': 'Listing is not available for the selected dates'
            })
        
        return data
    
    def create(self, validated_data):
        """Create a new booking"""
        # Set user to current user if not provided
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        
        # Calculate total price
        booking = Booking(**validated_data)
        booking.total_price = booking.calculate_total_price()
        booking.save()
        
        return booking
    
    def update(self, instance, validated_data):
        """Update booking details"""
        # Don't allow changing property or user
        validated_data.pop('property', None)
        validated_data.pop('user', None)
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalculate total price if dates changed
        if 'start_date' in validated_data or 'end_date' in validated_data:
            instance.total_price = instance.calculate_total_price()
        
        instance.save()
        return instance


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Review model.
    Handles review creation and representation.
    """
    
    # Read-only fields
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    # Nested serializers
    property_name = serializers.CharField(source='property.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id',
            'property',
            'property_name',
            'user',
            'user_email',
            'user_name',
            'rating',
            'comment',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {
            'rating': {'required': True, 'min_value': 1, 'max_value': 5},
            'comment': {'required': True, 'allow_blank': False},
        }
    
    def get_user_name(self, obj):
        """Get reviewer's name"""
        if hasattr(obj.user, 'first_name') and hasattr(obj.user, 'last_name'):
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.email
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate(self, data):
        """Validate that user has stayed at the property"""
        user = self.context['request'].user
        property_obj = data.get('property')
        
        # Check if user has completed booking for this property
        completed_bookings = Booking.objects.filter(
            user=user,
            property=property_obj,
            status='confirmed',
            end_date__lt=timezone.now().date()
        )
        
        if not completed_bookings.exists():
            raise serializers.ValidationError({
                'property': 'You can only review properties you have stayed at'
            })
        
        # Check if user has already reviewed this property
        if Review.objects.filter(user=user, property=property_obj).exists():
            if not self.instance:  # Only check on creation, not update
                raise serializers.ValidationError({
                    'property': 'You have already reviewed this property'
                })
        
        return data
    
    def create(self, validated_data):
        """Create a new review"""
        # Set user to current user if not provided
        if 'user' not in validated_data:
            validated_data['user'] = self.context['request'].user
        
        return Review.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        """Update review details"""
        # Don't allow changing property or user
        validated_data.pop('property', None)
        validated_data.pop('user', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


# Detailed serializers for nested representations

class ListingDetailSerializer(ListingSerializer):
    """
    Extended Listing serializer with nested bookings and reviews.
    Used for detailed property view.
    """
    reviews = ReviewSerializer(many=True, read_only=True)
    bookings_count = serializers.SerializerMethodField()
    
    class Meta(ListingSerializer.Meta):
        fields = ListingSerializer.Meta.fields + ['reviews', 'bookings_count']
    
    def get_bookings_count(self, obj):
        """Get total number of bookings for this property"""
        return obj.bookings.filter(status='confirmed').count()


class BookingDetailSerializer(BookingSerializer):
    """
    Extended Booking serializer with full property and user details.
    Used for detailed booking view.
    """
    property_details = ListingSerializer(source='property', read_only=True)
    
    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + ['property_details']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'amount',
            'currency',
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'description'
        ]