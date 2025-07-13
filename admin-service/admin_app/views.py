from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
from .services import DatabaseService
import logging
import requests

logger = logging.getLogger(__name__)

def dashboard(request):
    """Admin dashboard view"""
    try:
        # Get statistics
        stats = DatabaseService.get_user_statistics()
        
        # Get cancer types count
        cancer_types_count = 0
        try:
            cancer_types = DatabaseService.get_cancer_types()
            # The API returns a paginated response with 'count' field
            if isinstance(cancer_types, dict) and 'count' in cancer_types:
                cancer_types_count = cancer_types['count']
            elif isinstance(cancer_types, dict) and 'results' in cancer_types:
                cancer_types_count = len(cancer_types['results'])
            elif isinstance(cancer_types, list):
                cancer_types_count = len(cancer_types)
            logger.info(f"Cancer types response: {cancer_types}")
        except Exception as e:
            logger.error(f"Could not fetch cancer types: {str(e)}")
        
        # Get API health status
        api_health = {}
        try:
            api_health = DatabaseService.check_all_services_health()
            logger.info(f"API health status: {api_health}")
        except Exception as e:
            logger.error(f"Could not fetch API health status: {str(e)}")
        
        context = {
            'stats': stats,
            'cancer_types_count': cancer_types_count,
            'api_health': api_health,
            'user': request.user_data
        }
        return render(request, 'admin_dashboard.html', context)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        messages.error(request, "Error loading dashboard")
        return render(request, 'admin_dashboard.html', {'error': str(e)})

# Cancer Type Views
def cancer_types_list(request):
    """List all cancer types"""
    try:
        response = DatabaseService.get_cancer_types()
        logger.info(f"Cancer types response: {response}")
        
        # The API returns the list directly, not wrapped in 'data'
        if isinstance(response, list):
            cancer_types = response
        elif isinstance(response, dict) and 'results' in response:
            cancer_types = response['results']
        else:
            cancer_types = []
        
        logger.info(f"Processed cancer types: {cancer_types}")
        
        context = {
            'cancer_types': cancer_types,
            'user': request.user_data
        }
        return render(request, 'cancer_types_list.html', context)
    except Exception as e:
        logger.error(f"Cancer types list error: {str(e)}")
        messages.error(request, "Error loading cancer types")
        return render(request, 'cancer_types_list.html', {'error': str(e), 'user': request.user_data})

@require_http_methods(["GET", "POST"])
def cancer_type_create(request):
    """Create new cancer type or subtype"""
    if request.method == "POST":
        try:
            entry_type = request.POST.get('entry_type', 'type')
            
            if entry_type == 'type':
                # Create cancer type
                data = {
                    'cancer_type': request.POST.get('cancer_type'),
                    'description': request.POST.get('description'),
                    'parent': None  # Main types don't have parents
                }
                
                DatabaseService.create_cancer_type(data)
                messages.success(request, "Cancer type created successfully")
                return redirect('cancer_types_list')
            else:
                # Create cancer subtype (as a CancerType with parent)
                data = {
                    'cancer_type': request.POST.get('subtype_cancer_type'),
                    'description': request.POST.get('subtype_description'),
                    'parent': request.POST.get('parent')
                }
                
                DatabaseService.create_cancer_type(data)
                messages.success(request, "Cancer subtype created successfully")
                return redirect('cancer_types_list')
                
        except Exception as e:
            logger.error(f"Cancer type/subtype create error: {str(e)}")
            messages.error(request, f"Error creating: {str(e)}")
    
    # Get all cancer types to populate parent dropdown
    try:
        cancer_types = DatabaseService.get_cancer_types()
        logger.info(f"Retrieved cancer types for dropdown: {cancer_types}")
        if isinstance(cancer_types, list):
            # Filter to only show parent types (where parent is None)
            parent_options = [ct for ct in cancer_types if ct.get('parent') is None]
        elif isinstance(cancer_types, dict) and 'results' in cancer_types:
            # Filter to only show parent types (where parent is None)
            parent_options = [ct for ct in cancer_types['results'] if ct.get('parent') is None]
        else:
            parent_options = []
        logger.info(f"Filtered parent options: {parent_options}")
    except Exception as e:
        logger.error(f"Error fetching cancer types for dropdown: {str(e)}")
        parent_options = []
    
    return render(request, 'cancer_type_form.html', {
        'action': 'create',
        'parent_options': parent_options,
        'user': request.user_data
    })

