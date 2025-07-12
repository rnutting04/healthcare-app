from django.shortcuts import render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
import requests

@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        # Get role from user object (set by middleware)
        role = getattr(request.user, 'role_name', 'PATIENT').lower()
        if role == 'admin':
            return redirect('/admin/dashboard/')
        elif role == 'clinician':
            return redirect('/clinician/dashboard/')
        else:
            return redirect('/patient/dashboard/')
    return render(request, 'login.html')

@ensure_csrf_cookie
def signup_view(request):
    if request.user.is_authenticated:
        # Get role from user object (set by middleware)
        role = getattr(request.user, 'role_name', 'PATIENT').lower()
        if role == 'admin':
            return redirect('/admin/dashboard/')
        elif role == 'clinician':
            return redirect('/clinician/dashboard/')
        else:
            return redirect('/patient/dashboard/')
    return render(request, 'signup.html')

@require_POST
def logout_view(request):
    # Get the refresh token from cookies
    refresh_token = request.COOKIES.get('refresh_token')
    access_token = request.COOKIES.get('access_token')
    
    # If tokens exist, call the auth service logout endpoint
    if refresh_token or access_token:
        try:
            response = requests.post(
                'http://localhost:8001/api/auth/logout/',
                json={'refresh': refresh_token} if refresh_token else {},
                headers={'Authorization': f'Bearer {access_token}'} if access_token else {}
            )
        except:
            pass  # Even if API call fails, we'll clear cookies and redirect
    
    # Create redirect response
    response = redirect('/login/')
    
    # Clear authentication cookies
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    
    return response