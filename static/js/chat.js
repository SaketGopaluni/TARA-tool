// JavaScript for the Chat Module

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const queryType = document.getElementById('query-type');
    const chatMessages = document.getElementById('chat-messages');
    const clearChatButton = document.getElementById('btn-clear-chat');
    
    // Prompt helper buttons
    const ecuExplainButton = document.getElementById('btn-ecu-explain');
    const damageScenarioButton = document.getElementById('btn-damage-scenario');
    const threatScenarioButton = document.getElementById('btn-threat-scenario');
    const attackPatternButton = document.getElementById('btn-attack-pattern');
    
    // Prompt helper elements
    const promptHelper = document.getElementById('prompt-helper');
    const promptHelperTitle = document.getElementById('prompt-helper-title');
    const closePromptHelper = document.getElementById('close-prompt-helper');
    
    // Prompt helper forms
    const ecuExplainForm = document.getElementById('ecu-explain-form');
    const damageScenarioForm = document.getElementById('damage-scenario-form');
    const threatScenarioForm = document.getElementById('threat-scenario-form');
    const attackPatternForm = document.getElementById('attack-pattern-form');
    
    // Message templates
    const userMessageTemplate = document.getElementById('user-message-template');
    const assistantMessageTemplate = document.getElementById('assistant-message-template');
    const loadingTemplate = document.getElementById('loading-template');
    
    // Load chat history
    loadChatHistory();
    
    // Chat form submit
    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const message = chatInput.value.trim();
            const type = queryType.value;
            
            if (!message) return;
            
            // Add user message to the chat
            addMessage('user', message);
            
            // Clear input
            chatInput.value = '';
            
            // Show loading indicator
            const loadingIndicator = loadingTemplate.content.cloneNode(true);
            loadingIndicator.firstElementChild.id = 'loading-indicator';
            chatMessages.appendChild(loadingIndicator);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            
            try {
                // Create assistant message placeholder for streaming
                const assistantMessageNode = assistantMessageTemplate.content.cloneNode(true);
                const assistantMessageElement = assistantMessageNode.querySelector('.message-container');
                assistantMessageElement.id = 'streaming-message';
                const messageContent = assistantMessageNode.querySelector('.message-content');
                messageContent.innerHTML = '<span class="typing-cursor"></span>';
                
                // Send message to the server with streaming enabled
                const response = await fetch('/api/chat/send?stream=true', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ message, query_type: type })
                });
                
                // Remove loading indicator
                const indicator = document.getElementById('loading-indicator');
                if (indicator) {
                    chatMessages.removeChild(indicator);
                }
                
                if (response.ok) {
                    // Add the placeholder message to the chat
                    chatMessages.appendChild(assistantMessageElement);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    
                    // Set up the event source and handle streaming
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
                                    
                                    if (data.initializing) {
                                        console.log('Stream initialized');
                                        continue;
                                    }
                                    
                                    if (data.chunk) {
                                        // Update the streaming message with the new chunk
                                        accumulatedContent += data.chunk;
                                        const processedContent = processMessageContent(accumulatedContent);
                                        const streamingMessage = document.getElementById('streaming-message');
                                        if (streamingMessage) {
                                            const messageContent = streamingMessage.querySelector('.message-content');
                                            messageContent.innerHTML = processedContent + '<span class="typing-cursor"></span>';
                                            chatMessages.scrollTop = chatMessages.scrollHeight;
                                        }
                                    }
                                    
                                    if (data.done) {
                                        // Remove the typing cursor when done
                                        const streamingMessage = document.getElementById('streaming-message');
                                        if (streamingMessage) {
                                            streamingMessage.id = ''; // Remove the ID
                                            const messageContent = streamingMessage.querySelector('.message-content');
                                            messageContent.innerHTML = processMessageContent(accumulatedContent);
                                        }
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
                    showToast(result.message || 'Failed to send message', 'error');
                }
            } catch (error) {
                // Remove loading indicator
                const indicator = document.getElementById('loading-indicator');
                if (indicator) {
                    chatMessages.removeChild(indicator);
                }
                
                showToast(`Error: ${error.message}`, 'error');
            }
        });
    }
    
    // Clear chat button
    if (clearChatButton) {
        clearChatButton.addEventListener('click', async function() {
            try {
                const result = await apiRequest('/api/chat/clear', 'POST');
                
                if (result.success) {
                    // Clear the chat messages except for the welcome message
                    chatMessages.innerHTML = '';
                    
                    // Add the welcome message back
                    const welcomeMessage = `
                        <div class="flex">
                            <div class="flex-shrink-0 mr-3">
                                <div class="w-10 h-10 rounded-full bg-purple-500 flex items-center justify-center text-white">
                                    <i class="fas fa-robot"></i>
                                </div>
                            </div>
                            <div>
                                <div class="bg-white p-3 rounded-lg shadow-sm">
                                    <p class="text-gray-800">Hello! I'm your TARA Assistant. I can help with:</p>
                                    <ul class="list-disc pl-5 mt-2 text-gray-700">
                                        <li>Explaining ECUs and their cybersecurity implications</li>
                                        <li>Generating damage scenarios using the CIA triad</li>
                                        <li>Creating threat scenarios based on the STRIDE model</li>
                                        <li>Developing attack patterns for specific dataflows</li>
                                        <li>Answering questions about automotive cybersecurity</li>
                                    </ul>
                                    <p class="mt-2 text-gray-800">How can I assist you today?</p>
                                </div>
                                <div class="text-xs text-gray-500 mt-1 ml-2">TARA Assistant</div>
                            </div>
                        </div>
                    `;
                    chatMessages.innerHTML = welcomeMessage;
                    
                    showToast('Chat cleared successfully', 'success');
                } else {
                    showToast(result.message || 'Failed to clear chat', 'error');
                }
            } catch (error) {
                showToast(`Error: ${error.message}`, 'error');
            }
        });
    }
    
    // ECU Explanation button
    if (ecuExplainButton) {
        ecuExplainButton.addEventListener('click', function() {
            showPromptHelper('ECU Explanation', ecuExplainForm);
        });
    }
    
    // Damage Scenario button
    if (damageScenarioButton) {
        damageScenarioButton.addEventListener('click', function() {
            showPromptHelper('Damage Scenario (CIA)', damageScenarioForm);
        });
    }
    
    // Threat Scenario button
    if (threatScenarioButton) {
        threatScenarioButton.addEventListener('click', function() {
            showPromptHelper('Threat Scenario (STRIDE)', threatScenarioForm);
        });
    }
    
    // Attack Pattern button
    if (attackPatternButton) {
        attackPatternButton.addEventListener('click', function() {
            showPromptHelper('Attack Pattern', attackPatternForm);
        });
    }
    
    // Close prompt helper
    if (closePromptHelper) {
        closePromptHelper.addEventListener('click', function() {
            promptHelper.classList.add('hidden');
            // Reset the query type
            queryType.value = 'general';
        });
    }
    
    // ECU Explanation form submit
    if (document.getElementById('ecu-explain-submit')) {
        document.getElementById('ecu-explain-submit').addEventListener('click', function() {
            const ecuType = document.getElementById('ecu-type').value.trim();
            
            if (!ecuType) {
                showToast('Please enter an ECU type', 'error');
                return;
            }
            
            // Set the query type
            queryType.value = 'ecu_explanation';
            
            // Set the chat input
            chatInput.value = `Explain the ${ecuType} ECU, its functions, common interfaces, security concerns, and importance in automotive systems.`;
            
            // Hide the prompt helper
            promptHelper.classList.add('hidden');
            
            // Focus the chat input
            chatInput.focus();
        });
    }
    
    // Damage Scenario form submit
    if (document.getElementById('damage-scenario-submit')) {
        document.getElementById('damage-scenario-submit').addEventListener('click', function() {
            const component = document.getElementById('damage-component').value.trim();
            const ciaAspect = document.getElementById('cia-aspect').value;
            
            if (!component) {
                showToast('Please enter a component or system', 'error');
                return;
            }
            
            // Set the query type
            queryType.value = 'damage_scenario';
            
            // Set the chat input
            chatInput.value = `Generate a damage scenario for ${component} focusing on the ${ciaAspect} aspect of the CIA triad.`;
            
            // Hide the prompt helper
            promptHelper.classList.add('hidden');
            
            // Focus the chat input
            chatInput.focus();
        });
    }
    
    // Threat Scenario form submit
    if (document.getElementById('threat-scenario-submit')) {
        document.getElementById('threat-scenario-submit').addEventListener('click', function() {
            const component = document.getElementById('threat-component').value.trim();
            const strideAspect = document.getElementById('stride-aspect').value;
            
            if (!component) {
                showToast('Please enter a component or system', 'error');
                return;
            }
            
            // Set the query type
            queryType.value = 'threat_scenario';
            
            // Set the chat input
            chatInput.value = `Generate a threat scenario for ${component} focusing on the ${strideAspect} aspect of the STRIDE model.`;
            
            // Hide the prompt helper
            promptHelper.classList.add('hidden');
            
            // Focus the chat input
            chatInput.focus();
        });
    }
    
    // Attack Pattern form submit
    if (document.getElementById('attack-pattern-submit')) {
        document.getElementById('attack-pattern-submit').addEventListener('click', function() {
            const dataflowDescription = document.getElementById('dataflow-description').value.trim();
            
            if (!dataflowDescription) {
                showToast('Please enter a dataflow description', 'error');
                return;
            }
            
            // Set the query type
            queryType.value = 'attack_pattern';
            
            // Set the chat input
            chatInput.value = `Based on the following dataflow description, generate possible attack patterns:\n\n${dataflowDescription}`;
            
            // Hide the prompt helper
            promptHelper.classList.add('hidden');
            
            // Focus the chat input
            chatInput.focus();
        });
    }
    
    // Function to show prompt helper
    function showPromptHelper(title, form) {
        // Hide all forms
        ecuExplainForm.classList.add('hidden');
        damageScenarioForm.classList.add('hidden');
        threatScenarioForm.classList.add('hidden');
        attackPatternForm.classList.add('hidden');
        
        // Show the specified form
        form.classList.remove('hidden');
        
        // Set the title
        promptHelperTitle.textContent = title;
        
        // Show the prompt helper
        promptHelper.classList.remove('hidden');
    }
    
    // Function to add a message to the chat
    function addMessage(role, content) {
        let messageNode;
        
        if (role === 'user') {
            messageNode = userMessageTemplate.content.cloneNode(true);
        } else {
            messageNode = assistantMessageTemplate.content.cloneNode(true);
        }
        
        // Find the message content element
        const messageContent = messageNode.querySelector('.message-content');
        
        // Process the content
        const processedContent = processMessageContent(content);
        
        // Set the content (can include HTML)
        messageContent.innerHTML = processedContent;
        
        // Add the message to the chat
        chatMessages.appendChild(messageNode);
        
        // Scroll to the bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Function to process message content
    function processMessageContent(content) {
        // Convert newlines to <br>
        content = content.replace(/\n/g, '<br>');
        
        // Convert URLs to links
        content = content.replace(
            /(https?:\/\/[^\s]+)/g, 
            '<a href="$1" target="_blank" class="text-blue-600 hover:underline">$1</a>'
        );
        
        // Convert code blocks
        if (content.includes('```')) {
            const parts = content.split('```');
            for (let i = 1; i < parts.length; i += 2) {
                let code = parts[i];
                let language = '';
                
                // Check if there's a language specified
                if (code.indexOf('\n') > 0) {
                    language = code.substring(0, code.indexOf('\n')).trim();
                    code = code.substring(code.indexOf('\n') + 1);
                }
                
                parts[i] = `<pre><code class="language-${language}">${formatCodeForDisplay(code)}</code></pre>`;
            }
            content = parts.join('');
        }
        
        // Convert inline code
        content = content.replace(
            /`([^`]+)`/g, 
            '<code class="px-1 py-0.5 bg-gray-100 rounded text-sm font-mono">$1</code>'
        );
        
        return content;
    }
    
    // Function to load chat history
    async function loadChatHistory() {
        try {
            const result = await apiRequest('/api/chat/history', 'GET');
            
            if (result.success && result.messages && result.messages.length > 0) {
                // Clear the chat messages
                chatMessages.innerHTML = '';
                
                // Add each message to the chat
                result.messages.forEach(message => {
                    addMessage(message.role, message.content);
                });
                
                // Scroll to the bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }
    
    // Function to get CSRF token
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
});

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
