// JavaScript for the Coding Module

// Function to get CSRF token
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Handle Generate Script form submission with streaming
function handleGenerateScriptFormSubmit(form, promptInput, languageSelect, resultContainer) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get input values
        const prompt = promptInput.value.trim();
        const language = languageSelect.value || 'python';
        
        if (!prompt) {
            showToast('Please enter a prompt for the script', 'error');
            return;
        }
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Generating...';
        
        // Prepare the result container for streaming
        resultContainer.classList.remove('hidden');
        const titleElement = resultContainer.querySelector('.script-title');
        const codeElement = resultContainer.querySelector('.script-code');
        
        titleElement.textContent = prompt.split('\n')[0].trim() || 'Generated Script';
        codeElement.textContent = '';
        codeElement.innerHTML = '<span class="typing-cursor"></span>';
        
        try {
            // Send request with streaming enabled
            const response = await fetch('/api/coding/generate?stream=true', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ prompt, language })
            });
            
            if (response.ok) {
                // Set up the reader for the stream
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let accumulatedContent = '';
                
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
                                
                                if (data.error) {
                                    showToast(`Error: ${data.error}`, 'error');
                                    break;
                                }
                                
                                if (data.chunk) {
                                    // Update the content with the new chunk
                                    accumulatedContent += data.chunk;
                                    codeElement.textContent = accumulatedContent;
                                    codeElement.innerHTML = codeElement.textContent + '<span class="typing-cursor"></span>';
                                    
                                    // Highlight the code
                                    hljs.highlightElement(codeElement);
                                    
                                    // Add the cursor back
                                    codeElement.innerHTML = codeElement.innerHTML + '<span class="typing-cursor"></span>';
                                }
                                
                                if (data.done) {
                                    // Remove the typing cursor when done
                                    codeElement.textContent = accumulatedContent;
                                    hljs.highlightElement(codeElement);
                                    
                                    // Enable copy button
                                    const copyButton = resultContainer.querySelector('.btn-copy');
                                    if (copyButton) {
                                        copyButton.disabled = false;
                                    }
                                    
                                    showToast('Script generated successfully', 'success');
                                    break;
                                }
                            } catch (e) {
                                console.error('Error parsing streaming data:', e);
                            }
                        }
                    }
                }
            } else {
                const result = await response.json();
                showToast(result.message || 'Failed to generate script', 'error');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            // Reset submit button
            submitButton.disabled = false;
            submitButton.innerHTML = 'Generate Script';
        }
    });
}

// Handle Debug Script form submission with streaming
function handleDebugScriptFormSubmit(form, scriptContent, resultContainer) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get input values
        const script_content = scriptContent.value.trim();
        const script_id = scriptContent.dataset.scriptId || '';
        
        if (!script_content) {
            showToast('Please enter script content to debug', 'error');
            return;
        }
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Debugging...';
        
        // Prepare the result container for streaming
        resultContainer.classList.remove('hidden');
        const explanationElement = resultContainer.querySelector('.debug-explanation');
        const codeElement = resultContainer.querySelector('.debug-code');
        const diffElement = resultContainer.querySelector('.debug-diff');
        
        explanationElement.textContent = 'Analyzing script...';
        codeElement.textContent = '';
        codeElement.innerHTML = '<span class="typing-cursor"></span>';
        diffElement.innerHTML = '<div class="p-4 bg-gray-100 rounded">Generating diff...</div>';
        
        try {
            // Send request with streaming enabled
            const response = await fetch('/api/coding/debug?stream=true', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ script_id, script_content })
            });
            
            if (response.ok) {
                // Set up the reader for the stream
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let accumulatedContent = '';
                
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
                                
                                if (data.error) {
                                    showToast(`Error: ${data.error}`, 'error');
                                    break;
                                }
                                
                                if (data.chunk) {
                                    // Update the content with the new chunk
                                    accumulatedContent += data.chunk;
                                    
                                    // Try to extract explanation and code as we go
                                    const { explanation, code } = extractExplanationAndCode(accumulatedContent);
                                    
                                    if (explanation) {
                                        explanationElement.textContent = explanation;
                                    }
                                    
                                    if (code) {
                                        codeElement.textContent = code;
                                        codeElement.innerHTML = codeElement.textContent + '<span class="typing-cursor"></span>';
                                        hljs.highlightElement(codeElement);
                                        codeElement.innerHTML = codeElement.innerHTML + '<span class="typing-cursor"></span>';
                                    }
                                }
                                
                                if (data.done) {
                                    // Final extraction and formatting
                                    const { explanation, code } = extractExplanationAndCode(accumulatedContent);
                                    
                                    explanationElement.textContent = explanation || 'Debug complete.';
                                    
                                    if (code) {
                                        codeElement.textContent = code;
                                        hljs.highlightElement(codeElement);
                                        
                                        // Generate a simple diff for display
                                        const diffHtml = generateSimpleDiff(script_content, code);
                                        diffElement.innerHTML = diffHtml;
                                    }
                                    
                                    // Enable copy button
                                    const copyButton = resultContainer.querySelector('.btn-copy');
                                    if (copyButton) {
                                        copyButton.disabled = false;
                                    }
                                    
                                    showToast('Script debugged successfully', 'success');
                                    break;
                                }
                            } catch (e) {
                                console.error('Error parsing streaming data:', e);
                            }
                        }
                    }
                }
            } else {
                const result = await response.json();
                showToast(result.message || 'Failed to debug script', 'error');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            // Reset submit button
            submitButton.disabled = false;
            submitButton.innerHTML = 'Debug Script';
        }
    });
}