@require_http_methods(["GET", "POST"])
def cancer_type_edit(request, cancer_type_id):
    """Edit cancer type"""
    try:
        response = DatabaseService.get_cancer_type(cancer_type_id)
        # The API returns the object directly, not wrapped in 'data'
        cancer_type = response
        logger.info(f"Editing cancer type {cancer_type_id}: {cancer_type}")
        
        if request.method == "POST":
            data = {
                'cancer_type': request.POST.get('cancer_type'),
                'description': request.POST.get('description'),
                'parent': request.POST.get('parent') or None
            }
            
            DatabaseService.update_cancer_type(cancer_type_id, data)
            messages.success(request, "Cancer type updated successfully")
            return redirect('cancer_types_list')
        
        # Get all cancer types to populate parent dropdown
        try:
            all_cancer_types = DatabaseService.get_cancer_types()
            if isinstance(all_cancer_types, list):
                parent_options = [ct for ct in all_cancer_types if ct.get('id') != cancer_type_id]
            elif isinstance(all_cancer_types, dict) and 'results' in all_cancer_types:
                parent_options = [ct for ct in all_cancer_types['results'] if ct.get('id') != cancer_type_id]
            else:
                parent_options = []
        except:
            parent_options = []
        
        return render(request, 'cancer_type_form.html', {
            'action': 'edit',
            'cancer_type': cancer_type,
            'parent_options': parent_options,
            'user': request.user_data
        })
    except Exception as e:
        logger.error(f"Cancer type edit error: {str(e)}")
        messages.error(request, f"Error editing cancer type: {str(e)}")
        return redirect('cancer_types_list')

@require_http_methods(["POST"])
def cancer_type_delete(request, cancer_type_id):
    """Delete cancer type"""
    try:
        DatabaseService.delete_cancer_type(cancer_type_id)
        messages.success(request, "Cancer type deleted successfully")
    except Exception as e:
        logger.error(f"Cancer type delete error: {str(e)}")
        messages.error(request, f"Error deleting cancer type: {str(e)}")
    
    return redirect('cancer_types_list')



# User Management Views
def users_list(request):
    """List all users"""
    try:
        role_filter = request.GET.get('role')
        status_filter = request.GET.get('status')
        
        is_active = None
        if status_filter == 'active':
            is_active = True
        elif status_filter == 'inactive':
            is_active = False
        
        response = DatabaseService.get_all_users(role=role_filter, is_active=is_active)
        # Handle paginated response from database-service
        users = response.get('results', response.get('data', []))
        
        context = {
            'users': users,
            'role_filter': role_filter,
            'status_filter': status_filter,
            'user': request.user_data
        }
        return render(request, 'users_list.html', context)
    except Exception as e:
        logger.error(f"Users list error: {str(e)}")
        messages.error(request, "Error loading users")
        return render(request, 'users_list.html', {'error': str(e)})

@require_http_methods(["POST"])
def user_toggle_status(request, user_id):
    """Toggle user active status"""
    try:
        action = request.POST.get('action')
        is_active = action == 'activate'
        
        DatabaseService.update_user_status(user_id, is_active)
        
        status_text = "activated" if is_active else "deactivated"
        messages.success(request, f"User {status_text} successfully")
    except Exception as e:
        logger.error(f"User status toggle error: {str(e)}")
        messages.error(request, f"Error updating user status: {str(e)}")
    
    return redirect('users_list')

