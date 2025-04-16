// JavaScript for the FA Transcriber module

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadForm = document.getElementById('upload-form');
    const uploadContainer = document.getElementById('upload-container');
    const imageUpload = document.getElementById('image-upload');
    const previewContainer = document.getElementById('preview-container');
    const imagePreview = document.getElementById('image-preview');
    const removeImageButton = document.getElementById('remove-image');
    const transcribeButton = document.getElementById('transcribe-button');
    const resultsContainer = document.getElementById('results-container');
    const resultsBody = document.getElementById('results-body');
    const exportCsvButton = document.getElementById('export-csv');
    const exportJsonButton = document.getElementById('export-json');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    // Store the transcription data for export
    let transcriptionData = null;
    
    // Setup drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadContainer.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadContainer.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadContainer.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        uploadContainer.classList.add('border-indigo-500', 'bg-indigo-50');
    }
    
    function unhighlight() {
        uploadContainer.classList.remove('border-indigo-500', 'bg-indigo-50');
    }
    
    // Handle file drop
    uploadContainer.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFiles(files);
        }
    }
    
    // Handle file selection via button
    uploadContainer.addEventListener('click', function() {
        imageUpload.click();
    });
    
    imageUpload.addEventListener('change', function() {
        if (this.files.length > 0) {
            handleFiles(this.files);
        }
    });
    
    // Process selected files
    function handleFiles(files) {
        const file = files[0];
        
        // Check file type
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
        if (!validTypes.includes(file.type)) {
            showToast('Invalid file type. Please select an image.', 'error');
            return;
        }
        
        // Display preview
        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            uploadContainer.classList.add('hidden');
            previewContainer.classList.remove('hidden');
            
            // Hide results if a new image is uploaded
            resultsContainer.classList.add('hidden');
            transcriptionData = null;
        };
        reader.readAsDataURL(file);
    }
    
    // Remove image
    removeImageButton.addEventListener('click', function() {
        imageUpload.value = '';
        imagePreview.src = '#';
        previewContainer.classList.add('hidden');
        uploadContainer.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        transcriptionData = null;
    });
    
    // Form submission
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        
        if (imageUpload.files.length === 0) {
            showToast('Please select an image to transcribe.', 'error');
            return;
        }
        
        formData.append('image', imageUpload.files[0]);
        
        // Show loading overlay
        loadingOverlay.classList.remove('hidden');
        
        try {
            const response = await fetch('/api/fa-transcriber/transcribe', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`API request failed with status ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                // Store transcription data
                transcriptionData = result.items;
                
                // Display results
                displayResults(result.items);
                
                // Show results container
                resultsContainer.classList.remove('hidden');
                
                showToast('Image transcribed successfully!', 'success');
            } else {
                showToast(result.error || 'Failed to transcribe image.', 'error');
                console.error('Transcription error:', result.error);
            }
        } catch (error) {
            console.error('Error transcribing image:', error);
            showToast('An error occurred while transcribing the image.', 'error');
        } finally {
            // Hide loading overlay
            loadingOverlay.classList.add('hidden');
        }
    });
    
    // Display results in table
    function displayResults(items) {
        resultsBody.innerHTML = '';
        
        if (!items || items.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="7" class="text-center py-4 text-gray-500">
                    No data extracted from the image.
                </td>
            `;
            resultsBody.appendChild(row);
            return;
        }
        
        items.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${escapeHtml(item.sheet_name || '')}</td>
                <td>${escapeHtml(item.message || '')}</td>
                <td>${escapeHtml(item.start_ecu || '')}</td>
                <td>${escapeHtml(item.end_ecu || '')}</td>
                <td>${escapeHtml(item.sending_ecu || '')}</td>
                <td>${escapeHtml(item.receiving_ecu || '')}</td>
                <td>${escapeHtml(item.dashed_line || '')}</td>
            `;
            resultsBody.appendChild(row);
        });
    }
    
    // Export as CSV
    exportCsvButton.addEventListener('click', function() {
        if (!transcriptionData || transcriptionData.length === 0) {
            showToast('No data to export.', 'error');
            return;
        }
        
        const headers = [
            'Sheet Name',
            'Message',
            'Start ECU',
            'End ECU',
            'Sending ECU',
            'Receiving ECU',
            'Dashed Line'
        ];
        
        let csvContent = headers.join(',') + '\n';
        
        transcriptionData.forEach(item => {
            const row = [
                formatCsvField(item.sheet_name),
                formatCsvField(item.message),
                formatCsvField(item.start_ecu),
                formatCsvField(item.end_ecu),
                formatCsvField(item.sending_ecu),
                formatCsvField(item.receiving_ecu),
                formatCsvField(item.dashed_line)
            ];
            
            csvContent += row.join(',') + '\n';
        });
        
        downloadFile(csvContent, 'fa-transcription.csv', 'text/csv');
    });
    
    // Export as JSON
    exportJsonButton.addEventListener('click', function() {
        if (!transcriptionData || transcriptionData.length === 0) {
            showToast('No data to export.', 'error');
            return;
        }
        
        const jsonContent = JSON.stringify(transcriptionData, null, 2);
        downloadFile(jsonContent, 'fa-transcription.json', 'application/json');
    });
    
    // Helper functions
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }
    
    function formatCsvField(value) {
        if (!value) return '';
        // Escape quotes and wrap in quotes if contains comma, quote, or newline
        const formatted = value.toString().replace(/"/g, '""');
        if (formatted.includes(',') || formatted.includes('"') || formatted.includes('\n')) {
            return `"${formatted}"`;
        }
        return formatted;
    }
    
    function downloadFile(content, filename, contentType) {
        const blob = new Blob([content], { type: contentType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast(`Downloaded ${filename}`, 'success');
    }
    
    // Fallback toast function if not defined in the global scope
    if (typeof window.showToast !== 'function') {
        window.showToast = function(message, type = 'info') {
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
            
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s ease';
                
                setTimeout(() => {
                    document.body.removeChild(toast);
                }, 500);
            }, 3000);
        };
    }
});
