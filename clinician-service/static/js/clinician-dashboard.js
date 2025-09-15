// Patient List Animation Functions
let isExpanded = false;
let allPatients = [];
let filteredPatients = [];
let currentPage = 1;
const patientsPerPage = 10;

function expandPatientList() {
    if (isExpanded) return;
    isExpanded = true;
    
    const actionButtons = document.getElementById('actionButtons');
    const patientListPanel = document.getElementById('patientListPanel');
    const container = document.getElementById('quickActionsContainer');
    
    // Start fading out buttons
    actionButtons.classList.add('hiding');
    container.classList.add('expanded');
    
    // After fade out, hide buttons and show panel
    setTimeout(() => {
        actionButtons.classList.add('hidden');
        patientListPanel.classList.add('showing');
        fetchPatients();
    }, 200);
}

function collapsePatientList() {
    if (!isExpanded) return;
    isExpanded = false;
    
    const actionButtons = document.getElementById('actionButtons');
    const patientListPanel = document.getElementById('patientListPanel');
    const container = document.getElementById('quickActionsContainer');
    
    // Start fading out panel
    patientListPanel.classList.remove('showing');
    container.classList.remove('expanded');
    
    // After fade out, show buttons
    setTimeout(() => {
        actionButtons.classList.remove('hidden');
        // Small delay to trigger reflow before removing hiding class
        requestAnimationFrame(() => {
            actionButtons.classList.remove('hiding');
        });
    }, 200);
}

async function fetchPatients() {
    const contentDiv = document.getElementById('patientListContent');
    const accessToken = localStorage.getItem('access_token');
    
    try {
        const response = await fetch('/api/clinician/patients/', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
        });

        if (response.ok) {
            const data = await response.json();
            allPatients = data.results || [];
            filteredPatients = [...allPatients];
            currentPage = 1;
            displayPatients();
        } else if (response.status === 401) {
            await window.tokenUtils.refreshAccessToken();
            await fetchPatients(); // Retry after refreshing token
        } else {
            contentDiv.innerHTML = '<p class="text-red-500 text-center py-4">Failed to load patients. Please try again.</p>';
        }
    } catch (error) {
        console.error('Failed to fetch patients:', error);
        contentDiv.innerHTML = '<p class="text-red-500 text-center py-4">Network error. Please check your connection.</p>';
    }
}

