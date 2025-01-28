from django.shortcuts import render

def about_view(request):
    return render(request, 'about.html')

def rules_view(request):
    return render(request, 'rules.html')

def home_view(request):
    return render(request, 'home.html')

def history_view(request):
    return render(request, 'history.html')