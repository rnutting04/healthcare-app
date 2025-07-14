from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
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
            # logger.info(f"Cancer types response: {cancer_types}")
        except Exception as e:
            logger.error(f"Could not fetch cancer types: {str(e)}")
        
        # Get API health status
        api_health = {}
        try:
            api_health = DatabaseService.check_all_services_health()
            # logger.info(f"API health status: {api_health}")
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
        # logger.info(f"Cancer types response: {response}")
        
        # The API returns the list directly, not wrapped in 'data'
        if isinstance(response, list):
            cancer_types = response
        elif isinstance(response, dict) and 'results' in response:
            cancer_types = response['results']
        else:
            cancer_types = []
        
        # logger.info(f"Processed cancer types: {cancer_types}")
        
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
        # logger.info(f"Retrieved cancer types for dropdown: {cancer_types}")
        if isinstance(cancer_types, list):
            # Filter to only show parent types (where parent is None)
            parent_options = [ct for ct in cancer_types if ct.get('parent') is None]
        elif isinstance(cancer_types, dict) and 'results' in cancer_types:
            # Filter to only show parent types (where parent is None)
            parent_options = [ct for ct in cancer_types['results'] if ct.get('parent') is None]
        else:
            parent_options = []
        # logger.info(f"Filtered parent options: {parent_options}")
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
        # logger.info(f"Editing cancer type {cancer_type_id}: {cancer_type}")
        
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
                # logger.info(f"Successfully fetched patient data for user {user_id}: {patient_data}")
                
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
                    
                    # logger.info(f"Fetching languages from: {settings.PATIENT_SERVICE_URL}/api/patients/languages/")
                    languages_response = requests.get(
                        f"{settings.PATIENT_SERVICE_URL}/api/patients/languages/",
                        headers=headers
                    )
                    # logger.info(f"Languages response status: {languages_response.status_code}")
                    # logger.info(f"Auth header being sent: {auth_header}")
                    if languages_response.status_code == 200:
                        languages_data = languages_response.json()
                        # logger.info(f"Languages response data: {languages_data}")
                        # Handle paginated response
                        # Ensure we're updating the outer scope languages variable
                        if isinstance(languages_data, list):
                            languages = languages_data
                        else:
                            languages = languages_data.get('results', languages_data)
                        # logger.info(f"Fetched {len(languages)} languages")
                        # logger.info(f"Languages list: {languages}")
                        
                        # Log the preferred language to debug
                        if patient_data:
                            # logger.info(f"Patient preferred_language value: {patient_data.get('preferred_language')}")
                            pass
                    else:
                        # logger.warning(f"Failed to fetch languages: {languages_response.status_code}")
                        # logger.warning(f"Response content: {languages_response.text}")
                        pass
                except Exception as e:
                    # logger.warning(f"Could not fetch languages: {str(e)}")
                    pass
            except Exception as e:
                # logger.warning(f"Could not fetch patient data for user {user_id}: {str(e)}")
                pass
        
        # logger.info(f"DEBUG: Languages before context: {languages}")
        # logger.info(f"DEBUG: Number of languages: {len(languages)}")
        
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
    if request.method == 'POST':
        try:
            # Get cancer type from form
            cancer_type_id = request.POST.get('cancer_type')
            if not cancer_type_id:
                return JsonResponse({'success': False, 'error': 'Please select a cancer type'}, status=400)
            
            # Get files from request
            files = request.FILES.getlist('files')
            if not files:
                return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)
            
            uploaded_files = []
            errors = []
            
            # Get JWT token for file service authentication
            token = request.COOKIES.get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
            
            for file in files:
                try:
                    # Upload file to file service
                    file_service_url = f"{settings.FILE_SERVICE_URL}/api/files/upload"
                    
                    files_data = {'file': (file.name, file.read(), file.content_type)}
                    response = requests.post(file_service_url, files=files_data, headers=headers)
                    
                    if response.status_code == 201:
                        file_data = response.json()
                        file_id = file_data['file_id']
                        
                        # Create RAGDocument association
                        rag_doc_data = {
                            'file_id': file_id,
                            'cancer_type_id': cancer_type_id
                        }
                        
                        db_response = DatabaseService.create_rag_document(rag_doc_data)
                        
                        if db_response:
                            uploaded_files.append({
                                'filename': file.name,
                                'file_id': file_id,
                                'size': file.size
                            })
                        else:
                            errors.append(f"Failed to associate {file.name} with cancer type")
                    else:
                        error_msg = response.json().get('message', response.json().get('error', 'Upload failed'))
                        errors.append(f"{file.name}: {error_msg}")
                        logger.error(f"File service response: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    logger.error(f"Error uploading {file.name}: {str(e)}")
                    errors.append(f"{file.name}: Upload error")
            
            return JsonResponse({
                'success': len(uploaded_files) > 0,
                'uploaded_files': uploaded_files,
                'errors': errors,
                'message': f"Successfully uploaded {len(uploaded_files)} file(s)"
            })
            
        except Exception as e:
            logger.error(f"Document upload error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Upload failed'}, status=500)
    
    # GET request - show upload form
    try:
        context = {
            'user': request.user_data
        }
        return render(request, 'document_upload.html', context)
    except Exception as e:
        logger.error(f"Document upload page error: {str(e)}")
        messages.error(request, "Error loading document upload page")
        return redirect('dashboard')

def api_cancer_types(request):
    """API endpoint to get cancer types (parent types only)"""
    try:
        # Get cancer types from database service
        cancer_types = DatabaseService.get_cancer_types()
        # logger.info(f"API cancer types raw response: {type(cancer_types)}")
        
        # Process the response based on its format (same as cancer_type_create)
        if isinstance(cancer_types, list):
            # Filter to only show parent types (where parent is None)
            parent_types = [ct for ct in cancer_types if ct.get('parent') is None]
        elif isinstance(cancer_types, dict) and 'results' in cancer_types:
            # Filter to only show parent types (where parent is None)
            parent_types = [ct for ct in cancer_types['results'] if ct.get('parent') is None]
        else:
            parent_types = []
        
        # logger.info(f"API cancer types filtered count: {len(parent_types)}")
        return JsonResponse(parent_types, safe=False)
    except Exception as e:
        logger.error(f"Error fetching cancer types: {str(e)}")
        return JsonResponse({'error': 'Failed to fetch cancer types'}, status=500)

def api_rag_documents(request):
    """API endpoint to get paginated RAG documents"""
    try:
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 10)
        cancer_type_id = request.GET.get('cancer_type_id')
        
        # Build params
        params = {'page': page, 'page_size': page_size}
        if cancer_type_id:
            params['cancer_type_id'] = cancer_type_id
        
        # Get RAG documents from database service
        headers = {
            'X-Service-Token': getattr(settings, 'DATABASE_SERVICE_TOKEN', 'db-service-secret-token')
        }
        response = requests.get(
            f"{settings.DATABASE_SERVICE_URL}/api/rag-documents/",
            params=params,
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        # The database service now includes file_data directly
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error fetching RAG documents: {str(e)}")
        return JsonResponse({'error': 'Failed to fetch documents'}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def api_delete_rag_document(request, file_id):
    """API endpoint to delete a RAG document"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        # Get the JWT token from cookies (same as file upload)
        jwt_token = request.COOKIES.get('access_token')
        if not jwt_token:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Step 1: Delete the file from file service
        file_service_url = f"{settings.FILE_SERVICE_URL}/api/files/{file_id}/delete"
        headers = {'Authorization': f'Bearer {jwt_token}'}
        
        file_response = requests.delete(file_service_url, headers=headers)
        if file_response.status_code not in [200, 204, 404]:
            logger.error(f"Failed to delete file from file service: {file_response.status_code}")
            # Continue with database deletion even if file deletion fails
        
        # Step 2: Delete the RAG document from database service
        db_headers = {
            'X-Service-Token': getattr(settings, 'DATABASE_SERVICE_TOKEN', 'db-service-secret-token')
        }
        # RAGDocument uses file_id as primary key
        db_response = requests.delete(
            f"{settings.DATABASE_SERVICE_URL}/api/rag-documents/{file_id}/",
            headers=db_headers
        )
        
        if db_response.status_code not in [200, 204]:
            logger.error(f"Failed to delete RAG document from database: {db_response.status_code}")
            return JsonResponse({'error': 'Failed to delete document record'}, status=500)
        
        return JsonResponse({'message': 'Document deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting RAG document: {str(e)}")
        return JsonResponse({'error': 'Failed to delete document'}, status=500)

# Health check
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({'status': 'healthy', 'service': 'admin-service'})