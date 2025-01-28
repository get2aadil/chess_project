from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # Keep this for other views like register and home

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),  # Built-in login
    path('register/', views.register_view, name='register'),  #  custom registration view
    path('logout/', views.logout_view, name='logout'),  # Built-in logout
    path('home/', views.home_view, name='home'),  # Home view
]
