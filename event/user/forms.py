from django import forms
from datetime import date
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import User

common_classes = {
    'class': 'w-full px-4 py-2 rounded-xl border border-gray-300 bg-gray-50 focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition duration-200 shadow-sm'
}

class SignupForm(forms.Form):
    name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Enter your name', **common_classes}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your email', **common_classes}))
    dateOfBirth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'max': date.today().isoformat(), **common_classes}))
    phone = forms.CharField(max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{10,15}$',
                message='Enter a valid phone number'
            )
        ],
        widget=forms.TextInput(attrs={**common_classes})
    )
    password = forms.CharField(min_length=6, widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', **common_classes}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password', **common_classes}))
    # Name validation
    def clean_name(self):
        name = self.cleaned_data['name']
        if not name.replace(" ", "").isalpha():
            raise ValidationError("Name should contain only letters")
        return name
    # Email validation (duplicate check moved here 🔥)
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists")
        return email
    # DOB validation
    def clean_dateOfBirth(self):
        dob = self.cleaned_data['dateOfBirth']
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 13:
            raise ValidationError("Minimum age is 13")
        return dob
    # Password match
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match")
        return cleaned_data
    
class LoginForm(forms.Form):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Enter email', **common_classes}))
    password = forms.CharField(required=True, min_length=6, widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', **common_classes}))

class ProfileForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-style', 'placeholder': 'Enter Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'input-style', 'placeholder': 'Enter email'}))
    dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'input-style'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-style', 'placeholder': 'Enter phone'}))

class EventForm(forms.Form):
    event_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Enter event name', **common_classes}))
    event_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local', **common_classes}))
    CHOICES = (
        ('tech', 'Tech'),
        ('music', 'Music'),
        ('sports', 'Sports'),
    )
    event_category = forms.ChoiceField(choices=CHOICES, widget=forms.Select(attrs={**common_classes}))
    event_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={**common_classes}))
    event_price = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={**common_classes, 'placeholder': 'Enter price'}))
    event_location = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Enter Event Location', **common_classes}))
    total_seats = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={**common_classes, 'placeholder': 'Enter Total Seats'}))
    available_seats = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={**common_classes, 'placeholder': 'Enter Available Seats'}))
    event_description = forms.CharField(widget=forms.Textarea(attrs={**common_classes, 'rows': 4, 'placeholder': 'Enter description'}))
    def clean(self):
        cleaned_data = super().clean()
        total = cleaned_data.get('total_seats')
        available = cleaned_data.get('available_seats')
        if total is not None and available is not None:
            if available > total:
                raise forms.ValidationError("Available seats cannot be greater than total seats.")
        return cleaned_data

class BannerForm(forms.Form):
    banner_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Enter banner name', **common_classes}))
    banner_image = forms.ImageField(required=False, widget=forms.FileInput(attrs=common_classes))
    is_active = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={ 'class': 'h-5 w-5 text-indigo-600 rounded' }))

class UserForm(forms.Form):
    name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Enter name', **common_classes}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter email', **common_classes}))
    dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', **common_classes}))
    phone = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'placeholder': 'Enter phone', **common_classes}))
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', **common_classes}))

class BookingForm(forms.Form):
    CHOICES = (
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('passport', 'Passport'),
        ('driving', 'Driving License'),
        ('voter', 'Voter ID')
    )
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'Enter Name', **common_classes}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter Email', **common_classes}))
    age = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'placeholder': 'Enter Age', **common_classes}))
    id_proof_type = forms.ChoiceField(choices=CHOICES, widget=forms.Select(attrs={**common_classes}))
    id_proof_image = forms.ImageField(widget=forms.FileInput(attrs={**common_classes}))
    def clean_age(self):
        age = self.cleaned_data['age']
        if age <= 15:
            raise forms.ValidationError("Age must be greater than 15.")
        return age