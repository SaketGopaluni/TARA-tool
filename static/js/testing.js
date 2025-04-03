// JavaScript for the Testing Module

document.addEventListener('DOMContentLoaded', function() {
    // Set up tab switching
    setupTabs('.tab-button', '.tab-pane');
    
    // Initialize variables
    let scripts = [];
    let testCases = [];
    
    // Elements for Generate Test Case
    const generateTestForm = document.getElementById('generate-test-form');
    const testSelectScript = document.getElementById('test-select-script');
    const testScriptContent = document.getElementById('test-script-content');
    const testRequirements = document.getElementById('test-requirements');
    const generateTestResult = document.getElementById('generate-test-result');
    const testTitle = document.getElementById('test-title');
    const testCode = document.getElementById('test-code');
    const copyTestResult = document.getElementById('copy-test-result');
    
    // Elements for Execute Test
    const executeTestForm = document.getElementById('execute-test-form');
    const executeSelectScript = document.getElementById('execute-select-script');
    const executeSelectTest = document.getElementById('execute-select-test');
    const executeScriptContent = document.getElementById('execute-script-content');
    const executeTestContent = document.getElementById('execute-test-content');
    const executeTestResult = document.getElementById('execute-test-result');
    const testStatusBadge = document.getElementById('test-status-badge');
    const testExecutionTime = document.getElementById('test-execution-time');
    const testTimestamp = document.getElementById('test-timestamp');
    const testOutput = document.getElementById('test-output');
    
    // Elements for Improve Test Case
    const improveTestForm = document.getElementById('improve-test-form');
    const improveSelectScript = document.getElementById('improve-select-script');
    const improveSelectTest = document.getElementById('improve-select-test');
    const improveScriptContent = document.getElementById('improve-script-content');
    const improveTestContent = document.getElementById('improve-test-content');
    const improveTestResult = document.getElementById('improve-test-result');
    const improvedTestTitle = document.getElementById('improved-test-title');
    const improvedTestCode = document.getElementById('improved-test-code');
    const copyImprovedTest = document.getElementById('copy-improved-test');
    
    // Load scripts and test cases
    loadScripts();
    
    // Generate Test Case Form Submit
    if (generateTestForm) {
        generateTestForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            generateTestForm.querySelector('button[type="submit"]').disabled = true;
            generateTestForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Generating...';
            
            // Get form data
            const script_id = testSelectScript.value;
            const script_content = testScriptContent.value;
            const test_requirements = testRequirements.value;
            
            try {
                // Initialize the code output area with a placeholder for streaming
                testCode.textContent = '';
                testCode.innerHTML = '<span class="typing-cursor"></span>';
                generateTestResult.classList.remove('hidden');
                testTitle.textContent = test_requirements.split('\n')[0].trim() || 'Test Case';
                
                // Send request to API with streaming enabled
                const response = await fetch('/api/testing/generate?stream=true', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ 
                        script_id, 
                        script_content, 
                        test_requirements 
                    })
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
                                        testCode.textContent = accumulatedContent;
                                        testCode.innerHTML = testCode.textContent + '<span class="typing-cursor"></span>';
                                        
                                        // Highlight the code
                                        hljs.highlightElement(testCode);
                                        
                                        // Add the cursor back
                                        testCode.innerHTML = testCode.innerHTML + '<span class="typing-cursor"></span>';
                                    }
                                    
                                    if (data.done) {
                                        // Remove the typing cursor when done
                                        testCode.textContent = accumulatedContent;
                                        hljs.highlightElement(testCode);
                                        
                                        // Refresh the test case list
                                        loadTestCases(script_id);
                                        showToast("Test case generated successfully", 'success');
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
                    showToast(result.message || 'Failed to generate test case', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                generateTestForm.querySelector('button[type="submit"]').disabled = false;
                generateTestForm.querySelector('button[type="submit"]').innerHTML = 'Generate Test Case';
            }
        });
    }
    
    // Execute Test Form Submit
    if (executeTestForm) {
        executeTestForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            executeTestForm.querySelector('button[type="submit"]').disabled = true;
            executeTestForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Executing...';
            
            // Get form data
            const test_case_id = executeSelectTest.value;
            const test_content = executeTestContent.value;
            const script_content = executeScriptContent.value;
            
            try {
                const result = await apiRequest('/api/testing/execute', 'POST', { 
                    test_case_id, 
                    test_content, 
                    script_content 
                });
                
                if (result.success) {
                    // Update the UI with the test results
                    testStatusBadge.textContent = result.test_result.status.toUpperCase();
                    
                    // Set status badge color
                    if (result.test_result.status === 'passed') {
                        testStatusBadge.classList.add('bg-green-100', 'text-green-800');
                        testStatusBadge.classList.remove('bg-red-100', 'text-red-800', 'bg-yellow-100', 'text-yellow-800');
                    } else if (result.test_result.status === 'failed') {
                        testStatusBadge.classList.add('bg-red-100', 'text-red-800');
                        testStatusBadge.classList.remove('bg-green-100', 'text-green-800', 'bg-yellow-100', 'text-yellow-800');
                    } else {
                        testStatusBadge.classList.add('bg-yellow-100', 'text-yellow-800');
                        testStatusBadge.classList.remove('bg-green-100', 'text-green-800', 'bg-red-100', 'text-red-800');
                    }
                    
                    // Set execution time
                    testExecutionTime.textContent = `${result.test_result.execution_time.toFixed(3)} seconds`;
                    
                    // Set timestamp
                    testTimestamp.textContent = new Date(result.test_result.created_at).toLocaleString();
                    
                    // Set output
                    testOutput.textContent = result.test_result.output || 'No output';
                    
                    // Show the result
                    executeTestResult.classList.remove('hidden');
                    
                    // Scroll to the result
                    executeTestResult.scrollIntoView({ behavior: 'smooth' });
                    
                    showToast(`Test executed with status: ${result.test_result.status}`, 
                        result.test_result.status === 'passed' ? 'success' : 
                        result.test_result.status === 'failed' ? 'error' : 'info');
                } else {
                    showToast(result.message || 'Failed to execute test', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                executeTestForm.querySelector('button[type="submit"]').disabled = false;
                executeTestForm.querySelector('button[type="submit"]').innerHTML = 'Execute Test';
            }
        });
    }
    
    // Improve Test Case Form Submit
    if (improveTestForm) {
        improveTestForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            improveTestForm.querySelector('button[type="submit"]').disabled = true;
            improveTestForm.querySelector('button[type="submit"]').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Improving...';
            
            // Get form data
            const test_case_id = improveSelectTest.value;
            const test_content = improveTestContent.value;
            const script_content = improveScriptContent.value;
            const test_result_output = document.getElementById('improve-test-result').value;
            
            try {
                // Initialize the code output area with a placeholder for streaming
                improvedTestCode.textContent = '';
                improvedTestCode.innerHTML = '<span class="typing-cursor"></span>';
                document.getElementById('improved-test-result').classList.remove('hidden');
                improvedTestTitle.textContent = 'Improved Test Case';
                
                // Send request to API with streaming enabled
                const response = await fetch('/api/testing/improve?stream=true', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ 
                        test_case_id, 
                        test_content, 
                        script_content,
                        test_result_output
                    })
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
                                        improvedTestCode.textContent = accumulatedContent;
                                        improvedTestCode.innerHTML = improvedTestCode.textContent + '<span class="typing-cursor"></span>';
                                        
                                        // Highlight the code
                                        hljs.highlightElement(improvedTestCode);
                                        
                                        // Add the cursor back
                                        improvedTestCode.innerHTML = improvedTestCode.innerHTML + '<span class="typing-cursor"></span>';
                                    }
                                    
                                    if (data.done) {
                                        // Remove the typing cursor when done
                                        improvedTestCode.textContent = accumulatedContent;
                                        hljs.highlightElement(improvedTestCode);
                                        
                                        // Refresh the test case list
                                        loadTestCases(improveSelectScript.value);
                                        showToast("Test case improved successfully", 'success');
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
                    showToast(result.message || 'Failed to improve test case', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                improveTestForm.querySelector('button[type="submit"]').disabled = false;
                improveTestForm.querySelector('button[type="submit"]').innerHTML = 'Improve Test Case';
            }
        });
    }
    
    // Copy buttons event listeners
    if (copyTestResult) {
        copyTestResult.addEventListener('click', function() {
            const codeToCopy = testCode.textContent;
            copyToClipboard(codeToCopy);
        });
    }
    
    if (copyImprovedTest) {
        copyImprovedTest.addEventListener('click', function() {
            const codeToCopy = improvedTestCode.textContent;
            copyToClipboard(codeToCopy);
        });
    }
    
    // Script selection change handlers
    if (testSelectScript) {
        testSelectScript.addEventListener('change', async function() {
            const scriptId = this.value;
            if (scriptId) {
                try {
                    // Fetch the script content
                    const result = await apiRequest(`/api/coding/scripts/${scriptId}`, 'GET');
                    
                    if (result.success) {
                        // Update the script content
                        testScriptContent.value = result.script.content;
                    }
                } catch (error) {
                    console.error('Error fetching script:', error);
                    showToast(`Error: ${error.message}`, 'error');
                }
            } else {
                testScriptContent.value = '';
            }
        });
    }
    
    if (executeSelectScript) {
        executeSelectScript.addEventListener('change', async function() {
            const scriptId = this.value;
            if (scriptId) {
                try {
                    // Fetch the script content
                    const scriptResult = await apiRequest(`/api/coding/scripts/${scriptId}`, 'GET');
                    
                    if (scriptResult.success) {
                        // Update the script content
                        executeScriptContent.value = scriptResult.script.content;
                    }
                    
                    // Fetch test cases for the script
                    loadTestCases(scriptId, executeSelectTest);
                    
                    // Enable the test selection dropdown
                    executeSelectTest.disabled = false;
                } catch (error) {
                    console.error('Error fetching script or test cases:', error);
                    showToast(`Error: ${error.message}`, 'error');
                }
            } else {
                executeScriptContent.value = '';
                executeSelectTest.innerHTML = '<option value="">-- Select a test case --</option>';
                executeSelectTest.disabled = true;
                executeTestContent.value = '';
            }
        });
    }
    
    if (executeSelectTest) {
        executeSelectTest.addEventListener('change', function() {
            const testCaseId = this.value;
            if (testCaseId) {
                const testCase = testCases.find(tc => tc.id == testCaseId);
                if (testCase) {
                    executeTestContent.value = testCase.content;
                    executeTestForm.querySelector('button[type="submit"]').disabled = false;
                }
            } else {
                executeTestContent.value = '';
                executeTestForm.querySelector('button[type="submit"]').disabled = true;
            }
        });
    }
    
    if (improveSelectScript) {
        improveSelectScript.addEventListener('change', async function() {
            const scriptId = this.value;
            if (scriptId) {
                try {
                    // Fetch the script content
                    const scriptResult = await apiRequest(`/api/coding/scripts/${scriptId}`, 'GET');
                    
                    if (scriptResult.success) {
                        // Update the script content
                        improveScriptContent.value = scriptResult.script.content;
                    }
                    
                    // Fetch test cases for the script
                    loadTestCases(scriptId, improveSelectTest);
                    
                    // Enable the test selection dropdown
                    improveSelectTest.disabled = false;
                } catch (error) {
                    console.error('Error fetching script or test cases:', error);
                    showToast(`Error: ${error.message}`, 'error');
                }
            } else {
                improveScriptContent.value = '';
                improveSelectTest.innerHTML = '<option value="">-- Select a test case --</option>';
                improveSelectTest.disabled = true;
                improveTestContent.value = '';
            }
        });
    }
    
    if (improveSelectTest) {
        improveSelectTest.addEventListener('change', function() {
            const testCaseId = this.value;
            if (testCaseId) {
                const testCase = testCases.find(tc => tc.id == testCaseId);
                if (testCase) {
                    improveTestContent.value = testCase.content;
                    improveTestForm.querySelector('button[type="submit"]').disabled = false;
                }
            } else {
                improveTestContent.value = '';
                improveTestForm.querySelector('button[type="submit"]').disabled = true;
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
        // Update Generate Test Case selector
        if (testSelectScript) {
            const currentValue = testSelectScript.value;
            testSelectScript.innerHTML = '<option value="">-- Select a script --</option>';
            
            scripts.forEach(script => {
                const option = document.createElement('option');
                option.value = script.id;
                option.textContent = script.title;
                testSelectScript.appendChild(option);
            });
            
            // Restore selected value if it still exists
            if (currentValue && scripts.some(s => s.id == currentValue)) {
                testSelectScript.value = currentValue;
            }
        }
        
        // Update Execute Test script selector
        if (executeSelectScript) {
            const currentValue = executeSelectScript.value;
            executeSelectScript.innerHTML = '<option value="">-- Select a script --</option>';
            
            scripts.forEach(script => {
                const option = document.createElement('option');
                option.value = script.id;
                option.textContent = script.title;
                executeSelectScript.appendChild(option);
            });
            
            // Restore selected value if it still exists
            if (currentValue && scripts.some(s => s.id == currentValue)) {
                executeSelectScript.value = currentValue;
                
                // Reload test cases for the script
                loadTestCases(currentValue, executeSelectTest);
            }
        }
        
        // Update Improve Test script selector
        if (improveSelectScript) {
            const currentValue = improveSelectScript.value;
            improveSelectScript.innerHTML = '<option value="">-- Select a script --</option>';
            
            scripts.forEach(script => {
                const option = document.createElement('option');
                option.value = script.id;
                option.textContent = script.title;
                improveSelectScript.appendChild(option);
            });
            
            // Restore selected value if it still exists
            if (currentValue && scripts.some(s => s.id == currentValue)) {
                improveSelectScript.value = currentValue;
                
                // Reload test cases for the script
                loadTestCases(currentValue, improveSelectTest);
            }
        }
    }
    
    // Function to load test cases for a script
    async function loadTestCases(scriptId, targetSelect) {
        try {
            const result = await apiRequest(`/api/testing/test-cases?script_id=${scriptId}`, 'GET');
            
            if (result.success) {
                testCases = result.test_cases;
                
                // Update test case selectors if a target is specified
                if (targetSelect) {
                    const currentValue = targetSelect.value;
                    targetSelect.innerHTML = '<option value="">-- Select a test case --</option>';
                    
                    testCases.forEach(testCase => {
                        const option = document.createElement('option');
                        option.value = testCase.id;
                        option.textContent = testCase.title;
                        targetSelect.appendChild(option);
                    });
                    
                    // Restore selected value if it still exists
                    if (currentValue && testCases.some(tc => tc.id == currentValue)) {
                        targetSelect.value = currentValue;
                    }
                    
                    // Enable/disable the target select based on test cases availability
                    targetSelect.disabled = testCases.length === 0;
                    
                    // Enable/disable the submit button
                    const form = targetSelect.closest('form');
                    if (form) {
                        const submitButton = form.querySelector('button[type="submit"]');
                        if (submitButton) {
                            submitButton.disabled = testCases.length === 0 || !targetSelect.value;
                        }
                    }
                }
            } else {
                console.error('Failed to load test cases:', result.message);
            }
        } catch (error) {
            console.error('Error loading test cases:', error);
        }
    }
    
    // Function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
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
</style>
`);
});
