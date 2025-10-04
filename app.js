document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------------------------------------
    // 1. FRONTEND ELEMENT REFERENCES
    // ----------------------------------------------------------------------------------
    const pdfFile = document.getElementById('pdfFile');
    const chooseFileBtn = document.getElementById('chooseFileBtn');
    const buttonText = document.getElementById('buttonText');
    const buttonSpinner = document.getElementById('buttonSpinner');
    const uploadLabel = document.querySelector('.upload-box'); 
    const statusMessage = document.getElementById('statusMessage');
    const resultsSection = document.getElementById('resultsSection');
    const summaryTextarea = document.getElementById('summaryText');
    const podcastAudio = document.getElementById('podcastAudio');
    const downloadLink = document.getElementById('downloadLink');
    const audioPlaceholder = document.getElementById('audioPlaceholder');
    const audioPlayerWrapper = document.getElementById('audioPlayerWrapper');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const processingSteps = document.getElementById('processingSteps');
    const copySummaryBtn = document.getElementById('copySummaryBtn');
    const wordCount = document.getElementById('wordCount');
    const charCount = document.getElementById('charCount');
    const audioDuration = document.getElementById('audioDuration');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const rewindBtn = document.getElementById('rewindBtn');
    const forwardBtn = document.getElementById('forwardBtn');

    let selectedFile = null;
    let isProcessing = false;

    // Ensure the main button is disabled initially until a file is selected
    if (chooseFileBtn) {
        chooseFileBtn.disabled = true;
    }


    // ----------------------------------------------------------------------------------
    // 2. EVENT LISTENERS
    // ----------------------------------------------------------------------------------

    // A. File Input Change Listener (when user selects a file)
    if (pdfFile) {
        pdfFile.addEventListener('change', (e) => {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                // Check if the selected file is a PDF
                if (selectedFile.type !== 'application/pdf') {
                    showStatus('Invalid file type. Please select a PDF file.', 'error');
                    selectedFile = null;
                    if (chooseFileBtn) chooseFileBtn.disabled = true;
                    pdfFile.value = ''; // Clear the file input
                    return;
                }

                // File is valid
                if (uploadLabel) {
                    uploadLabel.style.borderColor = 'var(--accent-purple)';
                    uploadLabel.classList.add('animate-pulse');
                }
                
                if (chooseFileBtn && buttonText) {
                    buttonText.textContent = `Process PDF: ${selectedFile.name}`;
                    chooseFileBtn.disabled = false;
                }
                
                showStatus('File selected. Click "Process PDF" to begin.', 'success');
                
                // Update file info
                updateFileInfo(selectedFile);
            } else {
                selectedFile = null;
                if (chooseFileBtn && buttonText) {
                    buttonText.textContent = 'Choose PDF File';
                    chooseFileBtn.disabled = true;
                }
                if (statusMessage) statusMessage.textContent = '';
                if (uploadLabel) {
                    uploadLabel.style.borderColor = 'var(--primary-purple)';
                    uploadLabel.classList.remove('animate-pulse');
                }
            }
        });
    }

    // B. Main Process Button Click Listener
    if (chooseFileBtn) {
        chooseFileBtn.addEventListener('click', () => {
            if (selectedFile) {
                // If a file is selected, call the main processing function
                processFile(selectedFile);
            } else {
                // If the button is clicked without a file, trigger the hidden file input
                if (pdfFile) pdfFile.click(); 
            }
        });
    }


    // C. Drag and Drop Handlers (The code that makes the box light up)
    if (uploadLabel) {
        // Prevent default browser behavior for drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadLabel.addEventListener(eventName, preventDefaults, false);
        });

        // Highlight the box when an item is dragged over
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadLabel.addEventListener(eventName, highlight, false);
        });

        // Remove highlight when item leaves or is dropped
        ['dragleave', 'drop'].forEach(eventName => {
            uploadLabel.addEventListener(eventName, unhighlight, false);
        });

        uploadLabel.addEventListener('drop', handleDrop, false);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        if (uploadLabel) uploadLabel.classList.add('border-4', 'border-dashed', 'border-accent-purple');
    }

    function unhighlight() {
        if (uploadLabel) uploadLabel.classList.remove('border-4', 'border-dashed', 'border-accent-purple');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            selectedFile = files[0];
            if (selectedFile.type === 'application/pdf') {
                // Manually update the hidden file input's file list
                if (pdfFile) pdfFile.files = files; 
                // Manually trigger the change listener to update the UI
                if (pdfFile) pdfFile.dispatchEvent(new Event('change'));
            } else {
                if (statusMessage) statusMessage.textContent = 'Invalid file type. Please drop a PDF file.';
                selectedFile = null;
                if (chooseFileBtn) chooseFileBtn.disabled = true;
            }
        }
    }


    // ----------------------------------------------------------------------------------
    // 3. CORE FILE PROCESSING FUNCTION (Communicates with Python Server)
    // ----------------------------------------------------------------------------------

    async function processFile(file) {
        if (!file || isProcessing) return;
        
        isProcessing = true;
        
        // 1. Lock the UI and show status
        setProcessingState(true);
        showStatus('Starting PDF processing...', 'info');
        showProgress(0, 'Initializing...');
        
        // Hide previous results and show audio placeholder area
        if (resultsSection) resultsSection.style.display = 'none';
        if (audioPlaceholder) audioPlaceholder.style.display = 'block';
        if (audioPlayerWrapper) audioPlayerWrapper.style.display = 'none';

        // 2. BACKEND API CALL 
        const formData = new FormData();
        formData.append('pdfFile', file); 

        // Flask server's URL
        const apiUrl = 'http://127.0.0.1:5000/api/process-pdf'; 

        try {
            // Simulate progress steps
            updateProgressStep(1, 'active');
            showProgress(20, 'Extracting text from PDF...');
            await sleep(1000);
            
            updateProgressStep(2, 'active');
            showProgress(50, 'AI is analyzing and summarizing...');
            await sleep(1000);
            
            updateProgressStep(3, 'active');
            showProgress(80, 'Generating audio podcast...');
            
            // Send the PDF file to the server
            const response = await fetch(apiUrl, {
                method: 'POST',
                body: formData, // Contains the PDF file
            });
            
            // Handle server errors
            if (!response.ok) {
                let errorDetails = `Server returned status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorDetails = errorData.error || errorDetails;
                } catch (e) {
                    // response was not JSON, use default error message
                }
                throw new Error(errorDetails);
            }

            // Get the JSON response from the server 
            const result = await response.json();
            
            // Complete progress
            showProgress(100, 'Processing complete!');
            updateProgressStep(3, 'completed');
            
            // 3. Update UI with Results
            if (summaryTextarea) {
                summaryTextarea.value = result.summary;
                updateSummaryStats(result.summary);
            }
            if (podcastAudio) {
                podcastAudio.src = result.audioUrl;
                setupAudioControls();
            }
            if (downloadLink) downloadLink.href = result.audioUrl;

            showStatus('Success! Your PDF is now a summary and a podcast.', 'success');
            
            // Show the results section with animation
            if (resultsSection) {
                resultsSection.style.display = 'block';
                resultsSection.scrollIntoView({ behavior: 'smooth' });
            }
            if (audioPlaceholder) audioPlaceholder.style.display = 'none';
            if (audioPlayerWrapper) audioPlayerWrapper.style.display = 'block';

        } catch (error) {
            console.error('Processing failed:', error);
            showStatus(`Error: Processing failed. Details: ${error.message}`, 'error');
            updateProgressStep(3, 'error');
        } finally {
            setProcessingState(false);
            isProcessing = false;
        }
    }

    // ----------------------------------------------------------------------------------
    // 4. HELPER FUNCTIONS
    // ----------------------------------------------------------------------------------

    function showStatus(message, type = 'info') {
        if (!statusMessage) return;
        
        statusMessage.textContent = message;
        statusMessage.className = `text-center mt-4 font-medium text-lg status-${type}`;
    }

    function setProcessingState(processing) {
        if (chooseFileBtn) {
            chooseFileBtn.disabled = processing;
            if (processing) {
                buttonText.textContent = 'Processing...';
                buttonSpinner.classList.remove('hidden');
                chooseFileBtn.classList.add('loading');
            } else {
                buttonText.textContent = selectedFile ? 'Process New PDF' : 'Choose PDF File';
                buttonSpinner.classList.add('hidden');
                chooseFileBtn.classList.remove('loading');
            }
        }
        
        if (processing) {
            if (processingSteps) processingSteps.classList.remove('hidden');
            if (progressContainer) progressContainer.style.display = 'block';
        } else {
            if (processingSteps) processingSteps.classList.add('hidden');
            if (progressContainer) progressContainer.style.display = 'none';
        }
    }

    function showProgress(percentage, text) {
        if (progressFill) progressFill.style.width = `${percentage}%`;
        if (progressText) progressText.textContent = text;
    }

    function updateProgressStep(stepNumber, status) {
        const steps = document.querySelectorAll('.step');
        if (steps[stepNumber - 1]) {
            steps[stepNumber - 1].classList.remove('active', 'completed', 'error');
            steps[stepNumber - 1].classList.add(status);
        }
    }

    function updateFileInfo(file) {
        const fileSize = (file.size / (1024 * 1024)).toFixed(2);
        console.log(`File: ${file.name}, Size: ${fileSize}MB`);
    }

    function updateSummaryStats(text) {
        if (wordCount) {
            const words = text.trim().split(/\s+/).length;
            wordCount.textContent = `${words} words`;
        }
        if (charCount) {
            charCount.textContent = `${text.length} characters`;
        }
    }

    function setupAudioControls() {
        if (!podcastAudio) return;

        // Update duration when metadata loads
        podcastAudio.addEventListener('loadedmetadata', () => {
            if (audioDuration) {
                audioDuration.textContent = formatTime(podcastAudio.duration);
            }
        });

        // Play/pause button
        if (playPauseBtn) {
            playPauseBtn.addEventListener('click', () => {
                if (podcastAudio.paused) {
                    podcastAudio.play();
                    playPauseBtn.innerHTML = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/></svg>';
                } else {
                    podcastAudio.pause();
                    playPauseBtn.innerHTML = '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
                }
            });
        }

        // Rewind button
        if (rewindBtn) {
            rewindBtn.addEventListener('click', () => {
                podcastAudio.currentTime = Math.max(0, podcastAudio.currentTime - 10);
            });
        }

        // Forward button
        if (forwardBtn) {
            forwardBtn.addEventListener('click', () => {
                podcastAudio.currentTime = Math.min(podcastAudio.duration, podcastAudio.currentTime + 10);
            });
        }
    }

    function formatTime(seconds) {
        if (isNaN(seconds)) return '--:--';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Copy summary functionality
    if (copySummaryBtn) {
        copySummaryBtn.addEventListener('click', async () => {
            if (summaryTextarea && summaryTextarea.value) {
                try {
                    await navigator.clipboard.writeText(summaryTextarea.value);
                    copySummaryBtn.classList.add('copied');
                    copySummaryBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>';
                    setTimeout(() => {
                        copySummaryBtn.classList.remove('copied');
                        copySummaryBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>';
                    }, 2000);
                } catch (err) {
                    console.error('Failed to copy text: ', err);
                }
            }
        });
    }
});