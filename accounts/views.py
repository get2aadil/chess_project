from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib import messages
from .forms import CustomUserCreationForm 

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Save the user, including first_name and last_name
            messages.success(request, 'Your account has been created successfully! Please log in.')
            return redirect('login')  # Redirect to login page after successful registration
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def home_view(request):
    return render(request, 'home.html')

@require_POST 
def logout_view(request):
    user = request.user
    logout(request)  # Logs out the user and flushes the session data
    # Delete all sessions associated with the user
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in sessions:
        session_data = session.get_decoded()
        if session_data.get('_auth_user_id') == str(user.id):
            session.delete()
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')


