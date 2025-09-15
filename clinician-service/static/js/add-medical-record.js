// Add Medical Record functionality
document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-upload');
    const fileDisplay = document.getElementById('selected-file');
    const titleInput = document.getElementById('title');
    let selectedFile = null;

    // Handle file selection
    function handleFile(file) {
        // Validate file type
        const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/jpg', 'image/png'];
        const fileType = file.type;
        const fileExtension = file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileType) && !['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'].includes(fileExtension)) {
            alert('Please upload a valid file type (PDF, DOC, DOCX, JPG, PNG)');
            return;
        }
        
        // Validate file size (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size must be less than 10MB');
            return;
        }
        
        // Store the file
        selectedFile = file;
        
        // Update UI
        fileDisplay.textContent = `Selected: ${file.name}`;
        fileDisplay.classList.remove('hidden');
        
        // Populate title with file name (without extension)
        const fileName = file.name;
        const nameWithoutExtension = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
        titleInput.value = nameWithoutExtension;
        
        // Update file input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
    }

    // File input change event
    fileInput.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('border-blue-500', 'bg-blue-50');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-blue-500', 'bg-blue-50');
    }

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        // Only handle the first file
        if (files.length > 0) {
            if (files.length > 1) {
                alert('Please upload only one file at a time');
            }
            handleFile(files[0]);
        }
    }
});