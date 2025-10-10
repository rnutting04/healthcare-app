// Medical Records JavaScript

let currentPage = 1;
const recordsPerPage = 10;
let allRecords = [];
let filteredRecords = [];

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    loadMedicalRecordTypes();
    loadMedicalRecords();
    setupEventListeners();
});

// Load medical record types from API
async function loadMedicalRecordTypes() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            console.error('No access token found');
            return;
        }
        
        const response = await fetch('/api/patients/medical-records/record_types/', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load record types');
        }
        
        const recordTypes = await response.json();
        
        // Populate the select dropdown
        const selectElement = document.getElementById('recordTypeFilter');
        
        // Clear existing options except the first one (All Types)
        while (selectElement.options.length > 1) {
            selectElement.remove(1);
        }
        
        // Add record types from database
        recordTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.type_name.toLowerCase().replace(/ /g, '_');
            option.textContent = type.type_name;
            selectElement.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading record types:', error);
        // If loading fails, keep the hardcoded options as fallback
    }
}

// Setup event listeners
function setupEventListeners() {
    // Filter buttons
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('recordTypeFilter').addEventListener('change', applyFilters);
    document.getElementById('dateFilter').addEventListener('change', applyFilters);
    document.getElementById('searchRecords').addEventListener('input', debounce(applyFilters, 300));
    
    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => changePage(-1));
    document.getElementById('nextPage').addEventListener('click', () => changePage(1));
    
    // Modal
    document.getElementById('closeModal').addEventListener('click', closeModal);
    document.getElementById('downloadRecord').addEventListener('click', downloadCurrentRecord);
    
    // Close modal when clicking outside
    document.getElementById('recordModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
}

// Load medical records from API
async function loadMedicalRecords() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            console.error('No access token found');
            window.location.href = '/login/?next=/patient/medical-records/';
            return;
        }
        
        const response = await fetch('/api/patients/medical-records/', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load medical records');
        }
        
        const data = await response.json();
        console.log('Medical records API response:', data);
        
        // Handle paginated response from database service
        if (data && data.results && Array.isArray(data.results)) {
            allRecords = data.results;
        } else if (Array.isArray(data)) {
            allRecords = data;
        } else {
            console.warn('Unexpected response format:', data);
            allRecords = [];
        }
        
        // Ensure allRecords is always an array
        if (!Array.isArray(allRecords)) {
            console.error('allRecords is not an array:', allRecords);
            allRecords = [];
        }
        
        filteredRecords = [...allRecords];
        
        updateSummaryCards();
        displayRecords();
        
    } catch (error) {
        console.error('Error loading medical records:', error);
        showEmptyState();
    }
}

// Update summary cards
function updateSummaryCards() {
    // Count records by type using the correct field structure
    const labCount = allRecords.filter(r => {
        if (r.medical_record_type_detail && r.medical_record_type_detail.type_name) {
            return r.medical_record_type_detail.type_name.toLowerCase().includes('lab');
        }
        return r.record_type === 'lab_result';
    }).length;
    
    const imagingCount = allRecords.filter(r => {
        if (r.medical_record_type_detail && r.medical_record_type_detail.type_name) {
            return r.medical_record_type_detail.type_name.toLowerCase().includes('imaging');
        }
        return r.record_type === 'imaging';
    }).length;
    
    const consultationCount = allRecords.filter(r => {
        if (r.medical_record_type_detail && r.medical_record_type_detail.type_name) {
            return r.medical_record_type_detail.type_name.toLowerCase().includes('consultation');
        }
        return r.record_type === 'consultation';
    }).length;
    
    document.getElementById('totalRecords').textContent = allRecords.length;
    document.getElementById('labResults').textContent = labCount;
    document.getElementById('imagingRecords').textContent = imagingCount;
    document.getElementById('consultationRecords').textContent = consultationCount;
}

