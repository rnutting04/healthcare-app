from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def patient_dashboard(request):
    return render(request, 'patient_dashboard.html')

@ensure_csrf_cookie
def patient_appointments(request):
    return render(request, 'patient_appointments.html')

@ensure_csrf_cookie
def patient_records(request):
    return render(request, 'medical_records.html')

@ensure_csrf_cookie  
def patient_prescriptions(request):
    return render(request, 'patient_prescriptions.html')

@ensure_csrf_cookie
def patient_profile_edit(request):
    return render(request, 'patient_profile_edit.html')

@ensure_csrf_cookie
def patient_chat(request):
    return render(request, 'chat_bot.html')

@ensure_csrf_cookie
def patient_medical_records(request):
    return render(request, 'medical_records.html')