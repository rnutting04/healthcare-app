// RAG Chatbot functionality for patient dashboard
class RAGChatbot {
    constructor() {
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendChatButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.contextBadge = document.getElementById('chatContextBadge');
        this.sessionId = null;  // Track session ID for conversation context
        this.messageHistory = [];  // Keep local history
        
        this.initialize();
    }
    
    initialize() {
        // Load cancer type context
        this.loadChatContext();
        
        // Set up event listeners
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter (but not Shift+Enter)
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
        });
    }
    
    async loadChatContext() {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/patients/rag-chat/context/', {
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                const cancerType = data.cancer_type.charAt(0).toUpperCase() + data.cancer_type.slice(1);
                this.contextBadge.textContent = `${cancerType} Cancer${data.is_fallback ? ' (Default)' : ''}`;
                this.contextBadge.title = data.is_fallback 
                    ? 'Using general uterine cancer information' 
                    : `Using ${cancerType} cancer specific information`;
            }
        } catch (error) {
            console.error('Error loading chat context:', error);
            this.contextBadge.textContent = 'Context unavailable';
        }
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        // Disable input while sending
        this.setInputState(false);
        
        // Add user message to chat
        this.addMessageToChat(message, 'user');
        
        // Clear input
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/patients/rag-chat/query/', {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    query: message,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            
            // Hide typing indicator
            this.hideTypingIndicator();
            
            if (response.ok) {
                // Update session ID if provided
                if (data.session_id) {
                    this.sessionId = data.session_id;
                }
                
                // Add to message history
                this.messageHistory.push({
                    role: 'human',
                    content: message
                });
                this.messageHistory.push({
                    role: 'assistant',
                    content: data.response
                });
                
                // Keep only last 20 messages
                if (this.messageHistory.length > 20) {
                    this.messageHistory = this.messageHistory.slice(-20);
                }
                
                // Add assistant response
                this.addMessageToChat(data.response, 'assistant', data.sources);
            } else {
                // Show error message
                this.addMessageToChat(
                    data.response || 'Sorry, I encountered an error. Please try again.', 
                    'assistant', 
                    null, 
                    true
                );
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessageToChat(
                'Sorry, I could not connect to the service. Please try again later.', 
                'assistant',
                null,
                true
            );
        } finally {
            // Re-enable input
            this.setInputState(true);
            this.chatInput.focus();
        }
    }
    
    addMessageToChat(message, sender, sources = null, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'max-w-xs lg:max-w-md';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = `p-3 rounded-lg shadow ${
            sender === 'user' 
                ? 'bg-blue-600 text-white' 
                : isError 
                    ? 'bg-red-50 border border-red-200'
                    : 'bg-white'
        }`;
        
        // Format message with line breaks
        const messageText = document.createElement('div');
        messageText.className = `text-sm ${
            sender === 'user' 
                ? 'text-white' 
                : isError 
                    ? 'text-red-800' 
                    : 'text-gray-800'
        }`;
        
        // Convert line breaks to <br> tags
        messageText.innerHTML = this.escapeHtml(message).replace(/\n/g, '<br>');
        
        messageBubble.appendChild(messageText);
        
        // Add sources if available
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'mt-2 pt-2 border-t border-gray-200';
            
            const sourcesTitle = document.createElement('p');
            sourcesTitle.className = 'text-xs text-gray-500 font-medium mb-1';
            sourcesTitle.textContent = 'Based on:';
            sourcesDiv.appendChild(sourcesTitle);
            
            sources.forEach(source => {
                const sourceItem = document.createElement('p');
                sourceItem.className = 'text-xs text-gray-600';
                sourceItem.textContent = `• ${source}`;
                sourcesDiv.appendChild(sourceItem);
            });
            
            messageBubble.appendChild(sourcesDiv);
        }
        
        // Add timestamp
        const timestamp = document.createElement('p');
        timestamp.className = `text-xs ${sender === 'user' ? 'text-blue-200' : 'text-gray-400'} mt-1`;
        timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageBubble.appendChild(timestamp);
        
        messageContent.appendChild(messageBubble);
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        
        this.scrollToBottom();
    }
    
    showTypingIndicator() {
        this.typingIndicator.classList.remove('hidden');
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.typingIndicator.classList.add('hidden');
    }
    
    setInputState(enabled) {
        this.chatInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 50);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    async clearChat() {
        // Clear session on server if we have a session ID
        if (this.sessionId) {
            try {
                const token = localStorage.getItem('access_token');
                await fetch('/api/patients/rag-chat/clear_session/', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ session_id: this.sessionId })
                });
            } catch (error) {
                console.error('Error clearing session:', error);
            }
        }
        
        // Reset local state
        this.sessionId = null;
        this.messageHistory = [];
        this.chatMessages.innerHTML = '';
        
        // Add welcome message
        const welcomeMessage = document.createElement('div');
        welcomeMessage.className = 'text-center text-gray-500 my-8';
        welcomeMessage.innerHTML = `
            <p class="text-lg font-medium mb-2">Medical Assistant</p>
            <p class="text-sm">Hello! I'm your medical assistant. I can help answer questions about your condition based on medical documents. How can I help you today?</p>
        `;
        this.chatMessages.appendChild(welcomeMessage);
    }
}

// Initialize chatbot when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.ragChatbot = new RAGChatbot();
    });
} else {
    window.ragChatbot = new RAGChatbot();
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes fade-in {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-fade-in {
        animation: fade-in 0.3s ease-out;
    }
`;
document.head.appendChild(style);