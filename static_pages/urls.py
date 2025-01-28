from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # Home page at the root URL
    path('about/', views.about_view, name='about'),
    path('rules/', views.rules_view, name='rules'),
    path('history/', views.history_view, name='history'),
]
