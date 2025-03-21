// JavaScript for the Coding Module

document.addEventListener('DOMContentLoaded', function() {
    // Set up tab switching
    setupTabs('.tab-button', '.tab-pane');
    
    // Initialize variables
    let scripts = [];
    
    // Elements for Generate Script
    const generateForm = document.getElementById('generate-form');
    const generateResult = document.getElementById('generate-result');
    const generateCode = document.getElementById('generate-code');
    const generateTitle = document.getElementById('generate-title');
    const copyGenerateButton = document.getElementById('copy-generate-result');
    
    // Elements for Debug Script
    const debugForm = document.getElementById('debug-form');
    const debugSelectScript = document.getElementById('debug-select-script');
    const debugContent = document.getElementById('debug-content');
    const debugScriptId = document.getElementById('debug-script-id');
    const debugResult = document.getElementById('debug-result');
    const debugCode = document.getElementById('debug-code');
    const debugExplanation = document.getElementById('debug-explanation');
    const debugDiff = document.getElementById('debug-diff');
    const copyDebugButton = document.getElementById('copy-debug-result');
    
    // Elements for Modify Script
    const modifyForm = document.getElementById('modify-form');
    const modifySelectScript = document.getElementById('modify-select-script');
    const modifyContent = document.getElementById('modify-content');
    const modifyScriptId = document.getElementById('modify-script-id');
    const modifyResult = document.getElementById('modify-result');
    const modifyCode = document.getElementById('modify-code');
    const modifyExplanation = document.getElementById('modify-explanation');
    const modifyDiff = document.getElementById('modify-diff');
    const copyModifyButton = document.getElementById('copy-modify-result');
    
    // Elements for Compare Versions
    const compareForm = document.getElementById('compare-form');
    const compareSelectScript = document.getElementById('compare-select-script');
    const compareVersion1 = document.getElementById('compare-version1');
    const compareVersion2 = document.getElementById('compare-version2');
    const compareResult = document.getElementById('compare-result');
    const compareExplanation = document.getElementById('compare-explanation');
    const compareDiff = document.getElementById('compare-diff');
    
    // Load scripts
    loadScripts();
    
    // Generate Script Form Submit
    if (generateForm) {
        generateForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            generateForm.querySelector('button[type="submit"]').disabled = true;
            generateForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Generating...';
            
            // Get form data
            const prompt = document.getElementById('prompt').value;
            const language = document.getElementById('language').value;
            
            try {
                const result = await apiRequest('/api/coding/generate', 'POST', { prompt, language });
                
                if (result.success) {
                    // Update the UI with the generated script
                    generateTitle.textContent = result.script.title;
                    generateCode.textContent = result.script.content;
                    generateCode.className = `language-${language}`;
                    
                    // Highlight the code
                    hljs.highlightElement(generateCode);
                    
                    // Show the result
                    generateResult.classList.remove('hidden');
                    
                    // Refresh the script list
                    loadScripts();
                    
                    // Scroll to the result
                    generateResult.scrollIntoView({ behavior: 'smooth' });
                    
                    showToast('Script generated successfully!', 'success');
                } else {
                    showToast(result.message || 'Failed to generate script', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                generateForm.querySelector('button[type="submit"]').disabled = false;
                generateForm.querySelector('button[type="submit"]').innerHTML = 'Generate Script';
            }
        });
    }
    
    // Debug Script Form Submit
    if (debugForm) {
        debugForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            debugForm.querySelector('button[type="submit"]').disabled = true;
            debugForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Debugging...';
            
            // Get form data
            const script_id = debugScriptId.value;
            const script_content = debugContent.value;
            
            try {
                const result = await apiRequest('/api/coding/debug', 'POST', { script_id, script_content });
                
                if (result.success) {
                    // Update the UI with the debugged script
                    debugCode.textContent = result.script.content;
                    debugExplanation.innerHTML = markdownToHtml(result.explanation);
                    debugDiff.innerHTML = result.diff_html;
                    
                    // Highlight the code
                    hljs.highlightElement(debugCode);
                    
                    // Show the result
                    debugResult.classList.remove('hidden');
                    
                    // Update the script ID if it's changed
                    debugScriptId.value = result.script.id;
                    
                    // Refresh the script list
                    loadScripts();
                    
                    // Scroll to the result
                    debugResult.scrollIntoView({ behavior: 'smooth' });
                    
                    showToast('Script debugged successfully!', 'success');
                } else {
                    showToast(result.message || 'Failed to debug script', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                debugForm.querySelector('button[type="submit"]').disabled = false;
                debugForm.querySelector('button[type="submit"]').innerHTML = 'Debug Script';
            }
        });
    }
    
    // Modify Script Form Submit
    if (modifyForm) {
        modifyForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            modifyForm.querySelector('button[type="submit"]').disabled = true;
            modifyForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Modifying...';
            
            // Get form data
            const script_id = modifyScriptId.value;
            const script_content = modifyContent.value;
            const modification_request = document.getElementById('modification-request').value;
            
            try {
                const result = await apiRequest('/api/coding/modify', 'POST', { 
                    script_id, 
                    script_content, 
                    modification_request 
                });
                
                if (result.success) {
                    // Update the UI with the modified script
                    modifyCode.textContent = result.script.content;
                    modifyExplanation.innerHTML = markdownToHtml(result.explanation);
                    modifyDiff.innerHTML = result.diff_html;
                    
                    // Highlight the code
                    hljs.highlightElement(modifyCode);
                    
                    // Show the result
                    modifyResult.classList.remove('hidden');
                    
                    // Update the script ID if it's changed
                    modifyScriptId.value = result.script.id;
                    
                    // Refresh the script list
                    loadScripts();
                    
                    // Scroll to the result
                    modifyResult.scrollIntoView({ behavior: 'smooth' });
                    
                    showToast('Script modified successfully!', 'success');
                } else {
                    showToast(result.message || 'Failed to modify script', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                modifyForm.querySelector('button[type="submit"]').disabled = false;
                modifyForm.querySelector('button[type="submit"]').innerHTML = 'Modify Script';
            }
        });
    }
    
    // Compare Versions Form Submit
    if (compareForm) {
        compareForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            compareForm.querySelector('button[type="submit"]').disabled = true;
            compareForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Comparing...';
            
            // Get form data
            const script_id = compareSelectScript.value;
            const version1_id = compareVersion1.value;
            const version2_id = compareVersion2.value;
            
            try {
                const result = await apiRequest('/api/coding/compare-versions', 'POST', { 
                    script_id, 
                    version1_id, 
                    version2_id 
                });
                
                if (result.success) {
                    // Update the UI with the comparison results
                    compareExplanation.innerHTML = markdownToHtml(result.explanation);
                    compareDiff.innerHTML = result.diff_html;
                    
                    // Show the result
                    compareResult.classList.remove('hidden');
                    
                    // Scroll to the result
                    compareResult.scrollIntoView({ behavior: 'smooth' });
                    
                    showToast('Versions compared successfully!', 'success');
                } else {
                    showToast(result.message || 'Failed to compare versions', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                compareForm.querySelector('button[type="submit"]').disabled = false;
                compareForm.querySelector('button[type="submit"]').innerHTML = 'Compare Versions';
            }
        });
    }
    
    // Copy buttons event listeners
    if (copyGenerateButton) {
        copyGenerateButton.addEventListener('click', function() {
            const codeToCopy = generateCode.textContent;
            copyToClipboard(codeToCopy);
        });
    }
    
    if (copyDebugButton) {
        copyDebugButton.addEventListener('click', function() {
            const codeToCopy = debugCode.textContent;
            copyToClipboard(codeToCopy);
        });
    }
    
    if (copyModifyButton) {
        copyModifyButton.addEventListener('click', function() {
            const codeToCopy = modifyCode.textContent;
            copyToClipboard(codeToCopy);
        });
    }
    
    // Script selection change handlers
    if (debugSelectScript) {
        debugSelectScript.addEventListener('change', function() {
            const scriptId = this.value;
            if (scriptId) {
                const script = scripts.find(s => s.id == scriptId);
                if (script) {
                    debugContent.value = script.content;
                    debugScriptId.value = script.id;
                }
            } else {
                debugContent.value = '';
                debugScriptId.value = '';
            }
        });
    }
    
    if (modifySelectScript) {
        modifySelectScript.addEventListener('change', function() {
            const scriptId = this.value;
            if (scriptId) {
                const script = scripts.find(s => s.id == scriptId);
                if (script) {
                    modifyContent.value = script.content;
                    modifyScriptId.value = script.id;
                }
            } else {
                modifyContent.value = '';
                modifyScriptId.value = '';
            }
        });
    }
    
    if (compareSelectScript) {
        compareSelectScript.addEventListener('change', async function() {
            const scriptId = this.value;
            if (scriptId) {
                try {
                    // Fetch versions for the selected script
                    const result = await apiRequest(`/api/coding/versions/${scriptId}`, 'GET');
                    
                    if (result.success && result.versions.length > 0) {
                        // Enable version selection
                        compareVersion1.innerHTML = '<option value="">-- Select a version --</option>';
                        compareVersion2.innerHTML = '<option value="">-- Select a version --</option>';
                        
                        // Add versions to the dropdowns
                        result.versions.forEach(version => {
                            const option1 = document.createElement('option');
                            option1.value = version.id;
                            option1.textContent = `Version ${version.version} (${new Date(version.created_at).toLocaleString()})`;
                            compareVersion1.appendChild(option1);
                            
                            const option2 = document.createElement('option');
                            option2.value = version.id;
                            option2.textContent = `Version ${version.version} (${new Date(version.created_at).toLocaleString()})`;
                            compareVersion2.appendChild(option2);
                        });
                        
                        // Enable version selection
                        compareVersion1.disabled = false;
                        compareVersion2.disabled = false;
                        
                        // Set default selections to oldest and newest
                        if (result.versions.length >= 2) {
                            compareVersion1.value = result.versions[0].id;
                            compareVersion2.value = result.versions[result.versions.length - 1].id;
                        }
                        
                        // Enable compare button
                        compareForm.querySelector('button[type="submit"]').disabled = false;
                    } else {
                        showToast('No versions available for comparison', 'error');
                        compareVersion1.disabled = true;
                        compareVersion2.disabled = true;
                        compareForm.querySelector('button[type="submit"]').disabled = true;
                    }
                } catch (error) {
                    showToast(`Error: ${error.message}`, 'error');
                }
            } else {
                compareVersion1.innerHTML = '<option value="">-- Select a version --</option>';
                compareVersion2.innerHTML = '<option value="">-- Select a version --</option>';
                compareVersion1.disabled = true;
                compareVersion2.disabled = true;
                compareForm.querySelector('button[type="submit"]').disabled = true;
            }
        });
    }
    
    // Function to load scripts
    async function loadScripts() {
        try {
            const result = await apiRequest('/api/coding/scripts', 'GET');
            
            if (result.success) {
                scripts = result.scripts;
                
                // Update script selectors
                updateScriptSelectors();
            } else {
                console.error('Failed to load scripts:', result.message);
            }
        } catch (error) {
            console.error('Error loading scripts:', error);
        }
    }
    
    // Function to update script selectors
    function updateScriptSelectors() {
        // Update Debug Script selector
        if (debugSelectScript) {
            const currentValue = debugSelectScript.value;
            debugSelectScript.innerHTML = '<option value="">-- Select a script --</option>';
            
            scripts.forEach(script => {
                const option = document.createElement('option');
                option.value = script.id;
                option.textContent = script.title;
                debugSelectScript.appendChild(option);
            });
            
            // Restore selected value if it still exists
            if (currentValue && scripts.some(s => s.id == currentValue)) {
                debugSelectScript.value = currentValue;
            }
        }
        
        // Update Modify Script selector
        if (modifySelectScript) {
            const currentValue = modifySelectScript.value;
            modifySelectScript.innerHTML = '<option value="">-- Select a script --</option>';
            
            scripts.forEach(script => {
                const option = document.createElement('option');
                option.value = script.id;
                option.textContent = script.title;
                modifySelectScript.appendChild(option);
            });
            
            // Restore selected value if it still exists
            if (currentValue && scripts.some(s => s.id == currentValue)) {
                modifySelectScript.value = currentValue;
            }
        }
        
        // Update Compare Scripts selector
        if (compareSelectScript) {
            const currentValue = compareSelectScript.value;
            compareSelectScript.innerHTML = '<option value="">-- Select a script --</option>';
            
            scripts.forEach(script => {
                const option = document.createElement('option');
                option.value = script.id;
                option.textContent = script.title;
                compareSelectScript.appendChild(option);
            });
            
            // Restore selected value if it still exists
            if (currentValue && scripts.some(s => s.id == currentValue)) {
                compareSelectScript.value = currentValue;
            }
        }
    }
});