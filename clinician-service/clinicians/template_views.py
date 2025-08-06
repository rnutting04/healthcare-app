from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from .services import DatabaseService
import logging

logger = logging.getLogger(__name__)


class ClinicianDashboardView(View):
    """Dashboard view for clinicians"""
    
    def get(self, request):
        """Render clinician dashboard"""
        try:
            # Get clinician profile
            clinician = DatabaseService.get_clinician_by_user_id(request.user_id)
            
            # Prepare context (stub data for now)
            context = {
                'user': request.user_data,
                'clinician': clinician,
                'stats': {
                    'total_patients': 0,
                    'today_appointments': 0,
                    'pending_appointments': 0,
                    'completed_appointments': 0
                },
                'upcoming_appointments': [],
                'recent_patients': [],
                'notifications': []
            }
            
            return render(request, 'clinician_dashboard.html', context)
            
        except Exception as e:
            logger.error(f"Failed to load dashboard: {e}")
            return render(request, 'clinician_dashboard.html', {
                'error': 'Failed to load dashboard data'
            })