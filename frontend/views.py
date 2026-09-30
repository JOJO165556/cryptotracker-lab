from django.shortcuts import render


def dashboard(request):
    """Vue pour servir le dashboard frontend"""
    return render(request, 'index.html')


def login(request):
    """Vue pour servir la page de connexion"""
    return render(request, 'login.html')


def register(request):
    """Vue pour servir la page d'inscription"""
    return render(request, 'register.html')
