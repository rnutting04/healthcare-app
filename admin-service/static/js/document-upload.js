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

        // Show upload progress modal
        uploadProgressModal.classList.remove('hidden');
        
        // Simulate upload progress (replace with actual upload logic)
        simulateUpload();
    });

    // Simulate upload (replace with actual upload logic)
    function simulateUpload() {
        let progress = 0;
        const interval = setInterval(function() {
            progress += 10;
            updateProgress(progress);
            
            if (progress >= 100) {
                clearInterval(interval);
                setTimeout(function() {
                    uploadProgressModal.classList.add('hidden');
                    showSuccess('Documents uploaded successfully!');
                    
                    // Clear form
                    selectedFiles.clear();
                    fileInput.value = '';
                    updateFilesList();
                    updateSubmitButton();
                    
                    // Update recent uploads (in real implementation, fetch from server)
                    updateRecentUploads();
                }, 500);
            }
        }, 300);
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
        setTimeout(() => alert.remove(), 5000);
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

    // Update recent uploads (placeholder - replace with actual data fetching)
    function updateRecentUploads() {
        const container = document.getElementById('recentUploadsContainer');
        
        // Sample data - replace with actual API call
        const sampleData = [
            {
                name: 'Medical Guidelines 2025.pdf',
                size: '2.5 MB',
                uploadedAt: new Date().toLocaleString()
            }
        ];

        if (sampleData.length > 0) {
            const table = document.createElement('table');
            table.className = 'recent-uploads-table';
            
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Document Name</th>
                        <th>Size</th>
                        <th>Uploaded At</th>
                    </tr>
                </thead>
                <tbody>
                    ${sampleData.map(doc => `
                        <tr>
                            <td class="font-medium">${doc.name}</td>
                            <td>${doc.size}</td>
                            <td>${doc.uploadedAt}</td>
                        </tr>
                    `).join('')}
                </tbody>
            `;
            
            container.innerHTML = '';
            container.appendChild(table);
        }
    }
});