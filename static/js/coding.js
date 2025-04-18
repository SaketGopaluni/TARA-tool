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

                // --- Populate Debug and Modify Forms --- 
                const debugScriptContentInput = document.getElementById('debug-content'); 
                const modifyScriptContentInput = document.getElementById('modify-content'); 
                const debugScriptIdInput = document.getElementById('debug-script-id');
                const modifyScriptIdInput = document.getElementById('modify-script-id');
                
                if (debugScriptContentInput) {
                    debugScriptContentInput.value = scriptData.content;
                    debugScriptContentInput.dataset.scriptId = scriptData.id;
                    console.log(`[Generate Success] Set dataset.scriptId = ${scriptData.id} on debug input:`, debugScriptContentInput.dataset);
                }
                
                if (modifyScriptContentInput) {
                    modifyScriptContentInput.value = scriptData.content;
                    modifyScriptContentInput.dataset.scriptId = scriptData.id;
                    console.log(`[Generate Success] Set dataset.scriptId = ${scriptData.id} on modify input:`, modifyScriptContentInput.dataset);
                }

                // Update the hidden input fields with script ID
                if (debugScriptIdInput) {
                    debugScriptIdInput.value = scriptData.id;
                    console.log(`[Generate Success] Set hidden input script ID = ${scriptData.id} for debug form`);
                }
                
                if (modifyScriptIdInput) {
                    modifyScriptIdInput.value = scriptData.id;
                    console.log(`[Generate Success] Set hidden input script ID = ${scriptData.id} for modify form`);
                }
                // --- End Population ---

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
        
        if (!scriptContentInput) {
            console.error('Could not find element with ID "debug-content"');
            showToast('Internal Error: Debug form elements missing. Cannot find content area.', 'error');
            return;
        }
        if (!errorLogInput) {
            console.error('Could not find element with ID "error-log"');
            showToast('Internal Error: Debug form elements missing. Cannot find error log area.', 'error');
            return;
        }

        const scriptContent = scriptContentInput.value.trim();            
        const errorLog = errorLogInput.value.trim();                      
        
        // Get script ID - first try dataset, then fallback to hidden input
        let scriptId = scriptContentInput.dataset.scriptId;
        console.log('Retrieved scriptId from dataset:', scriptId);
        
        // If dataset scriptId is missing, try the hidden input
        if (!scriptId) {
            const hiddenInput = document.getElementById('debug-script-id');
            if (hiddenInput) {
                scriptId = hiddenInput.value;
            }
        }

        if (!scriptId) {
            console.error('Script ID is missing from both dataset and hidden input!');
            showToast('Error: Could not find Script ID. Please generate the script again.', 'error');
            return;
        }
        
        if (!scriptContent) {
            showToast('Please enter the script content to debug', 'error');
            return;
        }
        
        const submitButton = this.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Debugging...';
        
        resultContainer.classList.remove('hidden');
        const explanationElement = document.getElementById('debug-explanation');
        const diffElement = document.getElementById('debug-diff');
        const codeElement = document.getElementById('debug-code');

        try {
            const requestData = { 
                script_id: scriptId, 
                script_content: scriptContent, 
                error_log: errorLog 
            };
            console.log('Sending requestData to /api/coding/debug:', requestData); 

            const response = await fetch('/api/coding/debug', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() 
                },
                body: JSON.stringify(requestData)
            });
            
            const result = await response.json(); 
            console.log('Debug API response:', result);

            if (response.ok && result.success) {
                // Display the explanation
                explanationElement.textContent = result.explanation || result.analysis || 'No explanation provided';
                
                // Display the diff
                diffElement.innerHTML = result.diff_html || '';
                
                // Display the fixed code with fallbacks
                if (codeElement) {
                    // Try multiple possible field names for the fixed code with fallback to original
                    const fixedCode = result.fixed_code || result.fixed_script || scriptContent;
                    codeElement.textContent = fixedCode;
                    console.log('Setting debug code output:', fixedCode.substring(0, 100) + '...');
                    
                    // Apply syntax highlighting
                    hljs.highlightElement(codeElement);
                } else {
                    console.error('Could not find element with ID "debug-code"');
                }
                
                showToast('Debugging complete!', 'success');
            } else {
                const errorMessage = result.error || 'Failed to debug script. Unknown error.';
                explanationElement.textContent = 'Error';
                diffElement.innerHTML = '';
                codeElement.textContent = errorMessage;
                showToast(errorMessage, 'error');
            }
            
        } catch (error) {
            console.error('Error debugging script:', error);
            explanationElement.textContent = 'Error';
            diffElement.innerHTML = '';
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
        
        if (!scriptContentInput) {
            console.error('Could not find element with ID "modify-content"');
            showToast('Internal Error: Modify form elements missing. Cannot find content area.', 'error');
            return;
        }
        if (!modificationRequestInput) {
            console.error('Could not find element with ID "modification-request"');
            showToast('Internal Error: Modify form elements missing. Cannot find modification request area.', 'error');
            return;
        }

        const scriptContent = scriptContentInput.value.trim();            
        const modificationRequest = modificationRequestInput.value.trim();                      
        
        // Get script ID - first try dataset, then fallback to hidden input
        let scriptId = scriptContentInput.dataset.scriptId;
        console.log('Retrieved scriptId from dataset:', scriptId);
        
        // If dataset scriptId is missing, try the hidden input
        if (!scriptId) {
            const hiddenInput = document.getElementById('modify-script-id');
            if (hiddenInput) {
                scriptId = hiddenInput.value;
            }
        }

        if (!scriptId) {
            console.error('Script ID is missing from both dataset and hidden input!');
            showToast('Error: Could not find Script ID. Please generate the script again.', 'error');
            return;
        }
        
        if (!scriptContent) {
            showToast('Please enter the script content to modify', 'error');
            return;
        }
        
        if (!modificationRequest) {
            showToast('Please enter the modification request', 'error');
            return;
        }
        
        const submitButton = this.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Modifying...';
        
        resultContainer.classList.remove('hidden');
        const explanationElement = document.getElementById('modify-explanation');
        const diffElement = document.getElementById('modify-diff');
        const codeElement = document.getElementById('modify-code');

        try {
            const requestData = { 
                script_id: scriptId, 
                script_content: scriptContent, 
                modification_request: modificationRequest 
            };
            console.log('Sending requestData to /api/coding/modify:', requestData); 

            const response = await fetch('/api/coding/modify', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() 
                },
                body: JSON.stringify(requestData)
            });
            
            const result = await response.json(); 
            console.log('Modify API response:', result);

            if (response.ok && result.success) {
                // Display the explanation
                explanationElement.textContent = result.explanation || 'Script modification completed successfully';
                
                // Display the diff
                diffElement.innerHTML = result.diff_html || '';
                
                // Display the modified code with fallbacks
                if (codeElement) {
                    // Try multiple possible field names for the modified code with fallback to original
                    const modifiedCode = result.modified_code || result.modified_script || scriptContent;
                    codeElement.textContent = modifiedCode;
                    console.log('Setting modified code output:', modifiedCode.substring(0, 100) + '...');
                    
                    // Apply syntax highlighting
                    hljs.highlightElement(codeElement);
                } else {
                    console.error('Could not find element with ID "modify-code"');
                }
                
                showToast('Modification complete!', 'success');
            } else {
                const errorMessage = result.error || 'Failed to modify script. Unknown error.';
                explanationElement.textContent = 'Error';
                diffElement.innerHTML = '';
                codeElement.textContent = errorMessage;
                showToast(errorMessage, 'error');
            }
            
        } catch (error) {
            console.error('Error modifying script:', error);
            explanationElement.textContent = 'Error';
            diffElement.innerHTML = '';
            codeElement.textContent = `An error occurred: ${error.message}`;
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
    
    const debugScriptForm = document.getElementById('debug-form');
    if (debugScriptForm) {
        const scriptContentInput = document.getElementById('debug-content'); 
        const errorLogInput = document.getElementById('error-log'); 
        const resultContainer = document.getElementById('debug-result');
        handleDebugScriptFormSubmit(debugScriptForm, scriptContentInput, errorLogInput, resultContainer);
    }
    
    const modifyScriptForm = document.getElementById('modify-form');
    if (modifyScriptForm) {
        const scriptContentInput = document.getElementById('modify-content'); 
        const modificationRequestInput = document.getElementById('modification-request'); 
        const resultContainer = document.getElementById('modify-result');
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
