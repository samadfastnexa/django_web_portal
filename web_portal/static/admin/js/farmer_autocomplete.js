(function() {
    'use strict';
    
    function initFarmerAutocomplete() {
        var $ = window.django ? django.jQuery : window.jQuery;
        
        if (!$) {
            console.error('jQuery not found!');
            return;
        }
        
        console.log('Farmer autocomplete script loaded');
        
        // Function to auto-populate farmer details
        function populateFarmerDetails(farmerId, $row) {
            if (!farmerId) {
                console.log('No farmer ID provided');
                return;
            }
            
            console.log('Fetching farmer details for ID:', farmerId);
            
            // Get CSRF token
            function getCookie(name) {
                var cookieValue = null;
                if (document.cookie && document.cookie !== '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
                        var cookie = cookies[i].trim();
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }
            
            var csrftoken = getCookie('csrftoken');
            
            // Fetch farmer details from admin change page
            $.ajax({
                url: '/admin/farmers/farmer/' + farmerId + '/change/',
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrftoken
                },
                success: function(html) {
                    console.log('Received farmer admin page');
                    
                    // Parse the HTML to extract farmer data
                    var $html = $(html);
                    var firstName = $html.find('#id_first_name').val() || '';
                    var lastName = $html.find('#id_last_name').val() || '';
                    var fullName = (firstName + ' ' + lastName).trim();
                    var primaryPhone = $html.find('#id_primary_phone').val() || '';
                    var totalLand = $html.find('#id_total_land_area').val() || '';
                    
                    console.log('Extracted - Name:', fullName, 'Phone:', primaryPhone, 'Land:', totalLand);
                    
                    // Find inputs in the current row
                    var $nameInput = $row.find('input[name*="farmer_name"], input[id*="farmer_name"]').not('[name*="farmer"][name$="farmer"]');
                    var $contactInput = $row.find('input[name*="contact_number"], input[id*="contact_number"]');
                    var $acreageInput = $row.find('input[name*="acreage"], input[id*="acreage"]');
                    
                    console.log('Found inputs - name:', $nameInput.length, 'contact:', $contactInput.length, 'acreage:', $acreageInput.length);
                    
                    // Auto-fill farmer_name
                    if ($nameInput.length && fullName) {
                        $nameInput.val(fullName);
                        console.log('Set farmer_name to:', fullName);
                    }
                    
                    // Auto-fill contact_number
                    if ($contactInput.length && primaryPhone) {
                        $contactInput.val(primaryPhone);
                        console.log('Set contact_number to:', primaryPhone);
                    }
                    
                    // Auto-fill acreage if available
                    if ($acreageInput.length && totalLand) {
                        var currentVal = $acreageInput.val();
                        if (!currentVal || currentVal === '0' || currentVal === '0.0' || currentVal === '0.00') {
                            $acreageInput.val(totalLand);
                            console.log('Set acreage to:', totalLand);
                        }
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching farmer details:', error);
                    console.error('Status:', status);
                    console.error('Response:', xhr.responseText);
                }
            });
        }
        
        // Handle Django autocomplete widget selection
        function handleAutocompleteChange(e) {
            var $select = $(e.target);
            var farmerId = $select.val();
            var $row = $select.closest('tr, .inline-related');
            
            console.log('========================================');
            console.log('Autocomplete event triggered!');
            console.log('Event type:', e.type);
            console.log('Target:', $select.attr('name'), $select.attr('id'));
            console.log('Farmer ID:', farmerId);
            console.log('Row found:', $row.length);
            console.log('========================================');
            
            if (farmerId && $row.length) {
                populateFarmerDetails(farmerId, $row);
            }
        }
        
        // Attach event handlers
        function attachHandlers() {
            // Find all farmer select/autocomplete fields
            var $farmerFields = $('select[name*="farmer"]:not([name*="farmer_name"]), input[name*="farmer"]:not([name*="farmer_name"])');
            
            console.log('Found', $farmerFields.length, 'farmer fields');
            
            $farmerFields.each(function(index) {
                var $field = $(this);
                var fieldName = $field.attr('name');
                var fieldId = $field.attr('id');
                
                console.log('Field', index + 1, '- Name:', fieldName, 'ID:', fieldId, 'Type:', $field.prop('tagName'));
                
                // Remove existing handlers
                $field.off('change.farmerAutocomplete');
                
                // Attach change handler
                $field.on('change.farmerAutocomplete', handleAutocompleteChange);
                
                // Check if field already has a value
                var currentVal = $field.val();
                if (currentVal) {
                    console.log('Field already has value:', currentVal);
                }
            });
        }
        
        // Initialize on page load
        $(document).ready(function() {
            console.log('Document ready - initializing farmer autocomplete');
            
            // Wait a bit for Django admin to finish loading
            setTimeout(function() {
                console.log('Delayed initialization (500ms)');
                attachHandlers();
            }, 500);
        });
        
        // Re-attach when new inline forms are added
        $(document).on('formset:added', function(event, $row, formsetName) {
            console.log('New formset row added:', formsetName);
            setTimeout(function() {
                var $farmerField = $row.find('select[name*="farmer"]:not([name*="farmer_name"]), input[name*="farmer"]:not([name*="farmer_name"])');
                if ($farmerField.length) {
                    console.log('Attaching handler to new row field:', $farmerField.attr('name'));
                    $farmerField.on('change.farmerAutocomplete', handleAutocompleteChange);
                }
            }, 100);
        });
    }
    
    // Initialize when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFarmerAutocomplete);
    } else {
        initFarmerAutocomplete();
    }
})();
