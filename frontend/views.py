from django.shortcuts import render, redirect


def dashboard(request):
    """Vue pour servir le dashboard frontend"""
    if not request.user.is_authenticated:
        return redirect('/login/')
    return render(request, 'index.html')


def login(request):
    """Vue pour servir la page de connexion"""
    return render(request, 'login.html')


def register(request):
    """Vue pour servir la page d'inscription"""
    return render(request, 'register.html')
