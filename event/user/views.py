from django.core.exceptions import ValidationError
from datetime import date 
from django.http import HttpResponse
from .forms import SignupForm, LoginForm, ProfileForm, EventForm, BannerForm, UserForm, BookingForm
from .models import User, Event, Banner, Bookings
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
import cloudinary.uploader
from django.db.models import Sum
from datetime import timedelta


# Authentication

# Signup
def signup(request):
    if 'user_id' in request.session:
        return redirect('home')
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            User.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                dob=form.cleaned_data['dateOfBirth'],
                phone=form.cleaned_data['phone'],
                password=form.cleaned_data['password']
            )
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})

# Login
def login(request):
    if 'user_id' in request.session:
        if request.session.get('role') == 'admin':
            return redirect('dashboard')
        else:
            return redirect('home')
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                # Check password
                if check_password(password, user.password):
                    # Create session (VERY IMPORTANT)
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    request.session['role'] = user.role
                    messages.success(request, "Login successful!")
                    if user.role == 'admin':
                        return redirect('dashboard')
                    else:
                        return redirect('home')  # create this page
                else:
                    messages.error(request, "Invalid password")
            except User.DoesNotExist:
                messages.error(request, "Email not registered")
        else:
            messages.error(request, "Invalid form input")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

# Logout
def logout(request):
    request.session.flush()
    return redirect('login')

