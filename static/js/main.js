// Main JavaScript file for VidPoint

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initializeApp();
});

function initializeApp() {
    // Set up form submission handlers
    setupFormHandlers();
    
    // Set up video input handlers
    setupVideoInput();
    
    // Initialize user interface components
    initializeUI();
}

function setupFormHandlers() {
    const videoForm = document.getElementById('video-form');
    if (videoForm) {
        videoForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Show loading state
            setLoadingState(true);
            
            try {
                const formData = new FormData(videoForm);
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const data = await response.json();
                displayResults(data);
            } catch (error) {
                showError('An error occurred while processing your video. Please try again.');
                console.error('Error:', error);
            } finally {
                setLoadingState(false);
            }
        });
    }
}

function setupVideoInput() {
    const videoInput = document.getElementById('video-input');
    const urlInput = document.getElementById('url-input');
    
    if (videoInput) {
        videoInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Clear URL input if file is selected
                if (urlInput) {
                    urlInput.value = '';
                }
                validateVideoFile(file);
            }
        });
    }
    
    if (urlInput) {
        urlInput.addEventListener('input', function(e) {
            // Clear file input if URL is entered
            if (videoInput && e.target.value) {
                videoInput.value = '';
            }
            validateVideoUrl(e.target.value);
        });
    }
}

function validateVideoFile(file) {
    const maxSize = 500 * 1024 * 1024; // 500MB
    const allowedTypes = ['video/mp4', 'video/webm', 'video/quicktime'];
    
    if (file.size > maxSize) {
        showError('File size exceeds 500MB limit.');
        return false;
    }
    
    if (!allowedTypes.includes(file.type)) {
        showError('Please upload a valid video file (MP4, WebM, or QuickTime).');
        return false;
    }
    
    return true;
}

function validateVideoUrl(url) {
    // Basic URL validation
    try {
        new URL(url);
        return true;
    } catch (e) {
        if (url) {
            showError('Please enter a valid URL.');
        }
        return false;
    }
}

function setLoadingState(isLoading) {
    const submitButton = document.querySelector('#video-form button[type="submit"]');
    const loadingSpinner = document.querySelector('.loading');
    
    if (submitButton) {
        submitButton.disabled = isLoading;
        submitButton.textContent = isLoading ? 'Processing...' : 'Process Video';
    }
    
    if (loadingSpinner) {
        loadingSpinner.style.display = isLoading ? 'flex' : 'none';
    }
}

function displayResults(data) {
    const resultsContainer = document.querySelector('.results');
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = '';
    
    // Display summary
    if (data.summary) {
        const summaryCard = createResultCard('Summary', data.summary);
        resultsContainer.appendChild(summaryCard);
    }
    
    // Display key points
    if (data.keyPoints && data.keyPoints.length > 0) {
        const pointsList = data.keyPoints.map(point => `<li>${point}</li>`).join('');
        const keyPointsCard = createResultCard('Key Points', `<ul>${pointsList}</ul>`);
        resultsContainer.appendChild(keyPointsCard);
    }
    
    // Add export button if results are available
    if (data.summary || (data.keyPoints && data.keyPoints.length > 0)) {
        const exportButton = document.createElement('button');
        exportButton.className = 'btn export-btn';
        exportButton.textContent = 'Export to Word';
        exportButton.onclick = () => exportToWord(data);
        resultsContainer.appendChild(exportButton);
    }
}

function createResultCard(title, content) {
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `
        <h3>${title}</h3>
        <div class="result-content">${content}</div>
    `;
    return card;
}

async function exportToWord(data) {
    try {
        const response = await fetch('/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'vidpoint_summary.docx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        showError('Failed to export document. Please try again.');
        console.error('Export error:', error);
    }
}

function showError(message) {
    const errorContainer = document.querySelector('.error-message');
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    }
}

function initializeUI() {
    // Initialize any UI components (tooltips, dropdowns, etc.)
    setupUserMenu();
    setupPricingToggle();
}

function setupUserMenu() {
    const userMenu = document.querySelector('.user-menu');
    if (userMenu) {
        userMenu.addEventListener('click', function(e) {
            const dropdown = this.querySelector('.user-dropdown');
            if (dropdown) {
                dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
                e.stopPropagation();
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function() {
            const dropdown = userMenu.querySelector('.user-dropdown');
            if (dropdown) {
                dropdown.style.display = 'none';
            }
        });
    }
}

function setupPricingToggle() {
    const pricingToggles = document.querySelectorAll('.pricing-toggle');
    pricingToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const period = this.dataset.period;
            updatePricingDisplay(period);
        });
    });
}

function updatePricingDisplay(period) {
    const prices = document.querySelectorAll('.price');
    prices.forEach(price => {
        const monthlyPrice = price.dataset.monthly;
        const yearlyPrice = price.dataset.yearly;
        price.textContent = period === 'yearly' ? yearlyPrice : monthlyPrice;
    });
}
