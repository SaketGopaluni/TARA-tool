// JavaScript for the Coding Module

// Function to get CSRF token
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Handle Generate Script form submission
function handleGenerateScriptFormSubmit(form, promptInput, languageSelect, resultContainer) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const prompt = promptInput.value.trim();
        const language = languageSelect.value || 'python';
        
        if (!prompt) {
            showToast('Please enter a prompt for the script', 'error');
            return;
        }
        
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Generating...';
        
        resultContainer.classList.remove('hidden');
        const titleElement = resultContainer.querySelector('.script-title');
        const codeElement = resultContainer.querySelector('.script-code');
        const saveButton = resultContainer.querySelector('.btn-save'); 
        const copyButton = resultContainer.querySelector('.btn-copy');

        titleElement.textContent = 'Generating...';
        codeElement.textContent = 'Please wait...';
        hljs.highlightElement(codeElement); 
        if(saveButton) saveButton.classList.add('hidden');
        if(copyButton) copyButton.disabled = true;
        
        try {
            const requestData = { requirements: prompt, language };
            console.log('Sending to /api/coding/generate:', requestData);
            
            const response = await fetch('/api/coding/generate', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() 
                },
                body: JSON.stringify(requestData)
            });
            
            const result = await response.json(); 

            if (response.ok && result.success) {
                const scriptData = result.script; 
                
                titleElement.textContent = scriptData.title || prompt.split('\n')[0].trim() || 'Generated Script';
                codeElement.textContent = scriptData.content; 
                
                hljs.highlightElement(codeElement);
                
                resultContainer.dataset.scriptId = scriptData.id; 
                if(saveButton) saveButton.classList.remove('hidden'); 
                if(copyButton) copyButton.disabled = false; 

                showToast('Script generated successfully!', 'success');

            } else {
                const errorMessage = result.error || 'Failed to generate script. Unknown error.';
                titleElement.textContent = 'Error';
                codeElement.textContent = errorMessage;
                showToast(errorMessage, 'error');
            }
            
        } catch (error) {
            console.error('Error generating script:', error);
            titleElement.textContent = 'Error';
            codeElement.textContent = `An error occurred: ${error.message}`;
            showToast('An error occurred while generating the script.', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Generate Script';
        }
    });
}

// Handle Debug Script form submission
function handleDebugScriptFormSubmit(form, scriptContentInput, errorLogInput, resultContainer) { 
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const scriptContent = scriptContentInput.value.trim();
        const errorLog = errorLogInput.value.trim(); 
        const scriptId = scriptContentInput.dataset.scriptId; 

        if (!scriptContent) {
            showToast('Please enter the script content to debug', 'error');
            return;
        }
        if (!errorLog) {
            showToast('Please enter the error log or description', 'error');
            return;
        }
        if (!scriptId) {
            console.warn('Script ID not found for debugging. Sending content only.');
        }
        
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Debugging...';
        
        resultContainer.classList.remove('hidden');
        const explanationElement = resultContainer.querySelector('.debug-explanation');
        const codeElement = resultContainer.querySelector('.debug-code'); 
        const saveButton = resultContainer.querySelector('.btn-save-debugged'); 
        const copyButton = resultContainer.querySelector('.btn-copy');

        explanationElement.textContent = 'Debugging in progress...';
        codeElement.textContent = 'Please wait...';
        hljs.highlightElement(codeElement); 
        if(saveButton) saveButton.classList.add('hidden');
        if(copyButton) copyButton.disabled = true;

        try {
            const response = await fetch('/api/coding/debug', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() 
                },
                body: JSON.stringify({ 
                    script_id: scriptId, 
                    script_content: scriptContent, 
                    error_log: errorLog 
                })
            });
            
            const result = await response.json(); 

            if (response.ok && result.success) {
                const debugData = result.debug_result; 
                
                explanationElement.textContent = debugData.explanation || 'No explanation provided.';
                codeElement.textContent = debugData.fixed_code;
                
                hljs.highlightElement(codeElement);
                
                resultContainer.dataset.newVersionId = debugData.id;
                if(saveButton) saveButton.classList.remove('hidden');
                if(copyButton) copyButton.disabled = false;

                showToast('Debugging complete!', 'success');

            } else {
                const errorMessage = result.error || 'Failed to debug script. Unknown error.';
                explanationElement.textContent = 'Error';
                codeElement.textContent = errorMessage;
                showToast(errorMessage, 'error');
            }
            
        } catch (error) {
            console.error('Error debugging script:', error);
            explanationElement.textContent = 'Error';
            codeElement.textContent = `An error occurred: ${error.message}`;
            showToast('An error occurred while debugging the script.', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Debug Script';
        }
    });
}

