from django.urls import path
from . import views

urlpatterns = [

    # Authentication
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    # User
    path('user/home/', views.home, name='home'),
    path('user/profile/', views.profile, name='profile'),
    path('user/event/', views.event, name='event'),
    path('user/event_detail/<int:id>', views.event_detail, name='event_detail'),
    path('user/event_book/<int:id>', views.event_booking, name='event_book'),
    path('user/userbookings/<int:id>/', views.get_booking, name='userbookings'),
    path('user/cancelbookings/<int:id>/', views.cancel_booking, name='cancelbookings'),
    path('user/search/', views.search, name='search'),
    path('user/download_ticket/<int:id>/', views.download_ticket, name='download_ticket'),
    path('user/verify_ticket/<str:ticket_number>/', views.verify_ticket, name='verify_ticket'),

    # Admin
    path('administrator/dashboard/', views.dashboard, name='dashboard'),
    path('administrator/eventlist/', views.event_list, name='eventlist'),
    path('administrator/addevent/', views.add_event, name='addevent'),
    path('administrator/updatevent/<int:id>', views.update_event, name='updatevent'),
    path('administrator/deletevent/<int:id>', views.delete_event, name='deletevent'),
    path('administrator/bannerlist/', views.banner_list, name='bannerlist'),
    path('administrator/addbanner/', views.add_banner, name='addbanner'),
    path('administrator/updatebanner/<int:id>/', views.update_banner, name='updatebanner'),
    path('administrator/deletebanner/<int:id>/', views.delete_banner, name='deletebanner'),
    path('administrator/users/', views.user_list, name='userlist'),
    path('administrator/adduser/', views.add_user, name='adduser'),
    path('administrator/updateuser/<int:id>/', views.update_user, name='updateuser'),
    path('administrator/deleteuser/<int:id>/', views.delete_user, name='deleteuser'),
    path('administrator/bookings/', views.booking_list, name='bookinglist'),
    path('administrator/deletebooking/<int:id>/', views.delete_booking, name='deletebooking'),
    path('administrator/search/', views.admin_search, name='admin_search'),
    path('administrator/viewuser/<int:id>/', views.view_user, name='view_user'),
    path('administrator/viewevent/<int:id>/', views.view_event, name='view_event'),
    path('administrator/viewbooking/<int:id>/', views.view_booking, name='view_booking'),
    path('administrator/viewbanner/<int:id>/', views.view_banner, name='view_banner'),
]