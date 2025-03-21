// Common functionality for all pages

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.querySelector('.mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Initialize syntax highlighting
    if (typeof hljs !== 'undefined') {
        document.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
});

// Utility functions for API calls
async function apiRequest(url, method, data) {
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    };

    const options = {
        method: method,
        headers: headers,
        credentials: 'same-origin'
    };

    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        const jsonResponse = await response.json();
        
        if (!response.ok) {
            throw new Error(jsonResponse.message || 'API request failed');
        }
        
        return jsonResponse;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Helper functions
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 p-4 rounded-md shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' : 
        type === 'error' ? 'bg-red-500' : 
        'bg-blue-500'
    } text-white`;
    toast.innerHTML = `
        <div class="flex items-center">
            <span class="mr-2">
                ${type === 'success' ? '<i class="fas fa-check-circle"></i>' : 
                  type === 'error' ? '<i class="fas fa-exclamation-circle"></i>' : 
                  '<i class="fas fa-info-circle"></i>'}
            </span>
            <span>${message}</span>
        </div>
    `;
    
    // Add to DOM
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.5s ease';
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 500);
    }, 3000);
}

// Copy text to clipboard
function copyToClipboard(text) {
    // Create a temporary textarea element
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = 0;
    
    document.body.appendChild(textarea);
    textarea.select();
    
    try {
        // Copy the text
        const successful = document.execCommand('copy');
        
        if (successful) {
            showToast('Copied to clipboard', 'success');
        } else {
            showToast('Failed to copy to clipboard', 'error');
        }
    } catch (err) {
        console.error('Unable to copy to clipboard', err);
        showToast('Failed to copy to clipboard', 'error');
    }
    
    document.body.removeChild(textarea);
}

// Function to format code for display
function formatCodeForDisplay(code, language = 'python') {
    // Remove leading/trailing whitespace
    code = code.trim();
    
    // Escape HTML entities
    code = code.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&#039;');
    
    return code;
}

// Convert markdown to HTML
function markdownToHtml(markdown) {
    if (!markdown) return '';
    
    // Convert headers
    markdown = markdown.replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
    markdown = markdown.replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>');
    markdown = markdown.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-6 mb-4">$1</h1>');
    
    // Convert bold and italic
    markdown = markdown.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    markdown = markdown.replace(/\*(.*?)\*/gim, '<em>$1</em>');
    
    // Convert lists
    markdown = markdown.replace(/^\s*- (.*$)/gim, '<li class="ml-4">$1</li>');
    markdown = markdown.replace(/^\s*\d+\. (.*$)/gim, '<li class="ml-4 list-decimal">$1</li>');
    
    // Wrap lists in <ul> or <ol>
    let inList = false;
    let lines = markdown.split('\n');
    for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes('<li') && !inList) {
            lines[i] = '<ul class="list-disc pl-5 my-3">' + lines[i];
            inList = true;
        } else if (!lines[i].includes('<li') && inList) {
            lines[i - 1] += '</ul>';
            inList = false;
        }
    }
    if (inList) {
        lines[lines.length - 1] += '</ul>';
    }
    markdown = lines.join('\n');
    
    // Convert links
    markdown = markdown.replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2" class="text-blue-600 hover:underline" target="_blank">$1</a>');
    
    // Convert paragraphs (need to be careful not to interfere with other HTML)
    const htmlElements = ['<h1', '<h2', '<h3', '<ul', '<li', '<p', '<a', '<strong', '<em'];
    lines = markdown.split('\n');
    for (let i = 0; i < lines.length; i++) {
        let shouldWrap = true;
        for (const element of htmlElements) {
            if (lines[i].trim().startsWith(element)) {
                shouldWrap = false;
                break;
            }
        }
        if (lines[i].trim() === '') {
            shouldWrap = false;
        }
        
        if (shouldWrap) {
            lines[i] = '<p class="my-2">' + lines[i] + '</p>';
        }
    }
    
    return lines.join('\n');
}

// Function to handle tab switching
function setupTabs(tabButtonSelector, tabPaneSelector) {
    const tabButtons = document.querySelectorAll(tabButtonSelector);
    const tabPanes = document.querySelectorAll(tabPaneSelector);
    
    if (!tabButtons.length || !tabPanes.length) return;
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the target tab ID
            const tabId = this.id.replace('tab-', 'content-');
            
            // Deactivate all tabs
            tabButtons.forEach(btn => {
                btn.classList.remove('border-indigo-500', 'text-indigo-600', 'border-green-500', 'text-green-600', 'border-purple-500', 'text-purple-600');
                btn.classList.add('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
            });
            
            tabPanes.forEach(pane => {
                pane.classList.add('hidden');
                pane.classList.remove('active');
            });
            
            // Activate the selected tab
            this.classList.remove('border-transparent', 'text-gray-500', 'hover:text-gray-700', 'hover:border-gray-300');
            
            // Apply appropriate colors based on the module
            if (this.id.includes('coding')) {
                this.classList.add('border-indigo-500', 'text-indigo-600');
            } else if (this.id.includes('test')) {
                this.classList.add('border-green-500', 'text-green-600');
            } else if (this.id.includes('chat')) {
                this.classList.add('border-purple-500', 'text-purple-600');
            }
            
            // Show the selected tab content
            const tabContent = document.getElementById(tabId);
            if (tabContent) {
                tabContent.classList.remove('hidden');
                tabContent.classList.add('active');
            }
        });
    });
}