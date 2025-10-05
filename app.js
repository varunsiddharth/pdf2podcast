// PDF to Podcast Generator - Fixed Frontend JavaScript

let isProcessing = false;

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const pdfFileInput = document.getElementById('pdfFile');
    const chooseFileBtn = document.getElementById('chooseFileBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsSection = document.getElementById('resultsSection');
    const summaryText = document.getElementById('summaryText');
    const podcastAudio = document.getElementById('podcastAudio');
    const downloadLink = document.getElementById('downloadLink');
    const copyBtn = document.getElementById('copyBtn');
    const uploadArea = document.getElementById('uploadArea');
    const processingAnimation = document.getElementById('processingAnimation');

    // Event Listeners
    if (pdfFileInput) {
        pdfFileInput.addEventListener('change', handleFileSelect);
    }
    
    if (chooseFileBtn) {
        chooseFileBtn.addEventListener('click', () => {
            if (pdfFileInput) {
                pdfFileInput.click();
            }
        });
    }
    
    if (copyBtn) {
        copyBtn.addEventListener('click', copySummary);
    }

    // Enhanced drag and drop functionality
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(139, 92, 246, 0.5)';
            uploadArea.style.transform = 'scale(1.02)';
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            uploadArea.style.transform = 'scale(1)';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(255, 255, 255, 0.3)';
            uploadArea.style.transform = 'scale(1)';
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                if (pdfFileInput) {
                    pdfFileInput.files = files;
                }
                processFile(files[0]);
            } else {
                showStatus('Please upload a valid PDF file.', 'error');
            }
        });
    }

    function handleFileSelect(event) {
        console.log('File selected:', event.target.files[0]);
        const file = event.target.files[0];
        if (file && file.type === 'application/pdf') {
            console.log('Processing PDF file:', file.name);
            processFile(file);
        } else {
            console.log('Invalid file type:', file ? file.type : 'no file');
            showStatus('Please select a valid PDF file.', 'error');
        }
    }

    async function processFile(file) {
        if (!file || isProcessing) return;

        console.log('Starting file processing...');
        isProcessing = true;
        
        // Show processing animation
        if (processingAnimation) {
            processingAnimation.classList.remove('hidden');
        }
        showStatus('Processing your PDF...', 'info');
        
        // Disable upload area
        if (uploadArea) {
            uploadArea.style.pointerEvents = 'none';
            uploadArea.style.opacity = '0.6';
        }
        
        const formData = new FormData();
        formData.append('pdfFile', file);
        console.log('Sending request to server...');

        try {
            const response = await fetch('/api/process-pdf', {
                method: 'POST',
                body: formData,
            });

            console.log('Response status:', response.status);
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error('Server error:', errorData);
                throw new Error(errorData.error || 'Server error');
            }

            const result = await response.json();
            console.log('Server response:', result);
            
            // Update UI with results
            if (summaryText) {
                summaryText.value = result.summary;
                // Ensure the textarea shows the full content
                summaryText.style.height = 'auto';
                summaryText.style.height = Math.min(summaryText.scrollHeight, 400) + 'px';
                // Scroll to top to show the beginning of the summary
                summaryText.scrollTop = 0;
            }
            if (podcastAudio) {
                podcastAudio.src = result.audioUrl;
            }
            if (downloadLink) {
                downloadLink.href = result.audioUrl;
            }
            
            // Show results with animation
            if (resultsSection) {
                resultsSection.style.display = 'block';
                resultsSection.scrollIntoView({ behavior: 'smooth' });
            }
            
            showStatus('🎉 Success! Your PDF has been converted to a podcast.', 'success');
            
            // Add success animation
            if (resultsSection) {
                resultsSection.classList.add('animate-fade-in');
            }
            
        } catch (error) {
            console.error('Error:', error);
            showStatus(`❌ Error: ${error.message}`, 'error');
        } finally {
            isProcessing = false;
            if (processingAnimation) {
                processingAnimation.classList.add('hidden');
            }
            if (uploadArea) {
                uploadArea.style.pointerEvents = 'auto';
                uploadArea.style.opacity = '1';
            }
        }
    }

    function showStatus(message, type) {
        if (statusMessage) {
            statusMessage.innerHTML = message;
            statusMessage.className = `mt-6 text-center font-medium status-message ${
                type === 'success' ? 'status-success' : 
                type === 'error' ? 'status-error' : 
                'text-blue-400'
            }`;
            
            // Add animation based on type
            if (type === 'success') {
                statusMessage.style.animation = 'pulse 2s infinite';
            } else if (type === 'error') {
                statusMessage.style.animation = 'shake 0.5s ease-in-out';
            }
        }
    }

    function copySummary() {
        if (summaryText) {
            summaryText.select();
            document.execCommand('copy');
            
            // Visual feedback
            if (copyBtn) {
                copyBtn.innerHTML = `
                    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    Copied!
                `;
                copyBtn.classList.add('bg-green-600', 'hover:bg-green-700');
                
                setTimeout(() => {
                    copyBtn.innerHTML = `
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                        </svg>
                        Copy Summary
                    `;
                    copyBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
                    copyBtn.classList.add('bg-gradient-to-r', 'from-blue-600', 'to-cyan-600', 'hover:from-blue-700', 'hover:to-cyan-700');
                }, 2000);
            }
            
            showStatus('📋 Summary copied to clipboard!', 'success');
        }
    }

    // Add file size validation
    function validateFileSize(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB
        if (file.size > maxSize) {
            showStatus('File size too large. Please upload a file smaller than 50MB.', 'error');
            return false;
        }
        return true;
    }

    // Enhanced file processing with validation
    function processFileWithValidation(file) {
        if (!file || isProcessing) return;
        
        if (!validateFileSize(file)) return;
        
        if (file.type !== 'application/pdf') {
            showStatus('Please upload a valid PDF file.', 'error');
            return;
        }
        
        // Continue with processing...
        processFile(file);
    }

    // Animate elements on load
    const elements = document.querySelectorAll('.animate-fade-in, .animate-fade-in-delay');
    elements.forEach((el, index) => {
        el.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Add hover effects to cards
    const cards = document.querySelectorAll('.bg-white\\/10');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.2)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.1)';
        });
    });
});