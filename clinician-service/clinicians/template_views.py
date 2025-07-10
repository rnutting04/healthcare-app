from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def clinician_dashboard(request):
    return render(request, 'clinician_dashboard.html')

@ensure_csrf_cookie
def clinician_appointments(request):
    return render(request, 'clinician_appointments.html')

@ensure_csrf_cookie
def clinician_patients(request):
    return render(request, 'clinician_patients.html')

@ensure_csrf_cookie  
def clinician_schedule(request):
    return render(request, 'clinician_schedule.html')