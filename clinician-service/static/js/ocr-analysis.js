// OCR Analysis JavaScript Module
// Handles AI Analysis button functionality and WebSocket connection to OCR service

// AI Analysis function - connects to OCR service
async function analyzeMedicalRecord(fileId, fileName) {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    
    try {
        // Submit file for AI analysis
        const response = await fetch(`/api/files/medical-records/${fileId}/analyze/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            alert(`Failed to start AI analysis: ${error.error || 'Unknown error'}`);
            return;
        }
        
        const data = await response.json();
        const jobId = data.job_id;
        const websocketUrl = data.websocket_url;
        
        // Show modal with WebSocket connection
        showAIAnalysisModal(fileName, fileId, jobId, websocketUrl);
        
    } catch (error) {
        console.error('Error starting AI analysis:', error);
        alert('Failed to start AI analysis');
    }
}

// Create a more sophisticated modal for AI analysis results
function showAIAnalysisModal(fileName, fileId, jobId, websocketUrl) {
    // Create modal HTML with loading state initially
    const modalHTML = `
        <div id="ai-modal-${fileId}" class="fixed z-50 inset-0 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
            <div class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:p-0">
                <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>
                <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                <div class="inline-block align-middle bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all my-8 sm:max-w-3xl sm:w-full">
                    <div class="bg-white">
                        <!-- Header -->
                        <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
                            <div class="flex items-start justify-between">
                                <div class="flex items-center">
                                    <div class="flex-shrink-0">
                                        <svg class="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                                        </svg>
                                    </div>
                                    <div class="ml-3">
                                        <h3 class="text-lg leading-6 font-medium text-gray-900">
                                            AI Medical Record Analysis
                                        </h3>
                                        <p class="text-sm text-gray-500">${fileName}</p>
                                    </div>
                                </div>
                                <button onclick="closeAIModal('${fileId}')" class="bg-gray-50 rounded-md text-gray-400 hover:text-gray-500 focus:outline-none">
                                    <span class="sr-only">Close</span>
                                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        
                        <!-- Content -->
                        <div class="px-6 py-4">
                            <!-- Loading State -->
                            <div id="ai-loading-${fileId}" class="py-8">
                                <div class="flex flex-col items-center">
                                    <div class="relative">
                                        <svg class="animate-spin h-12 w-12 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    </div>
                                    <p class="mt-4 text-sm text-gray-600">Initializing OCR processing...</p>
                                    <div class="mt-4 w-full max-w-xs">
                                        <div class="bg-gray-200 rounded-full h-2">
                                            <div id="progress-bar-${fileId}" class="bg-blue-600 h-2 rounded-full transition-all duration-500" style="width: 0%"></div>
                                        </div>
                                        <p id="progress-text-${fileId}" class="text-xs text-gray-500 text-center mt-2">0% Complete</p>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Results (hidden initially) -->
                            <div id="ai-results-${fileId}" class="space-y-4 hidden">
                                <!-- OCR Results Section -->
                                <div class="border border-gray-200 rounded-lg p-4">
                                    <h4 class="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                                        <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                        </svg>
                                        Text Extraction Results
                                    </h4>
                                    <div class="space-y-2">
                                        <div class="flex justify-between text-sm">
                                            <span class="text-gray-600">Page Count:</span>
                                            <span id="page-count-${fileId}" class="font-medium text-gray-900">-</span>
                                        </div>
                                        <div class="flex justify-between text-sm">
                                            <span class="text-gray-600">Confidence Score:</span>
                                            <span id="confidence-${fileId}" class="font-medium text-gray-900">-</span>
                                        </div>
                                        <div class="flex justify-between text-sm">
                                            <span class="text-gray-600">Processing Time:</span>
                                            <span id="process-time-${fileId}" class="font-medium text-gray-900">-</span>
                                        </div>
                                        <div class="mt-3">
                                            <p class="text-xs text-gray-500 mb-1">Extracted Text Preview:</p>
                                            <div id="text-preview-${fileId}" class="bg-gray-50 rounded p-3 text-xs text-gray-700 max-h-32 overflow-y-auto font-mono">
                                                Processing...
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Medical Analysis Section (Future) -->
                                <div class="border border-gray-200 rounded-lg p-4">
                                    <h4 class="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                                        <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
                                        </svg>
                                        Medical Information Analysis
                                    </h4>
                                    <div class="bg-gray-50 rounded p-3">
                                        <p class="text-sm text-gray-600">Advanced medical analysis features coming soon:</p>
                                        <ul class="mt-2 text-xs text-gray-500 space-y-1">
                                            <li>• Diagnosis extraction</li>
                                            <li>• Medication identification</li>
                                            <li>• Lab result interpretation</li>
                                            <li>• Clinical note summarization</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Error State (hidden initially) -->
                            <div id="ai-error-${fileId}" class="hidden">
                                <div class="bg-red-50 border border-red-200 rounded-lg p-4">
                                    <div class="flex">
                                        <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                        <div class="ml-3">
                                            <h3 class="text-sm font-medium text-red-800">Processing Error</h3>
                                            <p id="error-message-${fileId}" class="mt-1 text-sm text-red-700">An error occurred during analysis.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div class="px-6 py-3 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
                            <button onclick="closeAIModal('${fileId}')" class="inline-flex justify-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                                Close
                            </button>
                            <button id="download-results-${fileId}" disabled class="inline-flex justify-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md opacity-50 cursor-not-allowed">
                                Download Results
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer);
    
    // Connect to OCR WebSocket for real-time updates
    connectToOCRWebSocket(fileId, jobId, websocketUrl);
}

// Connect to OCR WebSocket for real-time updates
function connectToOCRWebSocket(fileId, jobId, websocketUrl) {
    const token = localStorage.getItem('access_token') || getCookie('access_token');
    const progressBar = document.getElementById(`progress-bar-${fileId}`);
    const progressText = document.getElementById(`progress-text-${fileId}`);
    const loadingSection = document.getElementById(`ai-loading-${fileId}`);
    const resultsSection = document.getElementById(`ai-results-${fileId}`);
    const errorSection = document.getElementById(`ai-error-${fileId}`);
    
    // Construct WebSocket URL (use ws:// for local, wss:// for production)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//localhost:8008${websocketUrl}`;
    
    console.log('Connecting to OCR WebSocket:', wsUrl);
    
    const socket = new WebSocket(wsUrl);
    let authenticated = false;
    
    socket.onopen = function(e) {
        console.log('WebSocket connected');
        // Send authentication immediately after connection
        socket.send(JSON.stringify({
            type: 'authenticate',
            token: token
        }));
    };
    
    socket.onmessage = async function(event) {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        switch(data.type) {
            case 'auth_required':
                // Authentication requested
                if (!authenticated) {
                    socket.send(JSON.stringify({
                        type: 'authenticate',
                        token: token
                    }));
                }
                break;
                
            case 'auth_success':
                authenticated = true;
                console.log('WebSocket authenticated');
                progressText.textContent = 'Starting OCR processing...';
                break;
                
            case 'auth_failed':
                console.error('WebSocket authentication failed:', data.message);
                showError('Authentication failed');
                socket.close();
                break;
                
            case 'progress_update':
                // Update progress bar
                const progress = data.progress || 0;
                progressBar.style.width = progress + '%';
                progressText.textContent = data.message || `${progress}% Complete`;
                break;
                
            case 'job_complete':
                console.log('OCR job completed');
                progressBar.style.width = '100%';
                progressText.textContent = '100% Complete';
                
                // Fetch full results from API
                await fetchAndDisplayResults(jobId, fileId);
                socket.close();
                break;
                
            case 'job_error':
                console.error('OCR job error:', data);
                showError(data.message || 'OCR processing failed');
                socket.close();
                break;
                
            case 'status_update':
                console.log('Status update:', data);
                if (data.status === 'completed') {
                    await fetchAndDisplayResults(jobId, fileId);
                    socket.close();
                }
                break;
        }
    };
    
    socket.onerror = function(error) {
        console.error('WebSocket error:', error);
        showError('Connection error occurred');
    };
    
    socket.onclose = function(event) {
        console.log('WebSocket closed:', event);
        if (!authenticated && !event.wasClean) {
            showError('Failed to connect to OCR service');
        }
    };
    
    function showError(message) {
        loadingSection.classList.add('hidden');
        errorSection.classList.remove('hidden');
        document.getElementById(`error-message-${fileId}`).textContent = message;
    }
    
    async function fetchAndDisplayResults(jobId, fileId) {
        try {
            // Fetch complete results from clinician service endpoint
            const response = await fetch(`/api/clinician/ocr/job/${jobId}/result/`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch results');
            }
            
            const result = await response.json();
            
            // Hide loading, show results
            loadingSection.classList.add('hidden');
            resultsSection.classList.remove('hidden');
            
            // Populate results
            document.getElementById(`page-count-${fileId}`).textContent = `${result.page_count || 0} pages`;
            document.getElementById(`confidence-${fileId}`).textContent = `${(result.confidence_score || 0).toFixed(1)}%`;
            document.getElementById(`process-time-${fileId}`).textContent = `${(result.processing_time || 0).toFixed(1)} seconds`;
            
            // Show text preview (first 500 chars)
            const extractedText = result.extracted_text || 'No text extracted';
            const preview = extractedText.length > 500 ? 
                extractedText.substring(0, 500) + '...' : 
                extractedText;
            document.getElementById(`text-preview-${fileId}`).textContent = preview;
            
            // Enable download button
            const downloadBtn = document.getElementById(`download-results-${fileId}`);
            downloadBtn.disabled = false;
            downloadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            downloadBtn.classList.add('hover:bg-blue-700');
            
            // Set download action
            downloadBtn.onclick = function() {
                downloadOCRResults(jobId, result);
            };
            
        } catch (error) {
            console.error('Failed to fetch OCR results:', error);
            showError('Failed to retrieve OCR results');
        }
    }
}

function downloadOCRResults(jobId, result) {
    // Create a blob with the extracted text
    const content = `OCR Analysis Results
========================================
Job ID: ${jobId}
File: ${result.file_name || 'Unknown'}
Confidence Score: ${(result.confidence_score || 0).toFixed(1)}
Page Count: ${result.page_count || 0}
Processing Time: ${(result.processing_time || 0).toFixed(1)} seconds
Model Used: ${result.model_used || 'Unknown'}
GPU Used: ${result.gpu_used ? 'Yes' : 'No'}
========================================

EXTRACTED TEXT:
========================================
${result.extracted_text || 'No text extracted'}
`;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ocr_results_${jobId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function closeAIModal(fileId) {
    const modal = document.getElementById(`ai-modal-${fileId}`);
    if (modal && modal.parentElement) {
        modal.parentElement.remove();
    }
}

// Utility function to get cookie value
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