// Apply filters
function applyFilters() {
    const recordType = document.getElementById('recordTypeFilter').value;
    const dateFilter = document.getElementById('dateFilter').value;
    const searchTerm = document.getElementById('searchRecords').value.toLowerCase();
    
    filteredRecords = allRecords.filter(record => {
        // Filter by record type
        if (recordType && record.record_type !== recordType) {
            return false;
        }
        
        // Filter by date range
        if (dateFilter && !isWithinDateRange(record.created_at, dateFilter)) {
            return false;
        }
        
        // Filter by search term
        if (searchTerm) {
            const searchableText = `${record.title} ${record.description} ${record.provider_name}`.toLowerCase();
            if (!searchableText.includes(searchTerm)) {
                return false;
            }
        }
        
        return true;
    });
    
    currentPage = 1;
    displayRecords();
}

// Check if date is within range
function isWithinDateRange(dateString, range) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now - date;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    switch(range) {
        case 'week': return diffDays <= 7;
        case 'month': return diffDays <= 30;
        case '3months': return diffDays <= 90;
        case '6months': return diffDays <= 180;
        case 'year': return diffDays <= 365;
        default: return true;
    }
}

// Display records with pagination
function displayRecords() {
    const container = document.getElementById('recordsContainer');
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    const pagination = document.getElementById('pagination');
    
    // Hide loading
    loadingState.classList.add('hidden');
    
    if (filteredRecords.length === 0) {
        container.classList.add('hidden');
        emptyState.classList.remove('hidden');
        pagination.classList.add('hidden');
        return;
    }
    
    // Show container, hide empty state
    container.classList.remove('hidden');
    emptyState.classList.add('hidden');
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * recordsPerPage;
    const endIndex = Math.min(startIndex + recordsPerPage, filteredRecords.length);
    const recordsToShow = filteredRecords.slice(startIndex, endIndex);
    
    // Clear container and add records
    container.innerHTML = '';
    recordsToShow.forEach(record => {
        container.appendChild(createRecordElement(record));
    });
    
    // Update pagination
    updatePagination(startIndex + 1, endIndex, filteredRecords.length);
}

// Create record element
function createRecordElement(record) {
    const div = document.createElement('div');
    
    // Extract the actual record type name
    let recordTypeName = 'unknown';
    if (record.medical_record_type_detail && record.medical_record_type_detail.type_name) {
        recordTypeName = record.medical_record_type_detail.type_name.toLowerCase().replace(/ /g, '_');
    } else if (record.record_type) {
        recordTypeName = record.record_type;
    }
    
    div.className = `record-card p-6 border-b border-gray-200 hover:bg-gray-50 cursor-pointer record-type-${recordTypeName}`;
    
    const recordDate = new Date(record.created_at).toLocaleDateString();
    
    // Get the display label for the record type
    let recordTypeLabel = 'Medical Record';
    if (record.medical_record_type_detail && record.medical_record_type_detail.type_name) {
        recordTypeLabel = record.medical_record_type_detail.type_name;
    } else if (record.record_type) {
        recordTypeLabel = getRecordTypeLabel(record.record_type);
    }
    
    // Get title from file details or default
    let recordTitle = 'Medical Record';
    if (record.file_detail && record.file_detail.filename) {
        recordTitle = record.file_detail.filename.replace('.pdf', '').replace(/_/g, ' ');
    } else if (record.title) {
        recordTitle = record.title;
    }
    
    const statusBadge = getStatusBadge(record.status || 'reviewed');
    
    div.innerHTML = `
        <div class="flex items-center justify-between">
            <div class="flex-1">
                <div class="flex items-center space-x-3">
                    <h4 class="text-lg font-semibold text-gray-900">${recordTitle}</h4>
                    <span class="status-badge ${statusBadge.class}">${statusBadge.text}</span>
                </div>
                <p class="text-sm text-gray-600 mt-1">${record.description || 'No description available'}</p>
                <div class="flex items-center space-x-4 mt-2">
                    <span class="text-xs text-gray-500">
                        <svg class="inline w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                        </svg>
                        ${recordDate}
                    </span>
                    <span class="text-xs text-gray-500">
                        <svg class="inline w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        ${recordTypeLabel}
                    </span>
                    ${record.provider_name ? `
                    <span class="text-xs text-gray-500">
                        <svg class="inline w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                        </svg>
                        ${record.provider_name}
                    </span>
                    ` : ''}
                </div>
            </div>
            <div class="ml-4">
                <button onclick="viewRecordDetails('${record.id}')" class="text-blue-600 hover:text-blue-800">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    div.addEventListener('click', () => viewRecordDetails(record.id));
    
    return div;
}

// Get record type label
function getRecordTypeLabel(type) {
    const labels = {
        'lab_result': 'Lab Results',
        'imaging': 'Imaging',
        'consultation': 'Consultation',
        'prescription': 'Prescription',
        'pathology': 'Pathology Report'
    };
    return labels[type] || type;
}

// Get status badge
function getStatusBadge(status) {
    const badges = {
        'new': { text: 'New', class: 'status-new' },
        'reviewed': { text: 'Reviewed', class: 'status-reviewed' },
        'pending': { text: 'Pending', class: 'status-pending' }
    };
    return badges[status] || { text: status, class: 'status-reviewed' };
}

// View record details
async function viewRecordDetails(recordId) {
    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/patients/medical-records/${recordId}/`, {
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load record details');
        }
        
        const record = await response.json();
        showRecordModal(record);
        
    } catch (error) {
        console.error('Error loading record details:', error);
        alert('Failed to load record details');
    }
}

