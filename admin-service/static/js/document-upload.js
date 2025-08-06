// Document Upload JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadDropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const selectedFilesContainer = document.getElementById('selectedFilesContainer');
    const selectedFilesList = document.getElementById('selectedFilesList');
    const clearButton = document.getElementById('clearButton');
    const uploadSubmitButton = document.getElementById('uploadSubmitButton');
    const uploadForm = document.getElementById('documentUploadForm');
    const uploadProgressModal = document.getElementById('uploadProgressModal');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const cancerTypeSelect = document.getElementById('cancerType');

    // File storage
    let selectedFiles = new Map();

    // File type validation
    const allowedTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'text/x-markdown'
    ];

    const allowedExtensions = ['.pdf', '.doc', '.docx', '.txt', '.md'];

    // Max file size (10MB)
    const maxFileSize = 10 * 1024 * 1024;

    // Load cancer types on page load
    loadCancerTypes();

    // Click to upload
    uploadButton.addEventListener('click', function(e) {
        e.preventDefault();
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
    });

    // Drag and drop events
    uploadDropzone.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.add('drag-over');
    });

    uploadDropzone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.remove('drag-over');
    });

    uploadDropzone.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    // Handle file selection
    function handleFiles(files) {
        for (let file of files) {
            if (validateFile(file)) {
                selectedFiles.set(file.name, file);
            }
        }
        updateFilesList();
        updateSubmitButton();
    }

    // Validate file
    function validateFile(file) {
        // Check file extension
        const fileName = file.name.toLowerCase();
        const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
        
        if (!hasValidExtension) {
            showError(`File "${file.name}" has an invalid extension. Allowed: ${allowedExtensions.join(', ')}`);
            return false;
        }

        // Check file size
        if (file.size > maxFileSize) {
            showError(`File "${file.name}" is too large. Maximum size is 10MB.`);
            return false;
        }

        // Check if already selected
        if (selectedFiles.has(file.name)) {
            showError(`File "${file.name}" is already selected.`);
            return false;
        }

        return true;
    }

    // Update files list display
    function updateFilesList() {
        selectedFilesList.innerHTML = '';
        
        if (selectedFiles.size === 0) {
            selectedFilesContainer.classList.add('hidden');
            return;
        }

        selectedFilesContainer.classList.remove('hidden');

        selectedFiles.forEach((file, fileName) => {
            const li = createFileListItem(file);
            selectedFilesList.appendChild(li);
        });
    }

    // Create file list item
    function createFileListItem(file) {
        const li = document.createElement('li');
        li.className = 'file-list-item';

        const fileInfo = document.createElement('div');
        fileInfo.className = 'file-info';

        const fileIcon = document.createElement('div');
        fileIcon.className = 'file-icon';
        fileIcon.innerHTML = getFileIcon(file.name);

        const fileDetails = document.createElement('div');
        fileDetails.className = 'file-details';

        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name;

        const fileSize = document.createElement('div');
        fileSize.className = 'file-size';
        fileSize.textContent = formatFileSize(file.size);

        fileDetails.appendChild(fileName);
        fileDetails.appendChild(fileSize);

        fileInfo.appendChild(fileIcon);
        fileInfo.appendChild(fileDetails);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'remove-file-btn';
        removeBtn.innerHTML = `
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        `;
        removeBtn.addEventListener('click', function() {
            removeFile(file.name);
        });

        li.appendChild(fileInfo);
        li.appendChild(removeBtn);

        return li;
    }

    // Get file icon based on extension
    function getFileIcon(fileName) {
        const ext = fileName.split('.').pop().toLowerCase();
        switch(ext) {
            case 'pdf':
                return '<svg class="h-6 w-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-5L9 2H4z" clip-rule="evenodd"></path></svg>';
            case 'doc':
            case 'docx':
                return '<svg class="h-6 w-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" clip-rule="evenodd"></path><path fill-rule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 00-2 2v6a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-1a1 1 0 100-2h1a4 4 0 014 4v6a4 4 0 01-4 4H6a4 4 0 01-4-4V7a4 4 0 014-4z" clip-rule="evenodd"></path></svg>';
            case 'txt':
            case 'md':
                return '<svg class="h-6 w-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm2 4a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path></svg>';
            default:
                return '<svg class="h-6 w-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" clip-rule="evenodd"></path><path fill-rule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 00-2 2v6a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-1a1 1 0 100-2h1a4 4 0 014 4v6a4 4 0 01-4 4H6a4 4 0 01-4-4V7a4 4 0 014-4z" clip-rule="evenodd"></path></svg>';
        }
    }

    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Remove file
    function removeFile(fileName) {
        selectedFiles.delete(fileName);
        updateFilesList();
        updateSubmitButton();
    }

    // Clear all files
    clearButton.addEventListener('click', function() {
        selectedFiles.clear();
        fileInput.value = '';
        updateFilesList();
        updateSubmitButton();
    });

    // Update submit button state
    function updateSubmitButton() {
        uploadSubmitButton.disabled = selectedFiles.size === 0;
    }

    // Handle form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (selectedFiles.size === 0) {
            showError('Please select at least one file to upload.');
            return;
        }

        if (!cancerTypeSelect.value) {
            showError('Please select a cancer type.');
            return;
        }

        // Show upload progress modal
        uploadProgressModal.classList.remove('hidden');
        
        // Simulate progress (since we don't have real progress from the server)
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += Math.random() * 30;
                progress = Math.min(progress, 90);
                updateProgress(progress);
            }
        }, 300);
        
        // Upload files to server
        uploadFiles().finally(() => {
            clearInterval(progressInterval);
            updateProgress(100);
        });
    });

    // Upload files to server
    async function uploadFiles() {
        const formData = new FormData();
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Add cancer type
        formData.append('cancer_type', cancerTypeSelect.value);
        
        // Add all selected files
        selectedFiles.forEach((file) => {
            formData.append('files', file);
        });
        
        try {
            const response = await fetch('/admin/documents/upload/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData,
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Build success message with embedding status
                let successMessage = data.message;
                
                // Check for embedding status in uploaded files
                if (data.uploaded_files && data.uploaded_files.length > 0) {
                    const embeddingFiles = data.uploaded_files.filter(f => f.embedding_status === 'queued');
                    if (embeddingFiles.length > 0) {
                        successMessage += `. ${embeddingFiles.length} file(s) queued for embedding processing.`;
                    }
                }
                
                // Keep modal visible for a moment to show 100% completion
                setTimeout(() => {
                    uploadProgressModal.classList.add('hidden');
                    showSuccess(successMessage);
                    
                    // Only reload documents if we're on page 1, otherwise just monitor the new uploads
                    if (currentPage === 1) {
                        // Update the documents list after hiding modal
                        updateRecentUploads();
                    }
                    
                    // Start monitoring embedding status for newly uploaded files only
                    if (data.uploaded_files) {
                        data.uploaded_files.forEach(file => {
                            if (file.embedding_job_id) {
                                // If we have a job ID, connect WebSocket directly
                                connectEmbeddingWebSocket(file.embedding_job_id, file.file_id);
                            } else if (file.embedding_status === 'queued' || file.embedding_status === 'processing') {
                                // Otherwise fall back to polling
                                monitorEmbeddingStatus(file.file_id);
                            }
                        });
                    }
                }, 1000);
                
                // Clear form
                selectedFiles.clear();
                fileInput.value = '';
                updateFilesList();
                updateSubmitButton();
                
                // Show any errors
                if (data.errors && data.errors.length > 0) {
                    data.errors.forEach(error => showError(error));
                }
            } else {
                uploadProgressModal.classList.add('hidden');
                showError(data.error || 'Upload failed');
            }
        } catch (error) {
            uploadProgressModal.classList.add('hidden');
            console.error('Upload error:', error);
            showError('Upload failed. Please try again.');
        }
    }

    // Update progress bar
    function updateProgress(percent) {
        progressBar.style.width = percent + '%';
        progressText.textContent = percent + '% Complete';
    }

    // Show error message
    function showError(message) {
        const alert = createAlert(message, 'error');
        document.querySelector('.document-upload-container').insertBefore(alert, document.querySelector('.document-upload-container').firstChild);
        setTimeout(() => alert.remove(), 5000);
    }

    // Show success message
    function showSuccess(message) {
        const alert = createAlert(message, 'success');
        document.querySelector('.document-upload-container').insertBefore(alert, document.querySelector('.document-upload-container').firstChild);
        setTimeout(() => alert.remove(), 8000); // Increased timeout for longer messages
    }

    // Create alert element
    function createAlert(message, type) {
        const div = document.createElement('div');
        div.className = `upload-${type} flex items-center`;
        
        const icon = type === 'success' 
            ? '<svg class="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>'
            : '<svg class="h-5 w-5 mr-2" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>';
        
        div.innerHTML = icon + message;
        return div;
    }

    // Pagination state
    let currentPage = 1;
    let totalPages = 1;
    let pageSize = 10;
    let currentCancerTypeFilter = '';
    
    // Initialize document list on page load
    loadDocuments();
    loadCancerTypesForFilter();
    
    // Pagination event listeners
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadDocuments();
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadDocuments();
        }
    });
    
    document.getElementById('prevPageMobile').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadDocuments();
        }
    });
    
    document.getElementById('nextPageMobile').addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadDocuments();
        }
    });
    
    // Page size change
    document.getElementById('pageSizeSelect').addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value);
        currentPage = 1;
        loadDocuments();
    });
    
    // Cancer type filter
    document.getElementById('cancerTypeFilter').addEventListener('change', (e) => {
        currentCancerTypeFilter = e.target.value;
        currentPage = 1;
        loadDocuments();
    });
    
    // Load documents with pagination
    async function loadDocuments() {
        const tableBody = document.getElementById('documentsTableBody');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const noDocumentsMessage = document.getElementById('noDocumentsMessage');
        const documentsTable = document.getElementById('documentsTable');
        
        // Show loading
        loadingSpinner.classList.remove('hidden');
        documentsTable.classList.add('hidden');
        noDocumentsMessage.classList.add('hidden');
        
        try {
            let url = `/admin/api/rag-documents/?page=${currentPage}&page_size=${pageSize}`;
            if (currentCancerTypeFilter) {
                url += `&cancer_type_id=${currentCancerTypeFilter}`;
            }
            
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load documents');
            }
            
            const data = await response.json();
            
            // Hide loading
            loadingSpinner.classList.add('hidden');
            
            if (data.results && data.results.length > 0) {
                documentsTable.classList.remove('hidden');
                renderDocuments(data.results);
                updatePagination(data);
            } else {
                noDocumentsMessage.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error loading documents:', error);
            loadingSpinner.classList.add('hidden');
            noDocumentsMessage.classList.remove('hidden');
        }
    }
    
    // Helper function to create document name with tooltip
    function createDocumentNameWithTooltip(filename) {
        const maxLength = 20;
        
        if (filename.length > maxLength) {
            // Truncate and add ellipsis
            const truncatedName = filename.substring(0, maxLength) + '...';
            
            return `
                <div class="tooltip-container">
                    <span class="document-name">${truncatedName}</span>
                    <div class="tooltip">${filename}</div>
                </div>
            `;
        } else {
            return `<span class="document-name">${filename}</span>`;
        }
    }
    
    // Render documents in table
    function renderDocuments(documents) {
        // Render desktop view
        const tableBody = document.getElementById('documentsTableBody');
        tableBody.innerHTML = '';
        
        // Render mobile view
        const mobileView = document.getElementById('documentsMobileView');
        mobileView.innerHTML = '';
        
        documents.forEach(doc => {
            const row = document.createElement('tr');
            const uploadDate = doc.file_data.uploaded_at ? 
                new Date(doc.file_data.uploaded_at).toLocaleString() : 'Unknown';
            const fileSize = formatFileSize(doc.file_data.file_size);
            const fileType = getFileTypeFromMimeType(doc.file_data.mime_type);
            
            // Create document name cell with tooltip if truncated
            const documentNameHtml = createDocumentNameWithTooltip(doc.file_data.filename);
            
            row.innerHTML = `
                <td class="text-sm font-medium text-gray-900 document-name-cell">
                    ${documentNameHtml}
                </td>
                <td class="text-sm text-gray-500">
                    ${doc.cancer_type}
                </td>
                <td class="text-sm text-gray-500">
                    ${fileSize}
                </td>
                <td class="text-sm text-gray-500">
                    ${uploadDate}
                </td>
                <td class="text-sm text-gray-500 type-column">
                    ${fileType}
                </td>
                <td class="text-sm text-gray-500">
                    <div id="embedding-status-desktop-${doc.file}" class="embedding-status" data-document-id="${doc.file}">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 animate-pulse">
                            Checking...
                        </span>
                    </div>
                </td>
                <td class="text-right text-sm font-medium">
                    <div class="flex items-center justify-end space-x-2">
                        <button class="text-blue-600 hover:text-blue-900" onclick="downloadDocument('${doc.file}')">
                            Download
                        </button>
                        <button class="text-red-600 hover:text-red-900" onclick="deleteDocument('${doc.file}', '${doc.file_data.filename}')">
                            Delete
                        </button>
                    </div>
                </td>
            `;
            
            tableBody.appendChild(row);
            
            // Check embedding status for this document with a small delay to avoid race conditions
            setTimeout(async () => {
                try {
                    const response = await fetch(`/admin/api/embedding-status/${doc.file}/`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                    
                    if (response.ok) {
                        const statusData = await response.json();
                        updateEmbeddingStatusDisplay(doc.file, statusData);
                    }
                } catch (error) {
                    console.error(`Error checking embedding status for ${doc.file}:`, error);
                }
            }, 100);
            
            // Create mobile card
            const mobileCard = document.createElement('div');
            mobileCard.className = 'bg-white p-4 mb-4 rounded-lg shadow border border-gray-200';
            mobileCard.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <h3 class="text-sm font-medium text-gray-900 break-words">${doc.file_data.filename}</h3>
                    <span class="text-xs text-gray-500 ml-2 flex-shrink-0">${fileType}</span>
                </div>
                <div class="space-y-1 text-xs text-gray-600">
                    <div class="flex justify-between">
                        <span>Cancer Type:</span>
                        <span class="font-medium">${doc.cancer_type}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Size:</span>
                        <span>${fileSize}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Uploaded:</span>
                        <span>${new Date(doc.file_data.uploaded_at).toLocaleDateString()}</span>
                    </div>
                    <div class="flex justify-between items-center mt-1">
                        <span>Embedding:</span>
                        <span id="embedding-status-mobile-${doc.file}" class="embedding-status" data-document-id="${doc.file}">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 animate-pulse">
                                Checking...
                            </span>
                        </span>
                    </div>
                </div>
                <div class="mt-3 flex gap-2">
                    <button class="flex-1 text-xs px-3 py-1.5 text-blue-600 bg-blue-50 rounded hover:bg-blue-100" onclick="downloadDocument('${doc.file}')">
                        Download
                    </button>
                    <button class="flex-1 text-xs px-3 py-1.5 text-red-600 bg-red-50 rounded hover:bg-red-100" onclick="deleteDocument('${doc.file}', '${doc.file_data.filename}')">
                        Delete
                    </button>
                </div>
            `;
            
            mobileView.appendChild(mobileCard);
            
            // Also check embedding status for mobile view (same document ID is used in both views)
            // The status update will apply to both desktop and mobile elements with the same ID
        });
    }
    
    // Update pagination controls
    function updatePagination(data) {
        const totalCount = data.count || 0;
        totalPages = Math.ceil(totalCount / pageSize);
        
        // Update showing text
        const start = (currentPage - 1) * pageSize + 1;
        const end = Math.min(currentPage * pageSize, totalCount);
        
        document.getElementById('pageStart').textContent = totalCount > 0 ? start : 0;
        document.getElementById('pageEnd').textContent = end;
        document.getElementById('totalCount').textContent = totalCount;
        
        // Update page numbers
        const pageNumbers = document.getElementById('pageNumbers');
        pageNumbers.innerHTML = '';
        
        // Generate page numbers
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        if (endPage - startPage < maxVisiblePages - 1) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const button = document.createElement('button');
            button.className = i === currentPage
                ? 'relative z-10 inline-flex items-center bg-red-600 px-4 py-2 text-sm font-semibold text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600'
                : 'relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0';
            button.textContent = i;
            button.addEventListener('click', () => {
                currentPage = i;
                loadDocuments();
            });
            pageNumbers.appendChild(button);
        }
        
        // Update button states
        const prevPage = document.getElementById('prevPage');
        const nextPage = document.getElementById('nextPage');
        const prevPageMobile = document.getElementById('prevPageMobile');
        const nextPageMobile = document.getElementById('nextPageMobile');
        
        prevPage.disabled = currentPage === 1;
        nextPage.disabled = currentPage === totalPages;
        prevPageMobile.disabled = currentPage === 1;
        nextPageMobile.disabled = currentPage === totalPages;
        
        if (currentPage === 1) {
            prevPage.classList.add('cursor-not-allowed', 'opacity-50');
            prevPageMobile.classList.add('cursor-not-allowed', 'opacity-50');
        } else {
            prevPage.classList.remove('cursor-not-allowed', 'opacity-50');
            prevPageMobile.classList.remove('cursor-not-allowed', 'opacity-50');
        }
        
        if (currentPage === totalPages || totalPages === 0) {
            nextPage.classList.add('cursor-not-allowed', 'opacity-50');
            nextPageMobile.classList.add('cursor-not-allowed', 'opacity-50');
        } else {
            nextPage.classList.remove('cursor-not-allowed', 'opacity-50');
            nextPageMobile.classList.remove('cursor-not-allowed', 'opacity-50');
        }
    }
    
    // Load cancer types for filter dropdown
    async function loadCancerTypesForFilter() {
        try {
            const response = await fetch('/admin/api/cancer-types/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const cancerTypes = await response.json();
                const filterSelect = document.getElementById('cancerTypeFilter');
                
                cancerTypes.forEach(ct => {
                    const option = document.createElement('option');
                    option.value = ct.id;
                    option.textContent = ct.cancer_type;
                    filterSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading cancer types for filter:', error);
        }
    }
    
    // Get file type from MIME type
    function getFileTypeFromMimeType(mimeType) {
        if (!mimeType) return 'Unknown';
        
        if (mimeType.includes('pdf')) return 'PDF';
        if (mimeType.includes('word') || mimeType.includes('document')) return 'Word';
        if (mimeType.includes('text')) return 'Text';
        if (mimeType.includes('markdown')) return 'Markdown';
        
        return mimeType.split('/')[1]?.toUpperCase() || 'Unknown';
    }
    
    // Download document
    window.downloadDocument = function(fileId) {
        // This would typically make an API call to get a download URL
        // For now, we'll just show a message
        showSuccess('Download functionality will be implemented with file service integration');
    }
    
    // Delete document
    window.deleteDocument = function(fileId, fileName) {
        // Show custom modal
        showDeleteModal(fileName, async () => {
            try {
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                const response = await fetch(`/admin/api/rag-documents/${fileId}/delete/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });
                
                if (response.ok) {
                    showSuccess(`Document "${fileName}" deleted successfully`);
                    // Reload the documents list
                    loadDocuments();
                } else {
                    const error = await response.json();
                    showError(error.error || 'Failed to delete document');
                }
            } catch (error) {
                console.error('Error deleting document:', error);
                showError('An error occurred while deleting the document');
            }
        });
    }
    
    // Show delete confirmation modal
    function showDeleteModal(fileName, onConfirm) {
        const modal = document.getElementById('deleteConfirmModal');
        const modalContent = document.getElementById('deleteModalContent');
        const fileNameSpan = document.getElementById('deleteFileName');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        const cancelBtn = document.getElementById('cancelDeleteBtn');
        
        // Set the file name
        fileNameSpan.textContent = fileName;
        
        // Show modal with animation
        modal.classList.remove('hidden');
        setTimeout(() => {
            modal.classList.add('opacity-100');
            modalContent.classList.remove('scale-95', 'opacity-0');
            modalContent.classList.add('scale-100', 'opacity-100');
        }, 10);
        
        // Handle confirm
        const handleConfirm = () => {
            hideDeleteModal();
            onConfirm();
        };
        
        // Handle cancel
        const handleCancel = () => {
            hideDeleteModal();
        };
        
        // Add event listeners
        confirmBtn.onclick = handleConfirm;
        cancelBtn.onclick = handleCancel;
        
        // Close on backdrop click
        modal.onclick = (e) => {
            if (e.target === modal) {
                handleCancel();
            }
        };
        
        // Close on Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                handleCancel();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    }
    
    // Hide delete confirmation modal
    function hideDeleteModal() {
        const modal = document.getElementById('deleteConfirmModal');
        const modalContent = document.getElementById('deleteModalContent');
        
        // Hide with animation
        modal.classList.remove('opacity-100');
        modalContent.classList.remove('scale-100', 'opacity-100');
        modalContent.classList.add('scale-95', 'opacity-0');
        
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 200);
    }

    // Load cancer types from the API
    async function loadCancerTypes() {
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            const response = await fetch('/admin/api/cancer-types/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load cancer types');
            }
            
            const data = await response.json();
            
            // Clear existing options
            cancerTypeSelect.innerHTML = '<option value="">Select a cancer type</option>';
            
            // Add cancer types (already filtered to parent types by the API)
            data.forEach(cancerType => {
                const option = document.createElement('option');
                option.value = cancerType.id;
                option.textContent = cancerType.cancer_type;
                cancerTypeSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading cancer types:', error);
            showError('Failed to load cancer types. Please refresh the page.');
        }
    }
    
    // Update progress bar
    function updateProgress(percent) {
        if (progressBar && progressText) {
            progressBar.style.width = percent + '%';
            progressText.textContent = Math.round(percent) + '% Complete';
        }
    }
    
    // Function to update recent uploads after successful upload
    async function updateRecentUploads() {
        // Simply reload the documents table
        if (typeof loadDocuments === 'function') {
            await loadDocuments();
        } else {
            console.error('loadDocuments function not found');
        }
    }
    
    // Make updateRecentUploads available globally if needed
    window.updateRecentUploads = updateRecentUploads;
    
    // WebSocket connections for embedding status
    const embeddingWebSockets = new Map();
    
    // Track which documents are actively being processed to avoid duplicate updates
    const activelyProcessingDocs = new Set();
    
    // Function to monitor embedding status
    function monitorEmbeddingStatus(documentId) {
        // Skip if already monitoring this document
        if (activelyProcessingDocs.has(documentId)) {
            return;
        }
        
        activelyProcessingDocs.add(documentId);
        
        // First check if there's a job ID from the recent upload
        const checkInitialStatus = async () => {
            try {
                const response = await fetch(`/admin/api/embedding-status/${documentId}/`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    updateEmbeddingStatusDisplay(documentId, data);
                    
                    // If processing, try to get job ID and connect WebSocket
                    if (data.status === 'processing' || data.status === 'pending') {
                        // Check for job_id in response
                        const jobId = data.job_id;
                        
                        if (jobId) {
                            connectEmbeddingWebSocket(jobId, documentId);
                        } else {
                            // Fall back to polling
                            setTimeout(() => checkInitialStatus(), 5000);
                        }
                    } else {
                        // Not processing anymore, remove from tracking
                        activelyProcessingDocs.delete(documentId);
                    }
                }
            } catch (error) {
                console.error(`Error checking embedding status for ${documentId}:`, error);
            }
        };
        
        checkInitialStatus();
    }
    
    // Function to connect WebSocket for real-time updates
    function connectEmbeddingWebSocket(jobId, documentId) {
        // Close existing connection if any
        if (embeddingWebSockets.has(jobId)) {
            embeddingWebSockets.get(jobId).close();
        }
        
        const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${wsScheme}://${window.location.host}/ws/embedding/progress/${jobId}/`;
        
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            embeddingWebSockets.set(jobId, socket);
        };
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Ensure we're updating the correct document
            if (data.job_id !== jobId) {
                console.warn(`Received update for wrong job: ${data.job_id} vs ${jobId}`);
                return;
            }
            
            if (data.type === 'progress_update') {
                updateEmbeddingStatusDisplay(documentId, {
                    status: data.status,
                    message: data.message,
                    progress: data.progress
                });
            } else if (data.type === 'job_complete') {
                // When job completes, fetch the actual embedding status to get chunk count
                socket.close();
                embeddingWebSockets.delete(jobId);
                activelyProcessingDocs.delete(documentId);
                
                // Small delay to ensure embeddings are saved in database
                setTimeout(() => {
                    // Fetch the actual status with chunk count
                    fetch(`/admin/api/embedding-status/${documentId}/`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    })
                    .then(response => response.json())
                    .then(statusData => {
                        updateEmbeddingStatusDisplay(documentId, statusData);
                    })
                    .catch(error => {
                        console.error(`Error fetching final status for ${documentId}:`, error);
                        // Fallback to the WebSocket data
                        updateEmbeddingStatusDisplay(documentId, {
                            status: 'completed',
                            message: data.message,
                            chunks_count: data.chunks_count || 0
                        });
                    });
                }, 1000); // 1 second delay
            } else if (data.type === 'job_error') {
                updateEmbeddingStatusDisplay(documentId, {
                    status: 'error',
                    message: data.message
                });
                socket.close();
                embeddingWebSockets.delete(jobId);
                activelyProcessingDocs.delete(documentId);
            }
        };
        
        socket.onerror = (error) => {
            console.error(`WebSocket error for job ${jobId}:`, error);
        };
        
        socket.onclose = () => {
            embeddingWebSockets.delete(jobId);
            activelyProcessingDocs.delete(documentId);
        };
    }
    
    // Function to update embedding status display
    function updateEmbeddingStatusDisplay(documentId, statusData) {
        // Update both desktop and mobile views
        const desktopElement = document.getElementById(`embedding-status-desktop-${documentId}`);
        const mobileElement = document.getElementById(`embedding-status-mobile-${documentId}`);
        
        
        if (!desktopElement && !mobileElement) {
            // Document might not be visible in current page
            return;
        }
        
        // Don't update if this is a stale update (document already completed)
        if (desktopElement && desktopElement.querySelector('.bg-green-100') && statusData.status === 'processing') {
            return;
        }
        
        let statusHtml = '';
        const progress = statusData.progress || {};
        
        switch (statusData.status) {
            case 'completed':
                const chunksCount = statusData.chunks_count || statusData.message?.match(/\d+/)?.[0] || '0';
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Ready (${chunksCount})
                    </span>
                `;
                break;
            case 'processing':
                const percentage = progress.percentage || 0;
                const phase = progress.phase || 'processing';
                
                // Show processing with progress if available
                if (phase === 'embedding' && progress.total_chunks) {
                    statusHtml = `
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">
                            Processing ${percentage}%
                        </span>
                    `;
                } else {
                    // Simple processing indicator
                    statusHtml = `
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">
                            Processing
                        </span>
                    `;
                }
                break;
            case 'pending':
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Queued
                    </span>
                `;
                break;
            case 'error':
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Failed
                    </span>
                `;
                break;
            case 'not_started':
            case 'no_embeddings':
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        Not processed
                    </span>
                `;
                break;
            default:
                // Keep "Checking..." for truly unknown states
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 animate-pulse">
                        Checking...
                    </span>
                `;
        }
        
        
        // Update both desktop and mobile elements if they exist
        if (desktopElement) {
            desktopElement.innerHTML = statusHtml;
        }
        if (mobileElement) {
            mobileElement.innerHTML = statusHtml;
        }
    }
    
    // Check embedding status for all visible documents
    function checkAllEmbeddingStatuses() {
        const statusElements = document.querySelectorAll('.embedding-status');
        
        // Use a Set to avoid checking the same document twice
        const checkedDocuments = new Set();
        
        statusElements.forEach(async element => {
            const documentId = element.getAttribute('data-document-id');
            
            // Skip if already being monitored or already checked
            if (documentId && !checkedDocuments.has(documentId) && !activelyProcessingDocs.has(documentId)) {
                checkedDocuments.add(documentId);
                // First check status to see if we need to monitor
                try {
                    const response = await fetch(`/admin/api/embedding-status/${documentId}/`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        credentials: 'same-origin'
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        updateEmbeddingStatusDisplay(documentId, data);
                        
                        // Only monitor if still processing
                        if (data.status === 'processing' || data.status === 'pending') {
                            monitorEmbeddingStatus(documentId);
                        }
                    } else {
                        console.error(`Failed to get embedding status for ${documentId}: ${response.status}`);
                    }
                } catch (error) {
                    console.error(`Error checking initial status for ${documentId}:`, error);
                }
            }
        });
    }
    
    // Override loadDocuments to include status checking
    const originalLoadDocuments = loadDocuments;
    window.loadDocuments = loadDocuments = async function() {
        await originalLoadDocuments.apply(this, arguments);
        setTimeout(checkAllEmbeddingStatuses, 500); // Give DOM time to update
    };
    
    // Also check statuses on initial page load
    setTimeout(checkAllEmbeddingStatuses, 1000);
    
});