// Handle Modify Script form submission with streaming
function handleModifyScriptFormSubmit(form, scriptContent, modificationRequest, resultContainer) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get input values
        const script_content = scriptContent.value.trim();
        const script_id = scriptContent.dataset.scriptId || '';
        const modification_request = modificationRequest.value.trim();
        
        if (!script_content) {
            showToast('Please enter script content to modify', 'error');
            return;
        }
        
        if (!modification_request) {
            showToast('Please enter modification request', 'error');
            return;
        }
        
        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Modifying...';
        
        // Prepare the result container for streaming
        resultContainer.classList.remove('hidden');
        const explanationElement = resultContainer.querySelector('.modify-explanation');
        const codeElement = resultContainer.querySelector('.modify-code');
        const diffElement = resultContainer.querySelector('.modify-diff');
        
        explanationElement.textContent = 'Processing modification request...';
        codeElement.textContent = '';
        codeElement.innerHTML = '<span class="typing-cursor"></span>';
        diffElement.innerHTML = '<div class="p-4 bg-gray-100 rounded">Generating diff...</div>';
        
        try {
            // Send request with streaming enabled
            const response = await fetch('/api/coding/modify?stream=true', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ script_id, script_content, modification_request })
            });
            
            if (response.ok) {
                // Set up the reader for the stream
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let accumulatedContent = '';
                
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
                                
                                if (data.error) {
                                    showToast(`Error: ${data.error}`, 'error');
                                    break;
                                }
                                
                                if (data.chunk) {
                                    // Update the content with the new chunk
                                    accumulatedContent += data.chunk;
                                    
                                    // Try to extract explanation and code as we go
                                    const { explanation, code } = extractExplanationAndCode(accumulatedContent);
                                    
                                    if (explanation) {
                                        explanationElement.textContent = explanation;
                                    }
                                    
                                    if (code) {
                                        codeElement.textContent = code;
                                        codeElement.innerHTML = codeElement.textContent + '<span class="typing-cursor"></span>';
                                        hljs.highlightElement(codeElement);
                                        codeElement.innerHTML = codeElement.innerHTML + '<span class="typing-cursor"></span>';
                                    }
                                }
                                
                                if (data.done) {
                                    // Final extraction and formatting
                                    const { explanation, code } = extractExplanationAndCode(accumulatedContent);
                                    
                                    explanationElement.textContent = explanation || 'Modification complete.';
                                    
                                    if (code) {
                                        codeElement.textContent = code;
                                        hljs.highlightElement(codeElement);
                                        
                                        // Generate a simple diff for display
                                        const diffHtml = generateSimpleDiff(script_content, code);
                                        diffElement.innerHTML = diffHtml;
                                    }
                                    
                                    // Enable copy button
                                    const copyButton = resultContainer.querySelector('.btn-copy');
                                    if (copyButton) {
                                        copyButton.disabled = false;
                                    }
                                    
                                    showToast('Script modified successfully', 'success');
                                    break;
                                }
                            } catch (e) {
                                console.error('Error parsing streaming data:', e);
                            }
                        }
                    }
                }
            } else {
                const result = await response.json();
                showToast(result.message || 'Failed to modify script', 'error');
            }
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            // Reset submit button
            submitButton.disabled = false;
            submitButton.innerHTML = 'Modify Script';
        }
    });
}

