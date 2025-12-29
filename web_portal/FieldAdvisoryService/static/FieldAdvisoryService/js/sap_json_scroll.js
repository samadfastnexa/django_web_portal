/**
 * Force SAP Response JSON textarea to have visible scrollbars
 * Uses a wrapper div approach for guaranteed scrollbar visibility
 */

(function() {
    'use strict';
    
    function wrapJsonFieldWithScroll() {
        const jsonField = document.getElementById('id_sap_response_json');
        
        if (!jsonField) {
            console.log('SAP JSON field not found yet...');
            return false;
        }
        
        // Check if already wrapped
        if (jsonField.parentElement.classList.contains('sap-json-scroll-wrapper')) {
            console.log('Already wrapped, skipping...');
            return true;
        }
        
        console.log('Wrapping SAP JSON field with scrollable container...');
        
        // Create wrapper div
        const wrapper = document.createElement('div');
        wrapper.className = 'sap-json-scroll-wrapper';
        wrapper.style.cssText = `
            width: 100% !important;
            height: 400px !important;
            overflow: scroll !important;
            overflow-y: scroll !important;
            overflow-x: scroll !important;
            border: 3px solid #ff6600 !important;
            border-radius: 6px !important;
            background: #f8f9fa !important;
            position: relative !important;
            display: block !important;
            box-sizing: border-box !important;
        `;
        
        // Style the textarea
        jsonField.style.cssText = `
            width: 100% !important;
            min-height: 400px !important;
            height: auto !important;
            border: none !important;
            background: transparent !important;
            font-family: Consolas, Monaco, "Courier New", monospace !important;
            font-size: 13px !important;
            line-height: 1.6 !important;
            padding: 12px !important;
            white-space: pre !important;
            word-wrap: normal !important;
            resize: none !important;
            display: block !important;
            box-sizing: border-box !important;
            color: #2c3e50 !important;
            overflow: visible !important;
        `;
        
        // Insert wrapper before textarea
        jsonField.parentNode.insertBefore(wrapper, jsonField);
        
        // Move textarea into wrapper
        wrapper.appendChild(jsonField);
        
        // Add custom scrollbar styles
        const styleId = 'sap-json-scrollbar-force';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                .sap-json-scroll-wrapper::-webkit-scrollbar {
                    width: 16px !important;
                    height: 16px !important;
                    display: block !important;
                }
                .sap-json-scroll-wrapper::-webkit-scrollbar-track {
                    background: #e0e0e0 !important;
                }
                .sap-json-scroll-wrapper::-webkit-scrollbar-thumb {
                    background: #ff6600 !important;
                    border: 3px solid #e0e0e0 !important;
                }
                .sap-json-scroll-wrapper::-webkit-scrollbar-thumb:hover {
                    background: #cc5200 !important;
                }
                .sap-json-scroll-wrapper {
                    scrollbar-width: auto !important;
                    scrollbar-color: #ff6600 #e0e0e0 !important;
                }
            `;
            document.head.appendChild(style);
        }
        
        console.log('✓ SAP JSON field wrapped successfully!');
        console.log('Wrapper size:', wrapper.offsetWidth + 'x' + wrapper.offsetHeight);
        console.log('Textarea scroll height:', jsonField.scrollHeight);
        
        return true;
    }
    
    // Try multiple times with increasing delays
    const attempts = [0, 100, 300, 500, 1000, 2000];
    attempts.forEach(delay => {
        setTimeout(wrapJsonFieldWithScroll, delay);
    });
    
    // Also try on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wrapJsonFieldWithScroll);
    }
    
    // Watch for the field to appear (for dynamic content)
    if (window.MutationObserver) {
        const observer = new MutationObserver(function() {
            if (wrapJsonFieldWithScroll()) {
                observer.disconnect();
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
})();
