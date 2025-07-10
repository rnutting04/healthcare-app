from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect(f'/{request.user.role.name.lower()}/dashboard')
    return render(request, 'login.html')

@ensure_csrf_cookie
def signup_view(request):
    if request.user.is_authenticated:
        return redirect(f'/{request.user.role.lower()}/dashboard')
    return render(request, 'signup.html')