// Show record modal
function showRecordModal(record) {
    const modal = document.getElementById('recordModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalContent = document.getElementById('modalContent');
    
    modalTitle.textContent = record.title || 'Medical Record';
    
    const recordDate = new Date(record.created_at).toLocaleDateString();
    const recordTypeLabel = getRecordTypeLabel(record.record_type);
    
    modalContent.innerHTML = `
        <div class="space-y-4">
            <div class="record-detail-section">
                <div class="record-detail-label">Date</div>
                <div class="record-detail-value">${recordDate}</div>
            </div>
            
            <div class="record-detail-section">
                <div class="record-detail-label">Type</div>
                <div class="record-detail-value">${recordTypeLabel}</div>
            </div>
            
            ${record.provider_name ? `
            <div class="record-detail-section">
                <div class="record-detail-label">Provider</div>
                <div class="record-detail-value">${record.provider_name}</div>
            </div>
            ` : ''}
            
            <div class="record-detail-section">
                <div class="record-detail-label">Description</div>
                <div class="record-detail-value">${record.description || 'No description available'}</div>
            </div>
            
            ${record.notes ? `
            <div class="record-detail-section">
                <div class="record-detail-label">Notes</div>
                <div class="record-detail-value">${record.notes}</div>
            </div>
            ` : ''}
            
            ${record.attachments && record.attachments.length > 0 ? `
            <div class="record-detail-section">
                <div class="record-detail-label">Attachments</div>
                <div class="mt-2">
                    ${record.attachments.map(att => `
                        <div class="attachment-item">
                            <svg class="attachment-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                            </svg>
                            <span>${att.name}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
    
    // Store current record for download
    modal.dataset.recordId = record.id;
    
    // Show modal
    modal.classList.remove('hidden');
}

// Close modal
function closeModal() {
    const modal = document.getElementById('recordModal');
    modal.classList.add('hidden');
}

// Download current record
function downloadCurrentRecord() {
    const modal = document.getElementById('recordModal');
    const recordId = modal.dataset.recordId;
    
    if (recordId) {
        // In a real application, this would trigger a download
        console.log('Downloading record:', recordId);
        alert('Download functionality would be implemented here');
    }
}

// Update pagination
function updatePagination(start, end, total) {
    const pagination = document.getElementById('pagination');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    
    if (total === 0) {
        pagination.classList.add('hidden');
        return;
    }
    
    pagination.classList.remove('hidden');
    
    document.getElementById('showingStart').textContent = start;
    document.getElementById('showingEnd').textContent = end;
    document.getElementById('totalCount').textContent = total;
    
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = end >= total;
}

// Change page
function changePage(direction) {
    const maxPages = Math.ceil(filteredRecords.length / recordsPerPage);
    const newPage = currentPage + direction;
    
    if (newPage >= 1 && newPage <= maxPages) {
        currentPage = newPage;
        displayRecords();
        
        // Scroll to top of records
        document.getElementById('recordsContainer').scrollIntoView({ behavior: 'smooth' });
    }
}

// Show empty state
function showEmptyState() {
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('recordsContainer').classList.add('hidden');
    document.getElementById('emptyState').classList.remove('hidden');
    document.getElementById('pagination').classList.add('hidden');
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}