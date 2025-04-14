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
            
            const submitButton = generateTestForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Generating...';
            
            // Get form data - Use script ID and requirements
            const script_id = testSelectScript.value;
            const requirements = testRequirements.value.trim(); // Changed from test_requirements
            // const script_content = testScriptContent.value; // No longer needed in request
            
            if (!script_id) {
                showToast('Please select a script', 'error');
                submitButton.disabled = false;
                submitButton.innerHTML = 'Generate Test Case';
                return;
            }

            // Prepare result area
            generateTestResult.classList.remove('hidden');
            testTitle.textContent = 'Generating Test Case...';
            testCode.textContent = 'Please wait...';
            hljs.highlightElement(testCode);
            if(copyTestResult) copyTestResult.disabled = true;

            try {
                // Send request to API (non-streaming)
                const response = await fetch('/api/testing/generate', { // Removed ?stream=true
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken() // Assuming CSRF is needed
                    },
                    body: JSON.stringify({ 
                        script_id: script_id, 
                        requirements: requirements // Send requirements
                        // script_content: script_content, // Removed
                        // test_requirements: test_requirements // Renamed and value taken from requirements
                    })
                });
                
                const result = await response.json(); // Get full JSON response

                if (response.ok && result.success) {
                    // --- Response Handling --- 
                    const testCaseData = result.test_case; // Backend returns {'success': true, 'test_case': tc_obj}

                    testTitle.textContent = testCaseData.title || 'Generated Test Case';
                    testCode.textContent = testCaseData.content;
                    
                    // Highlight the code
                    hljs.highlightElement(testCode);

                    // Enable copy button
                    if(copyTestResult) copyTestResult.disabled = false;
                    
                    // Reload test cases in other tabs (optional, depends on desired UX)
                    loadTestCases(script_id, executeSelectTest); 
                    loadTestCases(script_id, improveSelectTest);

                    showToast("Test case generated successfully", 'success');

                } else {
                    // Handle error from API response
                    const errorMessage = result.error || 'Failed to generate test case';
                    testTitle.textContent = 'Error';
                    testCode.textContent = errorMessage;
                    showToast(errorMessage, 'error');
                }

            } catch (error) {
                console.error('Error generating test case:', error);
                testTitle.textContent = 'Error';
                testCode.textContent = `An error occurred: ${error.message}`;
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                submitButton.disabled = false;
                submitButton.innerHTML = 'Generate Test Case';
            }
        });
    }
    
    // Execute Test Form Submit
    if (executeTestForm) {
        executeTestForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitButton = executeTestForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Executing...';
            
            // Get form data
            const test_case_id = executeSelectTest.value;
            // script_content and test_content are fetched by backend using ID
            
            if (!test_case_id) {
                 showToast('Please select a test case to execute', 'error');
                 submitButton.disabled = false;
                 submitButton.innerHTML = 'Execute Test';
                 return;
            }

            // Prepare result area
            executeTestResult.classList.remove('hidden');
            testStatusBadge.textContent = 'Running...';
            testStatusBadge.className = 'badge bg-secondary';
            testOutput.textContent = 'Executing test...';
            // testExecutionTime.textContent = 'N/A'; // Remove or hide this
            testTimestamp.textContent = new Date().toLocaleString();

            try {
                // Send request to API
                const response = await fetch('/api/testing/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken() // Assuming CSRF needed
                    },
                    body: JSON.stringify({ 
                        test_case_id: test_case_id 
                    })
                });
                
                const result = await response.json(); // Get full JSON response

                if (result.success) {
                    // --- Response Handling --- 
                    const testResultData = result.test_result; // Backend returns {'success': true, 'test_result': res_obj}
                    
                    testStatusBadge.textContent = testResultData.status;
                    // Set badge color based on status
                    if (testResultData.status === 'passed') {
                        testStatusBadge.className = 'badge bg-success';
                    } else if (testResultData.status === 'failed') {
                        testStatusBadge.className = 'badge bg-danger';
                    } else { // error or other
                        testStatusBadge.className = 'badge bg-warning text-dark'; // Use warning for errors
                    }
                    
                    // Display output
                    testOutput.textContent = testResultData.output || 'No output captured.';
                    
                    // Update timestamp if available in response (it is in the model)
                    testTimestamp.textContent = new Date(testResultData.created_at).toLocaleString();
                    // testExecutionTime.textContent = `${result.execution_time || 0}s`; // Not provided by backend
                    
                    showToast("Test execution completed", 'success');

                } else {
                    // Handle API error
                    const errorMessage = result.error || 'Failed to execute test case';
                    testStatusBadge.textContent = 'Error';
                    testStatusBadge.className = 'badge bg-danger';
                    testOutput.textContent = errorMessage;
                    showToast(errorMessage, 'error');
                }
                
            } catch (error) {
                console.error('Error executing test case:', error);
                testStatusBadge.textContent = 'Error';
                testStatusBadge.className = 'badge bg-danger';
                testOutput.textContent = `Client-side error: ${error.message}`;
                showToast(`Error: ${error.message}`, 'error');
            } finally {
                // Reset loading state
                submitButton.disabled = false;
                submitButton.innerHTML = 'Execute Test';
            }
        });
    }
    
    // Improve Test Case Form Submit - Disabled
    if (improveTestForm) {
        improveTestForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show 'Not Implemented' message and do nothing else
            showToast('The "Improve Test Case" feature is currently not available.', 'info');
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
