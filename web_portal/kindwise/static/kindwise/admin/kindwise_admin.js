/**
 * Kindwise Admin JavaScript
 * Interactive functionality for Kindwise identification records
 */

(function() {
    'use strict';

    /**
     * Initialize modal on page load
     */
    document.addEventListener('DOMContentLoaded', function() {
        createModal();
        addEventListeners();
    });

    /**
     * Create modal structure if it doesn't exist
     */
    function createModal() {
        if (document.getElementById('kindwise-modal')) {
            return; // Modal already exists
        }

        const modalHTML = `
            <div id="kindwise-modal" class="kindwise-modal">
                <div class="kindwise-modal-content">
                    <div class="kindwise-modal-header">
                        <span class="kindwise-modal-close">&times;</span>
                        <h2>Kindwise Identification Details</h2>
                    </div>
                    <div class="kindwise-modal-body" id="kindwise-modal-body">
                        <div class="loading">Loading...</div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Add event listeners for modal interactions
     */
    function addEventListeners() {
        const modal = document.getElementById('kindwise-modal');
        const closeBtn = document.querySelector('.kindwise-modal-close');

        // Close modal when clicking X
        if (closeBtn) {
            closeBtn.onclick = function() {
                modal.style.display = 'none';
            };
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        };

        // ESC key to close modal
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && modal.style.display === 'block') {
                modal.style.display = 'none';
            }
        });
    }

    /**
     * Show detailed information for a Kindwise record
     * @param {number} recordId - The ID of the Kindwise identification record
     */
    window.showKindwiseDetails = function(recordId) {
        const modal = document.getElementById('kindwise-modal');
        const modalBody = document.getElementById('kindwise-modal-body');

        // Show modal with loading state
        modal.style.display = 'block';
        modalBody.innerHTML = '<div class="loading" style="text-align:center;padding:40px;"><p>Loading details...</p></div>';

        // Fetch record details from API
        fetch(`/kindwise/records/${recordId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                displayRecordDetails(data, modalBody);
            })
            .catch(error => {
                console.error('Error fetching Kindwise details:', error);
                modalBody.innerHTML = `
                    <div class="error-box" style="background:#fee;border-left:4px solid #c00;padding:15px;color:#c00;">
                        <h4>Error Loading Details</h4>
                        <p>${error.message}</p>
                        <p>Record ID: ${recordId}</p>
                    </div>
                `;
            });
    };

    /**
     * Display record details in modal
     * @param {Object} data - The record data from API
     * @param {HTMLElement} container - The modal body element
     */
    function displayRecordDetails(data, container) {
        let html = '';

        // Basic Information
        html += `
            <div class="detail-section" style="margin-bottom:25px;">
                <h3 style="color:#ff6600;border-bottom:2px solid #ff6600;padding-bottom:8px;">Basic Information</h3>
                <table style="width:100%;margin-top:15px;">
                    <tr>
                        <td style="font-weight:600;width:180px;padding:8px 0;color:#666;">Record ID:</td>
                        <td style="padding:8px 0;">${data.id || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;padding:8px 0;color:#666;">User:</td>
                        <td style="padding:8px 0;">${data.user ? data.user.username : 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;padding:8px 0;color:#666;">Status:</td>
                        <td style="padding:8px 0;">${getStatusBadge(data.status)}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;padding:8px 0;color:#666;">Image Name:</td>
                        <td style="padding:8px 0;">${data.image_name || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:600;padding:8px 0;color:#666;">Created:</td>
                        <td style="padding:8px 0;">${formatDate(data.created_at)}</td>
                    </tr>
                </table>
            </div>
        `;

        // Image Preview
        if (data.image) {
            html += `
                <div class="detail-section" style="margin-bottom:25px;">
                    <h3 style="color:#ff6600;border-bottom:2px solid #ff6600;padding-bottom:8px;">Image</h3>
                    <div style="margin-top:15px;text-align:center;">
                        <img src="${data.image}" alt="Identification Image" 
                             style="max-width:100%;max-height:400px;border:3px solid #ff6600;border-radius:8px;box-shadow:0 4px 8px rgba(0,0,0,0.1);">
                    </div>
                </div>
            `;
        }

        // Top Suggestions
        if (data.response_payload && data.response_payload.result && 
            data.response_payload.result.classification && 
            data.response_payload.result.classification.suggestions) {
            
            const suggestions = data.response_payload.result.classification.suggestions.slice(0, 5);
            
            html += `
                <div class="detail-section" style="margin-bottom:25px;">
                    <h3 style="color:#ff6600;border-bottom:2px solid #ff6600;padding-bottom:8px;">Top Identifications</h3>
                    <div style="margin-top:15px;">
            `;

            suggestions.forEach((suggestion, index) => {
                const probability = (suggestion.probability * 100).toFixed(2);
                const confidence = probability > 80 ? 'high' : probability > 50 ? 'medium' : 'low';
                const color = confidence === 'high' ? '#4CAF50' : confidence === 'medium' ? '#FFA500' : '#FF5722';
                
                html += `
                    <div style="background:#f8f9fa;padding:15px;margin:10px 0;border-left:4px solid ${color};border-radius:4px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div style="flex:1;">
                                <strong style="font-size:16px;color:#333;">${index + 1}. ${suggestion.name || 'Unknown'}</strong>
                                ${suggestion.details && suggestion.details.common_names && suggestion.details.common_names.length > 0 ? 
                                    `<br><em style="color:#666;font-size:14px;">${suggestion.details.common_names[0]}</em>` : ''}
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:24px;font-weight:bold;color:${color};">${probability}%</div>
                                <div style="font-size:12px;color:#666;text-transform:uppercase;">${confidence} Confidence</div>
                            </div>
                        </div>
                        ${suggestion.details && suggestion.details.description ? 
                            `<div style="margin-top:10px;padding-top:10px;border-top:1px solid #dee2e6;color:#555;font-size:14px;">
                                ${truncateText(suggestion.details.description.value, 200)}
                            </div>` : ''}
                    </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
        }

        // Request Payload
        if (data.request_payload) {
            html += `
                <div class="detail-section" style="margin-bottom:25px;">
                    <h3 style="color:#ff6600;border-bottom:2px solid #ff6600;padding-bottom:8px;">Request Payload</h3>
                    <div class="json-response-container" style="margin-top:15px;">
                        <pre style="margin:0;white-space:pre-wrap;word-wrap:break-word;">${JSON.stringify(data.request_payload, null, 2)}</pre>
                    </div>
                </div>
            `;
        }

        // Full Response
        if (data.response_payload) {
            html += `
                <div class="detail-section" style="margin-bottom:25px;">
                    <h3 style="color:#ff6600;border-bottom:2px solid #ff6600;padding-bottom:8px;">Full API Response</h3>
                    <div class="json-response-container" style="margin-top:15px;">
                        <pre style="margin:0;white-space:pre-wrap;word-wrap:break-word;">${JSON.stringify(data.response_payload, null, 2)}</pre>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    /**
     * Get HTML for status badge
     * @param {string} status - The status value
     * @returns {string} HTML badge
     */
    function getStatusBadge(status) {
        const statusMap = {
            'success': { class: 'status-success', icon: '✓', text: 'Success' },
            'error': { class: 'status-error', icon: '✗', text: 'Error' },
            'pending': { class: 'status-pending', icon: '⏳', text: 'Pending' }
        };
        
        const statusInfo = statusMap[status] || { class: 'status-pending', icon: '?', text: status };
        
        return `<span class="${statusInfo.class}">${statusInfo.icon} ${statusInfo.text}</span>`;
    }

    /**
     * Format date to readable string
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        
        const date = new Date(dateString);
        const options = { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
        };
        
        return date.toLocaleDateString('en-US', options);
    }

    /**
     * Truncate text to specified length
     * @param {string} text - Text to truncate
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated text
     */
    function truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text || '';
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Copy JSON to clipboard
     * @param {string} elementId - ID of element containing JSON
     */
    window.copyKindwiseJSON = function(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const text = element.textContent;
        
        navigator.clipboard.writeText(text).then(() => {
            alert('JSON copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    };

})();
