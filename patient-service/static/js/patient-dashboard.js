// Patient Dashboard JavaScript

async function loadDashboard() {
    try {
        // Check if we have a token
        const token = localStorage.getItem('access_token');
        if (!token) {
            console.error('No access token found - redirecting to login');
            window.location.href = '/login/?next=/patient/dashboard/';
            return;
        }
        
        console.log('Token found:', token ? 'Yes (length: ' + token.length + ')' : 'No');
        
        const response = await fetch('/api/patients/profiles/dashboard/', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.error('Dashboard API error:', response.status, response.statusText);
            throw new Error('Failed to load dashboard');
        }
        
        const data = await response.json();
        
        // Debug: Log the data structure
        console.log('Dashboard API response:', data);
        if (data.recent_records && data.recent_records.length > 0) {
            console.log('First record structure:', data.recent_records[0]);
        }
        
        // Update counts
        document.getElementById('appointmentCount').textContent = data.upcoming_appointments.length;
        document.getElementById('prescriptionCount').textContent = data.active_prescriptions.length;
        document.getElementById('recordCount').textContent = data.recent_records.length;
        
        // Update recent activity
        const activityList = document.getElementById('recentActivity');
        activityList.innerHTML = '';
        
        // Add appointments to activity
        data.upcoming_appointments.forEach(appointment => {
            const date = new Date(appointment.appointment_date);
            const li = document.createElement('li');
            li.className = 'px-4 py-4 hover:bg-gray-50';
            li.innerHTML = `
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm font-medium text-gray-900">
                            Appointment with ${appointment.clinician_name}
                        </p>
                        <p class="text-sm text-gray-500">
                            ${date.toLocaleDateString()} at ${date.toLocaleTimeString()}
                        </p>
                    </div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        ${appointment.status}
                    </span>
                </div>
            `;
            activityList.appendChild(li);
        });
        
        // Add recent records to activity
        data.recent_records.forEach(record => {
            const date = new Date(record.created_at);
            const li = document.createElement('li');
            li.className = 'px-4 py-4 hover:bg-gray-50';
            
            // Extract title from file details or use default
            let recordTitle = 'Medical Record';
            if (record.file_detail && record.file_detail.filename) {
                recordTitle = record.file_detail.filename.replace('.pdf', '').replace(/_/g, ' ');
            } else if (record.title) {
                recordTitle = record.title;
            }
            
            // Extract record type name
            let recordType = 'Medical Record';
            if (record.medical_record_type_detail && record.medical_record_type_detail.type_name) {
                recordType = record.medical_record_type_detail.type_name;
            } else if (record.record_type) {
                recordType = record.record_type;
            }
            
            // Extract uploaded by information
            let uploadedBy = 'Unknown';
            if (record.uploaded_by_detail && record.uploaded_by_detail.name) {
                uploadedBy = record.uploaded_by_detail.name;
            }
            
            // Format date and time
            const dateStr = date.toLocaleDateString();
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            li.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <p class="text-sm font-normal text-gray-900">
                            ${recordTitle}
                        </p>
                        <div class="mt-1 flex items-center space-x-4 text-xs text-gray-500">
                            <span class="flex items-center">
                                <svg class="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                                </svg>
                                Uploaded by ${uploadedBy}
                            </span>
                            <span class="flex items-center">
                                <svg class="mr-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                                ${dateStr} at ${timeStr}
                            </span>
                        </div>
                    </div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        ${recordType}
                    </span>
                </div>
            `;
            activityList.appendChild(li);
        });
        
        if (activityList.children.length === 0) {
            activityList.innerHTML = '<li class="px-4 py-4"><p class="text-sm text-gray-500">No recent activity</p></li>';
        }
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        // For now, just show placeholder data
        document.getElementById('appointmentCount').textContent = '0';
        document.getElementById('prescriptionCount').textContent = '0';
        document.getElementById('recordCount').textContent = '0';
        document.getElementById('recentActivity').innerHTML = '<li class="px-4 py-4"><p class="text-sm text-gray-500">No recent activity</p></li>';
    }
}