def user_detail(request, user_id):
    """View user details"""
    try:
        from datetime import datetime
        
        response = DatabaseService.get_user(user_id)
        # The database-service returns the user directly, not wrapped in 'data'
        user_data = response
        
        # Convert date strings to datetime objects for template formatting
        if user_data.get('date_joined'):
            try:
                user_data['date_joined'] = datetime.fromisoformat(user_data['date_joined'].replace('Z', '+00:00'))
            except:
                pass
        if user_data.get('last_login'):
            try:
                user_data['last_login'] = datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00'))
            except:
                pass
        
        # If user is a patient, fetch patient-specific information
        patient_data = None
        languages = []
        if user_data.get('role_name') == 'PATIENT':
            try:
                patient_response = DatabaseService.get_patient_by_user(user_id)
                patient_data = patient_response
                logger.info(f"Successfully fetched patient data for user {user_id}: {patient_data}")
                
                # Fetch available languages
                try:
                    # Use the user's token from cookies or create a service token
                    auth_header = None
                    
                    # First try to get token from cookies
                    access_token = request.COOKIES.get('access_token')
                    if access_token:
                        auth_header = f'Bearer {access_token}'
                    else:
                        # If no user token, use a service account approach
                        # For now, use the admin's token that was used to fetch patient data
                        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                    
                    headers = {}
                    if auth_header:
                        headers['Authorization'] = auth_header
                    
                    logger.info(f"Fetching languages from: {settings.PATIENT_SERVICE_URL}/api/patients/languages/")
                    languages_response = requests.get(
                        f"{settings.PATIENT_SERVICE_URL}/api/patients/languages/",
                        headers=headers
                    )
                    logger.info(f"Languages response status: {languages_response.status_code}")
                    if languages_response.status_code == 200:
                        languages_data = languages_response.json()
                        # Handle paginated response
                        languages = languages_data.get('results', languages_data)
                        logger.info(f"Fetched {len(languages)} languages")
                        
                        # Log the preferred language to debug
                        if patient_data:
                            logger.info(f"Patient preferred_language value: {patient_data.get('preferred_language')}")
                    else:
                        logger.warning(f"Failed to fetch languages: {languages_response.status_code}")
                except Exception as e:
                    logger.warning(f"Could not fetch languages: {str(e)}")
                    
            except Exception as e:
                logger.warning(f"Could not fetch patient data for user {user_id}: {str(e)}")
        
        context = {
            'user': user_data,  # Template expects 'user'
            'patient_data': patient_data,  # Patient-specific data
            'current_user': request.user_data,  # Current logged-in user
            'languages': languages  # Available languages
        }
        return render(request, 'user_detail.html', context)
    except Exception as e:
        logger.error(f"User detail error: {str(e)}")
        messages.error(request, f"Error loading user details: {str(e)}")
        return redirect('users_list')

# Patient Management
@require_http_methods(["POST"])
def update_patient_info(request, patient_id):
    """Update patient information"""
    try:
        # Get the data from the form
        data = {
            'date_of_birth': request.POST.get('date_of_birth'),
            'gender': request.POST.get('gender'),
            'phone_number': request.POST.get('phone_number'),
            'address': request.POST.get('address'),
            'emergency_contact_name': request.POST.get('emergency_contact_name'),
            'emergency_contact_phone': request.POST.get('emergency_contact_phone'),
            'preferred_language_id': request.POST.get('preferred_language_id'),
        }
        
        # Remove empty values
        data = {k: v for k, v in data.items() if v}
        
        # Update patient info via database service
        DatabaseService.update_patient(patient_id, data)
        
        messages.success(request, "Patient information updated successfully")
    except Exception as e:
        logger.error(f"Patient update error: {str(e)}")
        messages.error(request, f"Error updating patient information: {str(e)}")
    
    # Redirect back to the user detail page
    # Get user_id from the form's referrer or from the patient data
    referrer = request.META.get('HTTP_REFERER')
    if referrer and '/users/' in referrer:
        # Extract user_id from the referrer URL
        try:
            user_id = referrer.split('/users/')[-1].rstrip('/')
            return redirect('user_detail', user_id=user_id)
        except:
            pass
    
    # If we can't get it from referrer, try to get from patient data
    try:
        patient_response = DatabaseService.make_request('GET', f'/api/patients/{patient_id}/')
        if isinstance(patient_response, dict) and 'user' in patient_response:
            user_data = patient_response['user']
            if isinstance(user_data, dict) and 'id' in user_data:
                return redirect('user_detail', user_id=user_data['id'])
    except:
        pass
    
    return redirect('users_list')

# Document Management for RAG
def document_upload(request):
    """Document upload page for RAG system"""
    try:
        context = {
            'user': request.user_data
        }
        return render(request, 'document_upload.html', context)
    except Exception as e:
        logger.error(f"Document upload page error: {str(e)}")
        messages.error(request, "Error loading document upload page")
        return redirect('dashboard')

# Health check
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({'status': 'healthy', 'service': 'admin-service'})