function displayPatients() {
    const contentDiv = document.getElementById('patientListContent');
    const paginationDiv = document.getElementById('paginationControls');
    
    if (filteredPatients.length === 0) {
        contentDiv.innerHTML = '<p class="text-gray-500 text-center py-8">No patients found.</p>';
        paginationDiv.classList.add('hidden');
        return;
    }

    // Calculate pagination
    const totalPages = Math.ceil(filteredPatients.length / patientsPerPage);
    const startIndex = (currentPage - 1) * patientsPerPage;
    const endIndex = Math.min(startIndex + patientsPerPage, filteredPatients.length);
    const paginatedPatients = filteredPatients.slice(startIndex, endIndex);

    // Check if mobile view (less than 768px)
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
        // Mobile card layout
        let html = '<div class="space-y-4">';
        
        paginatedPatients.forEach(patient => {
            const user = patient.user || {};
            const assignment = patient.assignment || {};
            
            html += '<div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">';
            html += '<div class="flex justify-between items-start mb-3">';
            html += `<h3 class="text-sm font-semibold text-gray-900">${user.first_name || ''} ${user.last_name || ''}</h3>`;
            html += `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">${patient.gender || '-'}</span>`;
            html += '</div>';
            
            html += '<div class="space-y-1 text-xs text-gray-600">';
            html += `<div class="flex items-center"><svg class="w-3 h-3 mr-1.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg><span class="break-all">${user.email || '-'}</span></div>`;
            html += `<div class="flex items-center"><svg class="w-3 h-3 mr-1.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>${patient.phone_number || '-'}</div>`;
            if (assignment.cancer_subtype_name) {
                html += `<div class="flex items-center"><svg class="w-3 h-3 mr-1.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>${assignment.cancer_subtype_name}</div>`;
            }
            if (assignment.assigned_at) {
                html += `<div class="flex items-center"><svg class="w-3 h-3 mr-1.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>Assigned: ${new Date(assignment.assigned_at).toLocaleDateString()}</div>`;
            }
            html += '</div>';
            
            html += '<div class="mt-3">';
            html += `<a href="/clinician/patients/${patient.id}/dashboard/" class="block w-full text-center px-3 py-2 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">`;
            html += 'View Dashboard';
            html += '</a>';
            html += '</div>';
            html += '</div>';
        });
        
        html += '</div>';
        contentDiv.innerHTML = html;
    } else {
        // Desktop table layout
        let html = '<div class="overflow-x-auto"><table class="min-w-full divide-y divide-gray-200">';
        html += '<thead class="bg-gray-50"><tr>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Patient Name</th>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Phone</th>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Gender</th>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cancer Type</th>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assigned Date</th>';
        html += '<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>';
        html += '</tr></thead><tbody class="bg-white divide-y divide-gray-200">';

        paginatedPatients.forEach(patient => {
            const user = patient.user || {};
            const assignment = patient.assignment || {};
            html += '<tr class="hover:bg-gray-50">';
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.first_name || ''} ${user.last_name || ''}</td>`;
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.email || '-'}</td>`;
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${patient.phone_number || '-'}</td>`;
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${patient.gender || '-'}</td>`;
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${assignment.cancer_subtype_name || '-'}</td>`;
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${assignment.assigned_at ? new Date(assignment.assigned_at).toLocaleDateString() : '-'}</td>`;
            html += `<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">`;
            html += `<a href="/clinician/patients/${patient.id}/dashboard/" class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">`;
            html += `View Dashboard`;
            html += `</a>`;
            html += `</td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        contentDiv.innerHTML = html;
    }

    // Update pagination controls
    updatePaginationControls(startIndex + 1, endIndex, filteredPatients.length, totalPages);
}

function updatePaginationControls(start, end, total, totalPages) {
    const paginationDiv = document.getElementById('paginationControls');
    document.getElementById('startRecord').textContent = start;
    document.getElementById('endRecord').textContent = end;
    document.getElementById('totalRecords').textContent = total;

    // Show/hide pagination if needed
    if (total > patientsPerPage) {
        paginationDiv.classList.remove('hidden');
        
        // Update buttons
        document.getElementById('prevPage').disabled = currentPage === 1;
        document.getElementById('nextPage').disabled = currentPage === totalPages;

        // Generate page numbers
        const pageNumbers = document.getElementById('pageNumbers');
        let pageHtml = '';
        
        // Show fewer page numbers on mobile
        const isMobile = window.innerWidth < 640;
        const maxPages = isMobile ? 3 : 5;
        
        // Calculate page range to show
        let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
        let endPage = Math.min(totalPages, startPage + maxPages - 1);
        
        // Adjust if we're near the end
        if (endPage - startPage < maxPages - 1) {
            startPage = Math.max(1, endPage - maxPages + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === currentPage;
            pageHtml += `<button class="px-2 sm:px-3 py-1 text-xs sm:text-sm border ${isActive ? 'bg-blue-500 text-white border-blue-500' : 'border-gray-300 hover:bg-gray-50'} rounded-md" onclick="goToPage(${i})">${i}</button>`;
        }
        
        pageNumbers.innerHTML = pageHtml;
    } else {
        paginationDiv.classList.add('hidden');
    }
}

function searchPatients(query) {
    const searchTerm = query.toLowerCase().trim();
    
    if (!searchTerm) {
        filteredPatients = [...allPatients];
    } else {
        filteredPatients = allPatients.filter(patient => {
            const user = patient.user || {};
            const fullName = `${user.first_name || ''} ${user.last_name || ''}`.toLowerCase();
            const email = (user.email || '').toLowerCase();
            
            return fullName.includes(searchTerm) || email.includes(searchTerm);
        });
    }
    
    currentPage = 1; // Reset to first page
    displayPatients();
}

function goToPage(page) {
    currentPage = page;
    displayPatients();
}

function viewPatientDashboard(patientId) {
    window.location.href = `/clinician/patients/${patientId}/dashboard/`;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add click handlers
    const patientListBtn = document.getElementById('patientListBtn');
    if (patientListBtn) {
        patientListBtn.addEventListener('click', expandPatientList);
    }

    const panelHeader = document.getElementById('panelHeader');
    if (panelHeader) {
        panelHeader.addEventListener('click', collapsePatientList);
    }

    const patientsLink = document.getElementById('patients-link');
    if (patientsLink) {
        patientsLink.addEventListener('click', function(e) {
            e.preventDefault();
            expandPatientList();
        });
    }

    // Search functionality
    const patientSearch = document.getElementById('patientSearch');
    if (patientSearch) {
        patientSearch.addEventListener('input', function(e) {
            searchPatients(e.target.value);
        });
    }

    // Pagination controls
    const prevPage = document.getElementById('prevPage');
    if (prevPage) {
        prevPage.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                displayPatients();
            }
        });
    }

    const nextPage = document.getElementById('nextPage');
    if (nextPage) {
        nextPage.addEventListener('click', function() {
            const totalPages = Math.ceil(filteredPatients.length / patientsPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                displayPatients();
            }
        });
    }

    // Handle window resize to update patient list display
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            if (isExpanded && filteredPatients.length > 0) {
                displayPatients();
            }
        }, 250);
    });
});