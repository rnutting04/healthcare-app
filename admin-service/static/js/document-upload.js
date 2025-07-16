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
            console.log('Upload response:', data);
            
            if (data.success) {
                // Build success message with embedding status
                let successMessage = data.message;
                
                // Check if we have embedding status info
                if (data.uploaded_files && data.uploaded_files.length > 0) {
                    const embeddingStatuses = data.uploaded_files.map(file => {
                        if (file.embedding_status === 'queued') {
                            return `${file.filename}: Queued for embedding (position #${file.queue_position || 'N/A'})`;
                        } else if (file.embedding_status === 'failed') {
                            return `${file.filename}: Upload successful but embedding failed`;
                        } else if (file.embedding_status === 'error') {
                            return `${file.filename}: Upload successful but embedding error occurred`;
                        }
                        return null;
                    }).filter(status => status !== null);
                    
                    if (embeddingStatuses.length > 0) {
                        successMessage += '<br><br><strong>Embedding Status:</strong><br>' + embeddingStatuses.join('<br>');
                    }
                }
                
                // Keep modal visible for a moment to show 100% completion
                setTimeout(() => {
                    uploadProgressModal.classList.add('hidden');
                    showSuccess(successMessage);
                    // Update the documents list after hiding modal
                    updateRecentUploads();
                }, 1000);
                
                // Clear form
                selectedFiles.clear();
                fileInput.value = '';
                updateFilesList();
                updateSubmitButton();
                
                // Show any errors
                if (data.errors && data.errors.length > 0) {
                    console.log('Upload errors:', data.errors);
                    data.errors.forEach(error => showError(error));
                }
            } else {
                uploadProgressModal.classList.add('hidden');
                console.log('Upload failed with response:', data);
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
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ${doc.file_data.filename}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${doc.cancer_type}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${fileSize}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${uploadDate}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${fileType}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <div class="embedding-status" data-document-id="${doc.file}">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Checking...
                        </span>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div class="flex items-center justify-end space-x-3">
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
                    <div class="flex justify-between items-center">
                        <span>Embedding:</span>
                        <div class="embedding-status" data-document-id="${doc.file}">
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Checking...
                            </span>
                        </div>
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
        });
        
        // Check embedding status for all documents
        checkAllEmbeddingStatuses();
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
    
    // Check embedding status for all visible documents
    async function checkAllEmbeddingStatuses() {
        const statusElements = document.querySelectorAll('.embedding-status');
        
        statusElements.forEach(async (element) => {
            const documentId = element.getAttribute('data-document-id');
            if (documentId) {
                await checkEmbeddingStatus(documentId, element);
            }
        });
    }
    
    // Check embedding status for a single document
    async function checkEmbeddingStatus(documentId, statusElement) {
        try {
            // Add a subtle pulse effect to indicate checking
            if (statusElement.querySelector('span')) {
                statusElement.querySelector('span').style.opacity = '0.7';
            }
            
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            const response = await fetch(`/admin/api/embedding-status/${documentId}/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                updateStatusDisplay(statusElement, 'error', 'Failed to check');
                return;
            }
            
            const data = await response.json();
            
            // Update the status display based on the response
            if (data.status === 'completed') {
                updateStatusDisplay(statusElement, 'completed', 'Embedded');
            } else if (data.status === 'processing') {
                const progressText = data.progress ? `Processing... (${Math.round(data.progress)}%)` : 'Processing...';
                updateStatusDisplay(statusElement, 'processing', progressText);
                // Check again in 2 seconds for more frequent updates
                setTimeout(() => checkEmbeddingStatus(documentId, statusElement), 2000);
            } else if (data.status === 'queued') {
                const queueText = data.queue_position ? `Queued (#${data.queue_position})` : 'Queued';
                updateStatusDisplay(statusElement, 'queued', queueText);
                // Check again in 3 seconds
                setTimeout(() => checkEmbeddingStatus(documentId, statusElement), 3000);
            } else if (data.status === 'failed') {
                const errorText = data.error ? 'Failed' : 'Failed';
                updateStatusDisplay(statusElement, 'error', errorText);
                // Add tooltip with error message if available
                if (data.error && statusElement.querySelector('span')) {
                    statusElement.querySelector('span').title = data.error;
                }
            } else if (data.status === 'duplicate') {
                updateStatusDisplay(statusElement, 'duplicate', 'Duplicate');
                // Add tooltip with error message
                if (data.error && statusElement.querySelector('span')) {
                    statusElement.querySelector('span').title = data.error;
                }
            } else if (data.status === 'error') {
                updateStatusDisplay(statusElement, 'error', 'Error');
            } else {
                updateStatusDisplay(statusElement, 'pending', 'Pending');
                // Check again in 3 seconds
                setTimeout(() => checkEmbeddingStatus(documentId, statusElement), 3000);
            }
            
        } catch (error) {
            console.error('Error checking embedding status:', error);
            updateStatusDisplay(statusElement, 'error', 'Error');
        }
    }
    
    // Update the status display element
    function updateStatusDisplay(element, status, text) {
        const statusColors = {
            'completed': 'bg-green-100 text-green-800',
            'processing': 'bg-blue-100 text-blue-800',
            'queued': 'bg-yellow-100 text-yellow-800',
            'error': 'bg-red-100 text-red-800',
            'duplicate': 'bg-orange-100 text-orange-800',
            'pending': 'bg-gray-100 text-gray-800'
        };
        
        const statusIcons = {
            'completed': '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>',
            'processing': '<svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>',
            'queued': '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path></svg>',
            'error': '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
            'duplicate': '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z"></path><path d="M3 8a2 2 0 012-2v10h8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"></path></svg>',
            'pending': '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"></path></svg>'
        };
        
        const colorClass = statusColors[status] || statusColors['pending'];
        const icon = statusIcons[status] || statusIcons['pending'];
        
        element.innerHTML = `
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass} transition-opacity duration-200" style="opacity: 1">
                ${icon}
                ${text}
            </span>
        `;
    }
});