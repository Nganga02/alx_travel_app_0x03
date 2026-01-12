"""
Management command to seed the database with sample data for testing.
Usage: python manage.py seed
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from listings.models import Listing, Booking, Review

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with sample data for Properties, Bookings, and Reviews'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )
        parser.add_argument(
            '--properties',
            type=int,
            default=20,
            help='Number of properties to create',
        )
        parser.add_argument(
            '--bookings',
            type=int,
            default=30,
            help='Number of bookings to create',
        )
        parser.add_argument(
            '--reviews',
            type=int,
            default=25,
            help='Number of reviews to create',
        )
    
    def create_users(self, count):
        """Create sample users (hosts & guests)"""
        self.stdout.write(f'\nCreating {count} users...')

        users = []
        roles = ['host', 'guest']

        for i in range(count):
            try:
                role = random.choice(roles)
                user = User.objects.create_user(
                    email=f"user{i}@example.com",
                    username=f"user{i}",
                    password="password123",
                )

                # If your User model has a 'role' field
                if hasattr(user, 'role'):
                    user.role = role
                    user.save()

                users.append(user)
                self.stdout.write(f"  ✓ Created user: {user.email} ({role})")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to create user: {str(e)}"))

        return users

    
    def handle(self, *args, **options):
        """Main command handler"""
        
        # Clear existing data if flag is set
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Review.objects.all().delete()
            Booking.objects.all().delete()
            Listing.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Data cleared'))
        
            
        # Seed data
        self.stdout.write('Starting database seeding...')
        
        users = self.create_users(options['users'])
        properties = self.create_properties(users, options['properties'])
        bookings = self.create_bookings(users, properties, options['bookings'])
        reviews = self.create_reviews(users, properties, bookings, options['reviews'])
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'✓ Users created: {len(users)}')
        self.stdout.write(f'✓ Properties created: {len(properties)}')
        self.stdout.write(f'✓ Bookings created: {len(bookings)}')
        self.stdout.write(f'✓ Reviews created: {len(reviews)}')
        self.stdout.write(self.style.SUCCESS('='*50 + '\n'))

    
    def create_properties(self, users, count):
        """Create sample properties"""
        self.stdout.write(f'\nCreating {count} properties...')
        
        properties = []
        
        # Get hosts (users with host role)
        hosts = [u for u in users if hasattr(u, 'role') and u.role == 'host']
        if not hosts:
            hosts = users[:len(users)//2]  # Use first half as hosts if no role field
        
        # Sample data
        property_types = ['Cozy', 'Luxury', 'Modern', 'Charming', 'Spacious', 'Beautiful', 'Stunning', 'Elegant']
        property_names = ['Villa', 'Apartment', 'Condo', 'House', 'Studio', 'Loft', 'Cottage', 'Penthouse']
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'Miami']
        
        descriptions = [
            'A wonderful place to stay with all modern amenities.',
            'Perfect for families and groups looking for comfort.',
            'Located in the heart of the city with easy access to attractions.',
            'Quiet neighborhood with beautiful views.',
            'Fully furnished with high-speed internet and parking.',
            'Recently renovated with stylish decor.',
            'Close to restaurants, shops, and entertainment.',
            'Pet-friendly accommodation with outdoor space.',
        ]
        
        for i in range(count):
            property_type = random.choice(property_types)
            property_name = random.choice(property_names)
            city = random.choice(cities)
            
            try:
                property_obj = Listing.objects.create(
                    host=random.choice(hosts),
                    name=f"{property_type} {property_name} in {city}",
                    description=random.choice(descriptions),
                    location=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Maple', 'Pine'])} St, {city}",
                    pricepernight=Decimal(str(random.randint(50, 500)))
                )
                properties.append(property_obj)
                self.stdout.write(f'  ✓ Created property: {property_obj.name}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to create property: {str(e)}'))
        
        return properties
    
    def create_bookings(self, users, properties, count):
        """Create sample bookings"""
        self.stdout.write(f'\nCreating {count} bookings...')
        
        bookings = []
        created_count = 0
        
        # Get guests
        guests = [u for u in users if hasattr(u, 'role') and u.role == 'guest']
        if not guests:
            guests = users[len(users)//2:]  # Use second half as guests
        
        statuses = ['pending', 'confirmed', 'confirmed', 'confirmed', 'canceled']  # More confirmed
        
        for i in range(count):
            try:
                guest = random.choice(guests)
                property_obj = random.choice(properties)
                
                # Generate random dates
                days_ahead = random.randint(1, 90)
                start_date = timezone.now().date() + timedelta(days=days_ahead)
                nights = random.randint(1, 14)
                end_date = start_date + timedelta(days=nights)
                
                # Calculate total price
                total_price = property_obj.pricepernight * nights
                
                # Check if property is available (simple check)
                if property_obj.is_available(start_date, end_date):
                    booking = Booking.objects.create(
                        property=property_obj,
                        user=guest,
                        start_date=start_date,
                        end_date=end_date,
                        total_price=total_price,
                        status=random.choice(statuses)
                    )
                    bookings.append(booking)
                    created_count += 1
                    
                    self.stdout.write(f'  ✓ Created booking: {guest.email} → {property_obj.name} ({start_date} to {end_date})')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to create booking: {str(e)}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created {created_count}/{count} bookings.')
        )
        return bookings
                                  

    def create_reviews(self, users, properties, bookings, count):
        """Create sample reviews"""
        self.stdout.write(f'\nCreating {count} reviews...')
        
        reviews = []
        
        # Get confirmed bookings that have ended
        past_bookings = [
            b for b in bookings 
            if b.status == 'confirmed' and b.end_date < timezone.now().date()
        ]
        
        # Sample comments
        positive_comments = [
            'Amazing place! Highly recommend.',
            'Great location and very clean.',
            'Perfect for our vacation. Will definitely come back!',
            'The host was very responsive and helpful.',
            'Beautiful property with all the amenities we needed.',
            'Exceeded our expectations in every way.',
            'Wonderful experience from start to finish.',
            'Could not have asked for a better place to stay.',
        ]
        
        neutral_comments = [
            'Good place overall, but could use some improvements.',
            'Decent accommodation for the price.',
            'Met our basic needs.',
            'Average experience, nothing special.',
        ]
        
        negative_comments = [
            'Not as described in the listing.',
            'Had some issues with cleanliness.',
            'Location was not ideal.',
            'Would not recommend.',
        ]
        
        # Create reviews from past bookings
        created_count = 0
        for i in range(min(count, len(past_bookings))):
            booking = random.choice(past_bookings)
            
            try:
                # Check if user has already reviewed this property
                existing_review = Review.objects.filter(
                    user=booking.user,
                    property=booking.property
                ).exists()
                
                if not existing_review:
                    rating = random.randint(1, 5)
                    
                    # Select comment based on rating
                    if rating >= 4:
                        comment = random.choice(positive_comments)
                    elif rating == 3:
                        comment = random.choice(neutral_comments)
                    else:
                        comment = random.choice(negative_comments)
                    
                    review = Review.objects.create(
                        property=booking.property,
                        user=booking.user,
                        rating=rating,
                        comment=comment
                    )
                    reviews.append(review)
                    created_count += 1
                    self.stdout.write(f'  ✓ Created review: {booking.user.email} → {booking.property.name} ({rating}★)')
                
                # Remove booking from list to avoid duplicate reviews
                past_bookings.remove(booking)
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠ Skipped review: {str(e)}'))
        
        # If we need more reviews, create some from available combinations
        if created_count < count:
            remaining = count - created_count
            self.stdout.write(f'\n  Creating {remaining} additional reviews...')
            
            for i in range(remaining):
                try:
                    # Find a guest who hasn't reviewed a property
                    guest = random.choice(users)
                    property_obj = random.choice(properties)
                    
                    # Check if review already exists
                    if not Review.objects.filter(user=guest, property=property_obj).exists():
                        # Create a past booking first (backdated)
                        days_ago = random.randint(7, 60)
                        end_date = timezone.now().date() - timedelta(days=days_ago)
                        start_date = end_date - timedelta(days=random.randint(1, 7))
                        
                        booking = Booking.objects.create(
                            property=property_obj,
                            user=guest,
                            start_date=start_date,
                            end_date=end_date,
                            total_price=property_obj.pricepernight * (end_date - start_date).days,
                            status='confirmed'
                        )
                        
                        rating = random.randint(1, 5)
                        if rating >= 4:
                            comment = random.choice(positive_comments)
                        elif rating == 3:
                            comment = random.choice(neutral_comments)
                        else:
                            comment = random.choice(negative_comments)
                        
                        review = Review.objects.create(
                            property=property_obj,
                            user=guest,
                            rating=rating,
                            comment=comment
                        )
                        reviews.append(review)
                        self.stdout.write(f'  ✓ Created review: {guest.email} → {property_obj.name} ({rating}★)')
                
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Skipped additional review: {str(e)}'))
        
        return reviews