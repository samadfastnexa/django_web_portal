(function(){
  function fetchJSON(url){ return fetch(url, { credentials: 'same-origin' }).then(function(r){ return r.json(); }); }
  function setValue(selector, value){ var el = document.querySelector(selector); if(el){ el.value = value || ''; } }
  function getSelectedDB(){
    var sel = document.querySelector('#db-selector');
    return sel ? sel.value : '';
  }
  function setChildCustomers(cardCode){
    var childSel = document.querySelector('select.sap-child-customer-lov');
    if(!childSel || !cardCode) return;
    var db = getSelectedDB();
    var url = '/api/field/api/child_customers/?father_card=' + encodeURIComponent(cardCode);
    if(db){ url += '&database=' + encodeURIComponent(db); }
    fetchJSON(url).then(function(resp){
      var children = (resp && resp.children) ? resp.children : [];
      while(childSel.firstChild){ childSel.removeChild(childSel.firstChild); }
      var def = document.createElement('option');
      def.value = '';
      def.textContent = children.length ? '--- Select Child Customer ---' : '--- No Child Customers ---';
      childSel.appendChild(def);
      children.forEach(function(c){
        var o = document.createElement('option');
        o.value = c.CardCode || '';
        o.textContent = (c.CardCode || '') + ' - ' + (c.CardName || '');
        childSel.appendChild(o);
      });
    }).catch(function(err){ console.warn('Child customers load failed', err); });
  }
  function onCustomerChange(){
    var sel = document.querySelector('select.sap-customer-lov');
    if(!sel) return;
    var code = sel.value || '';
    if(!code){
      // Clear fields if no customer selected
      setValue('input[name="card_name"]','');
      setValue('input[name="contact_person_code"]','');
      setValue('input[name="federal_tax_id"]','');
      setValue('input[name="pay_to_code"]','');
      setValue('textarea[name="address"]','');
      setChildCustomers('');
        console.log('[CUSTOMER] Dispatching customer-selected event with empty code');
      try { document.dispatchEvent(new CustomEvent('customer-selected', { detail: { cardCode: '' } })); } catch(e) {}
      return;
    }
      console.log('[CUSTOMER] onCustomerChange called with:', code);
    var db = getSelectedDB();
    var url = '/api/field/api/customer_details/?card_code=' + encodeURIComponent(code);
    if(db){ url += '&database=' + encodeURIComponent(db); }
    fetchJSON(url).then(function(data){
      if(data && !data.error){
        setValue('input[name="card_name"]', data.card_name);
        setValue('input[name="contact_person_code"]', data.contact_person_code);
        setValue('input[name="federal_tax_id"]', data.federal_tax_id);
        setValue('input[name="pay_to_code"]', data.pay_to_code);
        setValue('textarea[name="address"]', data.address);
        
        // CRITICAL: Remove readonly attribute to allow form submission
        ['card_name', 'contact_person_code', 'federal_tax_id', 'pay_to_code', 'address'].forEach(function(fieldName){
          var field = document.querySelector('input[name="' + fieldName + '"], textarea[name="' + fieldName + '"]');
          if(field){
            field.removeAttribute('readonly');
            field.removeAttribute('disabled');
            console.log('[CUSTOMER] Removed readonly from:', fieldName);
          }
        });
      }
      setChildCustomers(code);
      // Notify policy loader to refresh policies for this customer
      console.log('[CUSTOMER] About to dispatch customer-selected event with code:', code);
      try {
        var evt = new CustomEvent('customer-selected', { detail: { cardCode: code } });
        document.dispatchEvent(evt);
        console.log('[CUSTOMER] ✓ Event dispatched successfully');
      } catch(e) {
        console.error('[CUSTOMER] ✗ Event dispatch failed:', e);
      }
    }).catch(function(err){ 
      console.warn('Customer details fetch failed', err); 
      // Still dispatch event even if API fails
      console.log('[CUSTOMER] API failed but dispatching event anyway with code:', code);
      try { document.dispatchEvent(new CustomEvent('customer-selected', { detail: { cardCode: code } })); } catch(e) {}
    });
  }
  document.addEventListener('DOMContentLoaded', function(){
    var custSel = document.querySelector('select.sap-customer-lov');
      console.log('[CUSTOMER] DOMContentLoaded - customer dropdown found?', custSel ? 'YES' : 'NO');
    if(custSel){
      custSel.addEventListener('change', onCustomerChange);
      if(custSel.value){
        console.log('[CUSTOMER] Initial customer found on page load:', custSel.value);
        onCustomerChange();
        // Also fire the custom event so policies load immediately on page load
          console.log('[CUSTOMER] Initial customer dispatch of customer-selected event');
        try { document.dispatchEvent(new CustomEvent('customer-selected', { detail: { cardCode: custSel.value } })); } catch(e) {}
      } else {
        console.log('[CUSTOMER] No initial customer selected');
      }
    }
    
    // Fallback: if policies still haven't loaded after a delay, try again
    setTimeout(function(){
      var custSel = document.querySelector('select.sap-customer-lov');
      if(custSel && custSel.value){
          console.log('[CUSTOMER] Fallback check for customer:', custSel.value);
        var policySels = document.querySelectorAll('select.sap-policy-lov');
        if(policySels && policySels.length > 0){
          var hasOptions = false;
          policySels.forEach(function(sel){ if(sel.options.length > 1) hasOptions = true; });
          if(!hasOptions){
            console.log('[CUSTOMER] Fallback: No policies loaded, triggering now for:', custSel.value);
            try { document.dispatchEvent(new CustomEvent('customer-selected', { detail: { cardCode: custSel.value } })); } catch(e) {}
          }
        }
      }
    }, 500);
  });
})();