// Helper function to extract explanation and code from streamed content
function extractExplanationAndCode(content) {
    let explanation = '';
    let code = '';
    
    // Check for markdown code blocks
    if (content.includes('```')) {
        const parts = content.split('```');
        if (parts.length >= 3) {
            explanation = parts[0].trim();
            
            // Remove the language identifier if present
            let codeBlock = parts[1];
            if (codeBlock.indexOf('\n') > 0) {
                codeBlock = codeBlock.substring(codeBlock.indexOf('\n') + 1);
            }
            code = codeBlock.trim();
        }
    } else {
        // Try to split on common separators
        const separators = [
            '### CODE ###',
            'Here is the code:',
            'Here\'s the code:',
            'Modified code:',
            'Debugged code:'
        ];
        
        for (const separator of separators) {
            if (content.includes(separator)) {
                const parts = content.split(separator);
                explanation = parts[0].trim();
                code = parts[1].trim();
                break;
            }
        }
        
        // If no clear separator, make a best guess
        if (!code && content.includes('\n')) {
            const lines = content.split('\n');
            let codeStartLine = 0;
            
            // Look for code-like lines
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].trim().startsWith('def ') || 
                    lines[i].trim().startsWith('class ') || 
                    lines[i].trim().startsWith('import ') || 
                    lines[i].trim().startsWith('from ')) {
                    codeStartLine = i;
                    break;
                }
            }
            
            if (codeStartLine > 0) {
                explanation = lines.slice(0, codeStartLine).join('\n').trim();
                code = lines.slice(codeStartLine).join('\n').trim();
            }
        }
    }
    
    return { explanation, code };
}

// Generate a simple diff for display
function generateSimpleDiff(oldCode, newCode) {
    const oldLines = oldCode.split('\n');
    const newLines = newCode.split('\n');
    
    let html = '<div class="diff-container">';
    
    // Simple line-by-line comparison
    const oldSet = new Set(oldLines);
    const newSet = new Set(newLines);
    
    // Find removed and added lines
    const removed = oldLines.filter(line => !newSet.has(line));
    const added = newLines.filter(line => !oldSet.has(line));
    
    // Create HTML diff
    for (const line of oldLines) {
        if (removed.includes(line)) {
            html += `<div class="diff-line-removed">${escapeHtml(line)}</div>`;
        }
    }
    
    for (const line of newLines) {
        if (added.includes(line)) {
            html += `<div class="diff-line-added">${escapeHtml(line)}</div>`;
        }
    }
    
    html += '</div>';
    return html;
}

// Escape HTML special characters for safe display
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// CSS for typing cursor
document.head.insertAdjacentHTML('beforeend', `
<style>
.typing-cursor {
    display: inline-block;
    width: 5px;
    height: 15px;
    background-color: #000;
    animation: blink 1s infinite;
    margin-left: 2px;
    vertical-align: middle;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
}

.diff-container {
    font-family: monospace;
    white-space: pre;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.diff-line-added {
    background-color: #e6ffe6;
    color: #006600;
}

.diff-line-removed {
    background-color: #ffe6e6;
    color: #cc0000;
    text-decoration: line-through;
}
</style>
`);

// Initialize form handlers when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Generate Script Form
    const generateScriptForm = document.getElementById('generate-script-form');
    if (generateScriptForm) {
        const promptInput = document.getElementById('script-prompt');
        const languageSelect = document.getElementById('script-language');
        const resultContainer = document.getElementById('generate-script-result');
        handleGenerateScriptFormSubmit(generateScriptForm, promptInput, languageSelect, resultContainer);
    }
    
    // Debug Script Form
    const debugScriptForm = document.getElementById('debug-script-form');
    if (debugScriptForm) {
        const scriptContent = document.getElementById('debug-script-content');
        const resultContainer = document.getElementById('debug-script-result');
        handleDebugScriptFormSubmit(debugScriptForm, scriptContent, resultContainer);
    }
    
    // Modify Script Form
    const modifyScriptForm = document.getElementById('modify-script-form');
    if (modifyScriptForm) {
        const scriptContent = document.getElementById('modify-script-content');
        const modificationRequest = document.getElementById('modification-request');
        const resultContainer = document.getElementById('modify-script-result');
        handleModifyScriptFormSubmit(modifyScriptForm, scriptContent, modificationRequest, resultContainer);
    }
    
    // Initialize copy buttons
    initializeCopyButtons();
});

// Initialize copy buttons
function initializeCopyButtons() {
    document.querySelectorAll('.btn-copy').forEach(button => {
        button.addEventListener('click', function() {
            const codeElement = this.closest('.result-container').querySelector('pre code');
            if (codeElement) {
                const code = codeElement.textContent;
                navigator.clipboard.writeText(code).then(() => {
                    showToast('Code copied to clipboard!', 'success');
                });
            }
        });
    });
}