// Handle Modify Script form submission
function handleModifyScriptFormSubmit(form, scriptContentInput, modificationRequestInput, resultContainer) {
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const scriptContent = scriptContentInput.value.trim();
        const modificationRequest = modificationRequestInput.value.trim();
        const scriptId = scriptContentInput.dataset.scriptId; 

        if (!scriptContent) {
            showToast('Please enter the script content to modify', 'error');
            return;
        }
        if (!modificationRequest) {
            showToast('Please enter the modification request', 'error');
            return;
        }
        if (!scriptId) {
            console.warn('Script ID not found for modification. Sending content only.');
        }
        
        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Modifying...';
        
        resultContainer.classList.remove('hidden');
        const explanationElement = resultContainer.querySelector('.modify-explanation');
        const codeElement = resultContainer.querySelector('.modify-code'); 
        const diffElement = resultContainer.querySelector('.modify-diff'); 
        const saveButton = resultContainer.querySelector('.btn-save-modified'); 
        const copyButton = resultContainer.querySelector('.btn-copy');

        explanationElement.textContent = 'Modification in progress...';
        codeElement.textContent = 'Please wait...';
        diffElement.innerHTML = ''; 
        hljs.highlightElement(codeElement); 
        if(saveButton) saveButton.classList.add('hidden');
        if(copyButton) copyButton.disabled = true;

        try {
            const response = await fetch('/api/coding/modify', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() 
                },
                body: JSON.stringify({ 
                    script_id: scriptId, 
                    script_content: scriptContent,
                    modification_request: modificationRequest 
                })
            });
            
            const result = await response.json(); 

            if (response.ok && result.success) {
                const modifyData = result.modify_result; 
                
                explanationElement.textContent = modifyData.explanation || 'No explanation provided.';
                codeElement.textContent = modifyData.modified_code;
                
                hljs.highlightElement(codeElement);

                const diffHtml = generateSimpleDiff(scriptContent, modifyData.modified_code);
                diffElement.innerHTML = diffHtml;
                
                resultContainer.dataset.newVersionId = modifyData.id;
                if(saveButton) saveButton.classList.remove('hidden');
                if(copyButton) copyButton.disabled = false;

                showToast('Modification complete!', 'success');

            } else {
                const errorMessage = result.error || 'Failed to modify script. Unknown error.';
                explanationElement.textContent = 'Error';
                codeElement.textContent = errorMessage;
                diffElement.innerHTML = ''; 
                showToast(errorMessage, 'error');
            }
            
        } catch (error) {
            console.error('Error modifying script:', error);
            explanationElement.textContent = 'Error';
            codeElement.textContent = `An error occurred: ${error.message}`;
            diffElement.innerHTML = ''; 
            showToast('An error occurred while modifying the script.', 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Modify Script';
        }
    });
}

// Generate a simple diff for display
function generateSimpleDiff(oldCode, newCode) {
    const oldLines = oldCode.split('\n');
    const newLines = newCode.split('\n');
    
    let html = '<div class="diff-container">';
    
    const oldSet = new Set(oldLines);
    const newSet = new Set(newLines);
    
    const removed = oldLines.filter(line => !newSet.has(line));
    const added = newLines.filter(line => !oldSet.has(line));
    
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
    const generateScriptForm = document.getElementById('generate-script-form');
    if (generateScriptForm) {
        const promptInput = document.getElementById('script-prompt');
        const languageSelect = document.getElementById('script-language');
        const resultContainer = document.getElementById('generate-script-result');
        handleGenerateScriptFormSubmit(generateScriptForm, promptInput, languageSelect, resultContainer);
    }
    
    const debugScriptForm = document.getElementById('debug-script-form');
    if (debugScriptForm) {
        const scriptContentInput = document.getElementById('debug-script-content'); 
        const errorLogInput = document.getElementById('debug-error-log'); 
        const resultContainer = document.getElementById('debug-script-result');
        handleDebugScriptFormSubmit(debugScriptForm, scriptContentInput, errorLogInput, resultContainer);
    }
    
    const modifyScriptForm = document.getElementById('modify-script-form');
    if (modifyScriptForm) {
        const scriptContentInput = document.getElementById('modify-script-content'); 
        const modificationRequestInput = document.getElementById('modification-request'); 
        const resultContainer = document.getElementById('modify-script-result');
        handleModifyScriptFormSubmit(modifyScriptForm, scriptContentInput, modificationRequestInput, resultContainer);
    }
    
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
});
