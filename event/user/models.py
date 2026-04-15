from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password
import uuid
from cloudinary.models import CloudinaryField

# Create your models here.
class User(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    dob = models.DateField()
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        # Hash password only once
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    
class Event(models.Model):
    event_name = models.CharField(max_length=100)
    event_date = models.DateTimeField()
    event_category = models.CharField(
        max_length=50,
        choices=[
            ('tech', 'Tech'),
            ('music', 'Music'),
            ('sports', 'Sports'),
        ],
        default='tech'
    )
    event_image = CloudinaryField('event_images', folder='event_images',null=True, blank=True)
    event_price = models.PositiveIntegerField()
    event_location = models.CharField(max_length=150)
    total_seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField(default=0)
    event_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def clean(self):
        if self.available_seats > self.total_seats:
            raise ValidationError("Available seats cannot exceed total seats.")
    def save(self, *args, **kwargs):
        self.full_clean()
        if self._state.adding and self.available_seats == 0:
            self.available_seats = self.total_seats
        super().save(*args, **kwargs)
    def __str__(self):
        return self.event_name
    
class Banner(models.Model):
    banner_name = models.CharField(max_length=100)
    banner_image = CloudinaryField('banner_images', folder='banner_images')
    is_active = models.BooleanField()
    def __str__(self):
        return self.banner_name
    
class Bookings(models.Model):
    CHOICES = (
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('passport', 'Passport'),
        ('driving', 'Driving License'),
        ('voter', 'Voter ID')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='bookings')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    age = models.PositiveIntegerField()
    id_proof_type = models.CharField(max_length=20, choices=CHOICES)
    ticket_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    id_proof_image = CloudinaryField('id_proofs', folder='id_proofs')
    booked_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"TKT-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)
    def clean(self):
        if self.age <= 15:
            raise ValidationError("Age must be greater than 15 to book.")
    def __str__(self):
        return self.name