(function(){
  // Utility to find closest row for inline form
  function closestRow(el){
    while(el && el.tagName && el.tagName.toLowerCase() !== 'tr'){ el = el.parentElement; }
    return el;
  }
  function qsInRow(row, selector){ return row ? row.querySelector(selector) : null; }
  function setOptions(selectEl, options){
    if(!selectEl) return;
    var prev = selectEl.value;
    console.log('[POLICY] setOptions on', selectEl.name || 'select', 'with', options.length, 'options; previous value:', prev);
    while(selectEl.firstChild){ selectEl.removeChild(selectEl.firstChild); }
    options.forEach(function(opt){
      var o = document.createElement('option');
      o.value = opt.value;
      o.textContent = opt.label;
      selectEl.appendChild(o);
    });
    // restore previous selection if still present
    if(prev){
      selectEl.value = prev;
      if(selectEl.value !== prev){
        console.log('[POLICY] Previous value', prev, 'not found in options');
      } else {
        console.log('[POLICY] Previous value restored:', prev);
      }
    }
  }
  function fetchJSON(url){ return fetch(url, { credentials: 'same-origin' }).then(function(r){ return r.json(); }); }

  // Cache items per row for setting description/uom later
  var rowItemCache = new WeakMap();

  function getSelectedDB(){
    var sel = document.querySelector('#db-selector');
    return sel ? sel.value : '';
  }

  function onPolicyChange(e){
    var sel = e.target;
    var row = closestRow(sel);
    var selectedText = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : '';
    console.log('[POLICY] Policy changed to:', selectedText);
    // Extract DocEntry from label e.g. "(... DocEntry: 18)"
    var m = /DocEntry:\s*(\d+)/.exec(selectedText);
    var docEntry = m ? m[1] : '';
    console.log('[POLICY] Extracted DocEntry:', docEntry);
    var uPlInput = qsInRow(row, 'input[name$="u_pl"]');
    if(uPlInput) uPlInput.value = docEntry || '';

    var itemSelect = qsInRow(row, 'select.sap-item-lov');
    if(!docEntry || !itemSelect){ 
      console.log('[POLICY] Missing docEntry or itemSelect, skipping item load');
      return; 
    }

    // Load items for policy
    var db = getSelectedDB();
    var url = '/api/sap/policy-items-lov/?doc_entry=' + encodeURIComponent(docEntry);
    if(db){ url += '&database=' + encodeURIComponent(db); }
    console.log('[POLICY] Loading items from:', url);
    fetchJSON(url).then(function(resp){
      console.log('[POLICY] Items response:', resp);
      var items = (resp && resp.data) ? resp.data : [];
      console.log('[POLICY] Found', items.length, 'items in response');
      // Build options
      var opts = [{ value: '', label: '--- Select Item ---' }];
      var map = {};
      var validItemCount = 0;
      items.forEach(function(it){
        var code = it.ItemCode || it.ITEMCODE || '';
        var name = it.ItemName || '';
        var uom = it.unit_of_measure || it.UNIT_OF_MEASURE || it.SalUnitMsr || '';
        if(code){
          opts.push({ value: code, label: code + ' - ' + name });
          map[code] = { name: name, uom: uom };
          validItemCount++;
          console.log('[POLICY] Added item:', code, '-', name);
        }
      });
      
      // If no valid items found, show a message
      if(validItemCount === 0 && items.length > 0){
        opts = [{ value: '', label: '--- No Items in This Policy ---' }];
        console.log('[POLICY] Policy has no items configured');
      }
      
      // Cache per row
      rowItemCache.set(row, map);
      setOptions(itemSelect, opts);
      console.log('[POLICY] Item dropdown updated with', validItemCount, 'valid items (', opts.length, 'options total)');
      // Reset dependent fields
      var desc = qsInRow(row, 'input[name$="item_description"]');
      var mu = qsInRow(row, 'input[name$="measure_unit"]');
      var price = qsInRow(row, 'input[name$="unit_price"]');
      if(desc) desc.value = '';
      if(mu) mu.value = '';
      if(price) price.value = '';
    }).catch(function(err){ 
      console.error('[POLICY] Failed to load items:', err); 
    });
  }

  function onItemChange(e){
    var sel = e.target;
    var row = closestRow(sel);
    var code = sel.value;
    console.log('[ITEM] Item changed to:', code);
    var map = rowItemCache.get(row) || {};
    var info = map[code] || {};
    console.log('[ITEM] Item info:', info);
    var desc = qsInRow(row, 'input[name$="item_description"]');
    var mu = qsInRow(row, 'input[name$="measure_unit"]');
    if(desc) desc.value = info.name || '';
    if(mu) mu.value = info.uom || '';

    // Fetch price by policy + item
    var uPlInput = qsInRow(row, 'input[name$="u_pl"]');
    var docEntry = uPlInput ? (uPlInput.value || '') : '';
    console.log('[ITEM] Fetching price for DocEntry:', docEntry, 'ItemCode:', code);
    if(docEntry && code){
      var db = getSelectedDB();
      var url = '/api/sap/item-price/?doc_entry=' + encodeURIComponent(docEntry) + '&item_code=' + encodeURIComponent(code);
      if(db){ url += '&database=' + encodeURIComponent(db); }
      console.log('[ITEM] Price URL:', url);
      fetchJSON(url).then(function(resp){
        console.log('[ITEM] Price response:', resp);
        var price = qsInRow(row, 'input[name$="unit_price"]');
        var val = (resp && resp.data && resp.data.unit_price != null) ? resp.data.unit_price : '';
        console.log('[ITEM] Setting price to:', val);
        if(price) price.value = val;
      }).catch(function(err){ 
        console.error('[ITEM] Failed to fetch price:', err); 
      });
    }

    // Fetch warehouses for item
    var wSel = qsInRow(row, 'select.sap-warehouse-lov');
    if(wSel && code){
      var db = getSelectedDB();
      var wurl = '/api/sap/warehouse-for-item/?item_code=' + encodeURIComponent(code);
      if(db){ wurl += '&database=' + encodeURIComponent(db); }
      fetchJSON(wurl).then(function(resp){
        var rows = (resp && resp.data) ? resp.data : resp;
        var opts = [{ value: '', label: '--- Select Warehouse ---' }];
        (rows || []).forEach(function(w){
          var c = w.WhsCode || w.WarehouseCode || w.code || '';
          var n = w.WhsName || w.name || '';
          if(c) opts.push({ value: c, label: c + ' - ' + n });
        });
        setOptions(wSel, opts);
      }).catch(function(err){ console.warn('Warehouses fetch failed', err); });
    }
  }

  function bindRow(row){
    var policySel = qsInRow(row, 'select.sap-policy-lov');
    var itemSel = qsInRow(row, 'select.sap-item-lov');
    if(policySel && !policySel.__bound){ policySel.__bound = true; policySel.addEventListener('change', onPolicyChange); }
    if(itemSel && !itemSel.__bound){ itemSel.__bound = true; itemSel.addEventListener('change', onItemChange); }
  }

  function bindAll(){
    // Bind by row for tabular inlines
    document.querySelectorAll('tr.dynamic-salesorderline_set, tr.form-row').forEach(bindRow);
    // Also bind directly by selects in case row selector changes
    document.querySelectorAll('select.sap-policy-lov, select[name$="u_policy"]').forEach(function(sel){
      if(!sel.__bound){ sel.__bound = true; sel.addEventListener('change', onPolicyChange); }
    });
    document.querySelectorAll('select.sap-item-lov, select[name$="item_code"]').forEach(function(sel){
      if(!sel.__bound){ sel.__bound = true; sel.addEventListener('change', onItemChange); }
    });
  }

  // Load and populate policies for a selected customer across all line rows
  function loadPoliciesForCustomer(cardCode){
    if(!cardCode){ 
      console.log('[POLICY] No customer selected, clearing policies');
      return; 
    }
    console.log('[POLICY] Loading policies for customer:', cardCode);
    var db = getSelectedDB();
    var url = '/api/sap/customer-policies/?card_code=' + encodeURIComponent(cardCode);
    if(db){ url += '&database=' + encodeURIComponent(db); }
    console.log('[POLICY] Fetching from:', url);
    fetchJSON(url).then(function(resp){
      console.log('[POLICY] Response:', resp);
      var rows = (resp && resp.data) ? resp.data : [];
      console.log('[POLICY] Found', rows.length, 'policies');
      var opts = [{ value: '', label: '--- Select Policy ---' }];
      rows.forEach(function(r){
        var doc = r.policy_doc_entry || r.POLICY_DOC_ENTRY || r.DocEntry || '';
        var proj = r.project_code || r.PROJECT_CODE || r.U_proj || '';
        var name = r.project_name || r.PROJECT_NAME || r.PrjName || 'Policy';
        if(doc){
          var label = (name || 'Policy') + ' (DocEntry: ' + doc + ')';
          opts.push({ value: proj || doc, label: label });
          console.log('[POLICY] Added option:', label);
        }
      });
      // Update all policy selects
      console.log('[POLICY] Updating all policy dropdowns with', opts.length, 'options');
      document.querySelectorAll('select.sap-policy-lov, select[name$="u_policy"]').forEach(function(sel){
        var hadValue = !!sel.value;
        setOptions(sel, opts);
        // Reset related fields when policies are reloaded
        var row = closestRow(sel);
        var uPlInput = qsInRow(row, 'input[name$="u_pl"]');
        if(uPlInput) uPlInput.value = '';
        var itemSelect = qsInRow(row, 'select.sap-item-lov');
        if(itemSelect) setOptions(itemSelect, [{ value: '', label: '--- Select Item ---' }]);
        var desc = qsInRow(row, 'input[name$="item_description"]');
        var mu = qsInRow(row, 'input[name$="measure_unit"]');
        var price = qsInRow(row, 'input[name$="unit_price"]');
        if(desc) desc.value = '';
        if(mu) mu.value = '';
        if(price) price.value = '';
        // If a policy was already selected (e.g., editing existing line), trigger item load
        if(sel.value){
          console.log('[POLICY] Triggering item load for existing policy selection:', sel.value);
          onPolicyChange({ target: sel });
        } else if(hadValue && !sel.value){
          console.log('[POLICY] Previously selected policy no longer present; please reselect');
        }
      });
    }).catch(function(err){ 
      console.error('[POLICY] Failed to load policies:', err); 
    });
  }

  // Expose a hook for other scripts to trigger policy loading
  try { window.__loadPoliciesForCustomer = loadPoliciesForCustomer; } catch(e) {}

  // Listen for custom event dispatched by customer script
  document.addEventListener('customer-selected', function(ev){
    console.log('[POLICY] ✓ Received customer-selected event:', ev);
    try {
      var code = (ev && ev.detail && ev.detail.cardCode) ? ev.detail.cardCode : '';
      console.log('[POLICY] Extracted cardCode from event:', code);
      if(code){ 
        console.log('[POLICY] Calling loadPoliciesForCustomer with:', code);
        loadPoliciesForCustomer(code); 
      } else {
        console.log('[POLICY] No cardCode in event, skipping');
      }
    } catch(err) { console.error('[POLICY] customer-selected handler error', err); }
  });

  document.addEventListener('DOMContentLoaded', function(){
    console.log('[POLICY] Page loaded - checking for customer');
    bindAll();
    
    // Find customer from main form
    var custDropdown = document.querySelector('select.sap-customer-lov');
      console.log('[POLICY] Customer dropdown found?', custDropdown ? 'YES' : 'NO');
      if(custDropdown) console.log('[POLICY] Customer dropdown value:', custDropdown.value);
    if(custDropdown && custDropdown.value){
      console.log('[POLICY] Found customer on page load:', custDropdown.value);
        console.log('[POLICY] Will call loadPoliciesForCustomer after 200ms delay');
      setTimeout(function(){
          console.log('[POLICY] Delayed call to loadPoliciesForCustomer');
        loadPoliciesForCustomer(custDropdown.value);
      }, 200);
    }
  });

  // Also bind after adding new inline rows
  document.addEventListener('click', function(ev){
    if(ev.target && (ev.target.classList.contains('add-row') || ev.target.closest('.add-row'))){
      setTimeout(bindAll, 100);
    }
  });
})();