# Profile
def profile(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            user.name = form.cleaned_data['name']
            user.email = form.cleaned_data['email']
            user.dob = form.cleaned_data['dob']
            user.phone = form.cleaned_data['phone']
            user.save()
            return redirect('profile')
    else:
        form = ProfileForm(initial={
            'name': user.name,
            'email': user.email,
            'dob': user.dob,
            'phone': user.phone,
        })
    return render(request, 'profile.html', { 'form': form, 'user': user })

# Home
def home(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') == 'admin':
        return redirect('dashboard')
    today = timezone.now().date()
    banners = Banner.objects.filter(is_active=True)
    events = Event.objects.filter(event_date__date__gte=today).order_by('-created_at')[:8]
    return render(request, 'home.html', {'name': request.session.get('user_name'), 'banners': banners, 'events': events})

# Event
def event(request):
    today = timezone.now().date()
    events = Event.objects.filter(event_date__date__gte=today).order_by('-created_at')
    category = request.GET.get('category')
    location = request.GET.get('location')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    event_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if category:
        events = events.filter(event_category=category)

    if location:
        events = events.filter(event_location__icontains=location)

    if min_price:
        events = events.filter(event_price__gte=min_price)

    if max_price:
        events = events.filter(event_price__lte=max_price)

    # date filtering
    if date_from:
        events = events.filter(event_date__date__gte=date_from)

    if date_to:
        events = events.filter(event_date__date__lte=date_to)

    if event_type == "today":
        events = events.filter(event_date__date=today)
    elif event_type == "upcoming":
        events = events.filter(event_date__date__gt=today)

    sort = request.GET.get('sort')
    if sort == "price_low":
        events = events.order_by('event_price')
    elif sort == "price_high":
        events = events.order_by('-event_price')
    elif sort == "newest":
        events = events.order_by('-created_at')

    return render(request, 'event.html', {'events': events})

# Event Details
def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, 'eventdetails.html', {'event': event})

# Bookings
def event_booking(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    event = get_object_or_404(Event, id = id)
    if event.available_seats <= 0:
        messages.error(request, 'Event Is Fully Booked!!')
        return redirect('event')
    user = get_object_or_404(User, id = request.session['user_id'])
    if request.method == "POST":
        form = BookingForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                booking = Bookings(
                    user=user,
                    event=event,
                    name=form.cleaned_data['name'],
                    email=form.cleaned_data['email'],
                    age=form.cleaned_data['age'],
                    id_proof_type=form.cleaned_data['id_proof_type'],
                    id_proof_image=form.cleaned_data['id_proof_image']
                )
                booking.full_clean()
                booking.save()
                event.available_seats -= 1
                event.save()
                pdf = generate_ticket_pdf(booking)
                subject = "🎉 Booking Confirmed - EventsHub"
                text_content = f"""
                    Hello {booking.name},
                    Your booking has been successfully confirmed.
                    Event: {event.event_name}
                    Date: {event.event_date}
                    Location: {event.event_location}
                    Thank you for choosing EventsHub!
                """
                context = {
                    'booking': booking,
                    'name': booking.name,
                    'event_name': event.event_name,
                    'event_date': event.event_date,
                    'event_location': event.event_location,
                    'event_description': booking.event.event_description,
                    'event_image': booking.event.event_image,
                }
                html_content = render_to_string('confirmation.html', context)
                email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [booking.email])
                email.attach_alternative(html_content, "text/html")
                filename = f"{booking.ticket_number}.pdf"
                email.attach(filename, pdf, "application/pdf")
                email.send()
                messages.success(request, "Booking Successful")
                return redirect('userbookings', id=request.session['user_id'])
            except ValidationError as e:
                print("Error:", e)
                form.add_error(None, e)
        else:
            print(form.errors)
    else:
        form = BookingForm()
    return render(request, 'event_book.html', {'form': form, 'event': event})

# Get Bookings
def get_booking(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'user':
        return redirect('dashboard')
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    bookings = Bookings.objects.select_related('user', 'event')\
        .filter(user_id=id)\
        .order_by('-booked_at')
    for b in bookings:
        event_date = b.event.event_date.date()
        b.can_cancel = event_date > tomorrow
    return render(request, 'bookings.html', {'bookings': bookings})

# Cancel Bookings
def cancel_booking(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'user':
        return redirect('dashboard')
    booking = get_object_or_404(Bookings, id=id, user_id=request.session['user_id'])
    event = booking.event
    event.available_seats += 1
    event.save()
    booking.delete()
    messages.success(request, "Booking cancelled successfully!")
    return redirect('userbookings', id=request.session['user_id'])

# Search
def search(request):
    query = request.GET.get('search')
    if query:
        events = Event.objects.filter(
            event_name__icontains=query
        ) | Event.objects.filter(
            event_category__icontains=query
        ) | Event.objects.filter(
            event_description__icontains=query
        )
    else:
        events = Event.objects.all()
    events = events.order_by('-created_at')
    return render(request, 'event.html', {'events': events, 'query': query})

# Download Ticket
def download_ticket(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    booking = get_object_or_404(Bookings, id=id, user_id=request.session['user_id'])
    pdf = generate_ticket_pdf(booking)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{booking.ticket_number}.pdf"'
    return response

# Verify Ticket
def verify_ticket(request, ticket_number):
    try:
        booking = Bookings.objects.get(ticket_number=ticket_number)
        return HttpResponse(f"VALID TICKET for {booking.name} - {booking.event.event_name}")
    except Bookings.DoesNotExist:
        return HttpResponse("INVALID TICKET")
    
# Admin

# Dashboard
def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    total_users = User.objects.filter(role='user').count()
    total_events = Event.objects.count()
    total_bookings = Bookings.objects.count()
    total_revenue = Bookings.objects.aggregate(
        total=Sum('event__event_price')
    )['total'] or 0
    today = timezone.now().date()
    chart_labels = []
    chart_values = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        bookings_count = Bookings.objects.filter(
            booked_at__date=day
        ).count()
        chart_labels.append(day.strftime('%a'))
        chart_values.append(bookings_count)

    recent_bookings = Bookings.objects.select_related('event').order_by('-booked_at')[:5]
    recent_events = Event.objects.order_by('-created_at')[:5]

    top_events = Event.objects.annotate(
        total_bookings=Count('bookings')
    ).order_by('-total_bookings')[:5]

    context = {
        'name': request.session.get('user_name'),
        'total_users': total_users,
        'total_events': total_events,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'recent_bookings': recent_bookings,
        'recent_events': recent_events,
        'top_events': top_events,
    }
    return render(request, 'dashboard.html', context)

# Get Event
def event_list(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    query = request.GET.get('search', '').strip()
    events = Event.objects.all()
    today = date.today()
    for event in events:
        event.is_completed = event.event_date.date() < today
    if query:
        events = events.filter(
            Q(event_name__icontains=query) |
            Q(event_category__icontains=query) |
            Q(event_location__icontains=query)
        )
    return render(request, 'event_list.html', {'events': events, 'query': query})

# View Event
def view_event(request, id):
    event = Event.objects.get(id=id)
    return render(request, 'view_event.html', {'event': event})

# Add Event
def add_event(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                Event.objects.create(
                    event_name=form.cleaned_data['event_name'],
                    event_date=form.cleaned_data['event_date'],
                    event_category=form.cleaned_data['event_category'],
                    event_image=form.cleaned_data['event_image'],
                    event_price=form.cleaned_data['event_price'],
                    event_location=form.cleaned_data['event_location'],
                    total_seats=form.cleaned_data['total_seats'],
                    available_seats=form.cleaned_data['available_seats'],
                    event_description=form.cleaned_data['event_description'],
                )
                return redirect('eventlist')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EventForm()
    return render(request, 'event_form.html', {'form': form})

# Update Event
def update_event(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    event = get_object_or_404(Event, id=id)
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                data = form.cleaned_data
                event.event_name = data['event_name']
                event.event_date = data['event_date']
                event.event_category = data['event_category']
                event.event_price = data['event_price']
                event.event_location = data['event_location']
                event.total_seats = data['total_seats']
                event.available_seats = data['available_seats']
                event.event_description = data['event_description']
                if data.get('event_image'):
                    if event.event_image:
                        cloudinary.uploader.destroy(event.event_image.public_id)
                    event.event_image = data['event_image']
                event.save()
                return redirect('eventlist')
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = EventForm(initial={
            'event_name': event.event_name,
            'event_date': event.event_date.strftime('%Y-%m-%dT%H:%M'),
            'event_category': event.event_category,
            'event_price': event.event_price,
            'event_location': event.event_location,
            'total_seats': event.total_seats,
            'available_seats': event.available_seats,
            'event_description': event.event_description,
        })
    return render(request, 'event_form.html', {'form': form, 'event': event, 'page': 'update'})

# Delete Event
def delete_event(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    event = get_object_or_404(Event, id=id)
    if event.event_image:
        cloudinary.uploader.destroy(event.event_image.public_id)
    event.delete()
    return redirect('eventlist')

# Get Banner
def banner_list(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    query = request.GET.get('search')
    banners = Banner.objects.all()
    if query:
        banners = banners.filter(
            Q(banner_name__icontains=query)
        )
    return render(request, 'banner_list.html', {'banners': banners, 'query': query})

# View Banner
def view_banner(request, id):
    banner = Banner.objects.get(id=id)
    return render(request, 'view_banner.html', {'banner': banner})

# Add Banner
def add_banner(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            Banner.objects.create(
                banner_name=form.cleaned_data['banner_name'],
                banner_image=form.cleaned_data['banner_image'],
                is_active=form.cleaned_data.get('is_active', False),
            )
            return redirect('bannerlist')
    else:
        form = BannerForm()
    return render(request, 'banner_form.html', {'form': form})

# Update Banner
def update_banner(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    banner = get_object_or_404(Banner, id=id)
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            banner.banner_name = data['banner_name']
            banner.is_active = data.get('is_active', False)
            if data.get('banner_image'):
                if banner.banner_image:
                    cloudinary.uploader.destroy(banner.banner_image.public_id)
                banner.banner_image = data['banner_image']
            banner.save()
            return redirect('bannerlist')
    else:
        form = BannerForm(initial={
            'banner_name': banner.banner_name,
            'is_active': banner.is_active
        })
    return render(request, 'banner_form.html', { 'form': form, 'banner': banner, 'page': 'update'})

# Delete Banner
def delete_banner(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    banner = get_object_or_404(Banner, id=id)
    if banner.banner_image:
        cloudinary.uploader.destroy(banner.banner_image.public_id)
    banner.delete()
    return redirect('bannerlist')

# Get User
def user_list(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    query = request.GET.get('search')
    users = User.objects.filter(role='user')
    if query:
        users = users.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )
    return render(request, 'user_list.html', {'users': users, 'query': query})

# View User
def view_user(request, id):
    user = User.objects.get(id=id)
    return render(request, 'view_user.html', {'user': user})

# Add User
def add_user(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            User.objects.create(
                name=data['name'],
                email=data['email'],
                dob=data['dob'],
                phone=data['phone'],
                password=data['password'],
                role='user'
            )
            return redirect('userlist')
    else:
        form = UserForm()
    return render(request, 'user_form.html', {'form': form})

# Update User
def update_user(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    user = get_object_or_404(User, id=id, role='user')
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user.name = data['name']
            user.email = data['email']
            user.dob = data['dob']
            user.phone = data['phone']
            if data.get('password'):
                user.password = data['password']
            user.save()
            return redirect('userlist')
    else:
        form = UserForm(initial={
            'name': user.name,
            'email': user.email,
            'dob': user.dob,
            'phone': user.phone,
        })
    return render(request, 'user_form.html', {'form': form, 'user': user, 'page': 'update'})

# Delete User
def delete_user(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    user = get_object_or_404(User, id=id, role='user')
    user.delete()
    return redirect('userlist')

# Get Booking Admin
def booking_list(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    query = request.GET.get('search')
    bookings = Bookings.objects.select_related('user', 'event').all().order_by('-booked_at')
    if query:
        bookings = bookings.filter(
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(event__event_name__icontains=query)
        )
    return render(request, 'booking_list.html', {'bookings': bookings, 'query': query})

# View Bookings
def view_booking(request, id):
    booking = Bookings.objects.get(id=id)
    return render(request, 'view_booking.html', {'booking': booking})

# Delete Booking
def delete_booking(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        return redirect('home')
    booking = get_object_or_404(Bookings, id=id)
    event = booking.event
    if booking.id_proof_image:
        cloudinary.uploader.destroy(booking.id_proof_image.public_id)
    if event.available_seats < event.total_seats:
        event.available_seats += 1
        event.save()
    booking.delete()
    return redirect('bookinglist')

# Search Admin
def admin_search(request):
    if request.session.get('role') != 'admin':
        return redirect('login')

    query = request.GET.get('search', '').strip()

    if not query:
        return redirect('dashboard')

    # Try USER first
    if User.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    ).exists():
        return redirect(f"/administrator/users/?search={query}")

    # EVENT
    elif Event.objects.filter(
        Q(event_name__icontains=query) |
        Q(event_category__icontains=query) |
        Q(event_location__icontains=query)
    ).exists():
        return redirect(f"/administrator/eventlist/?search={query}")

    # BOOKING
    elif Bookings.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(event__event_name__icontains=query)
    ).exists():
        return redirect(f"/administrator/bookings/?search={query}")

    # BANNER
    elif Banner.objects.filter(
        Q(banner_name__icontains=query)
    ).exists():
        return redirect(f"/administrator/bannerlist/?search={query}")

    return redirect('dashboard')
    
# Generate Ticket
def generate_ticket_pdf(booking):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    event_dt = booking.event.event_date

    # ===== HEADER =====
    p.setFillColor(colors.darkblue)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(180, 800, "Eventora")

    p.setStrokeColor(colors.orange)
    p.setLineWidth(2)
    p.line(40, 790, width - 40, 790)

    # ===== TITLE =====
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 760, f"Electronic Ticket Receipt")

    p.setFont("Helvetica", 10)
    p.drawString(50, 740, f"Ticket No: {booking.ticket_number}")
    p.drawString(350, 740, f"Date: {event_dt.strftime('%d %b %Y')}")

    # ===== SECTION LINE =====
    p.setStrokeColor(colors.grey)
    p.line(40, 725, width - 40, 725)

    # ===== EVENT DETAILS =====
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 700, "Event Details")

    p.setFont("Helvetica", 11)
    p.drawString(50, 675, f"Event: {booking.event.event_name}")
    p.drawString(50, 655, f"Location: {booking.event.event_location}")
    p.drawString(50, 635, f"Date: {event_dt.strftime('%d-%m-%Y')}")
    p.drawString(300, 635, f"Time: {event_dt.strftime('%I:%M %p')}")

    # Divider
    p.line(40, 620, width - 40, 620)

    # ===== USER DETAILS =====
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 600, "Attendee Details")

    p.setFont("Helvetica", 11)
    p.drawString(50, 575, f"Name: {booking.name}")
    p.drawString(50, 555, f"Email: {booking.email}")
    p.drawString(50, 535, f"Age: {booking.age}")
    p.drawString(50, 515, f"ID Proof: {booking.id_proof_type}")
    p.drawString(50, 495, f"Booked By: {booking.user.name}")

    # Divider
    p.line(40, 480, width - 40, 480)

    # ===== FOOTER =====
    p.setStrokeColor(colors.grey)
    p.line(40, 120, width - 40, 120)

    p.setFont("Helvetica-Oblique", 9)
    p.setFillColor(colors.grey)
    p.drawString(50, 100, "• Please carry valid ID proof.")
    p.drawString(50, 85, "• Ticket is non-transferable.")
    p.drawString(50, 70, "• Entry allowed only with valid QR / Ticket.")

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf