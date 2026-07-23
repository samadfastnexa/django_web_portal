/*
 * Type-ahead suggestions for the Django admin changelist search box.
 *
 * Attaches to #searchbar, figures out the current model from the body classes
 * Django already emits (app-<label> model-<name>), and asks the admin site's
 * search-suggest endpoint for matches. Suggestions come from the ModelAdmin's
 * own search_fields, so picking one always returns results.
 *
 * No dependencies - plain DOM, works with the admin's own jQuery absent.
 */
(function () {
  'use strict';

  var MIN_CHARS = 1;      // show suggestions from the first letter typed
  var DEBOUNCE_MS = 180;
  var ACTIVE_CLASS = 'is-active';

  function ready(fn) {
    if (document.readyState !== 'loading') { fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  // Django tags changelist pages with `app-<label>` and `model-<name>`.
  function pageModel() {
    var app = null, model = null;
    Array.prototype.forEach.call(document.body.classList, function (cls) {
      if (cls.indexOf('app-') === 0) { app = cls.slice(4); }
      else if (cls.indexOf('model-') === 0) { model = cls.slice(6); }
    });
    return { app: app, model: model };
  }

  /*
   * Wire type-ahead onto one input.
   *   opts.app / opts.model - which admin model to query
   *   opts.field            - optional: suggest distinct values of this field
   *                           (sidebar filter boxes); omitted for the main
   *                           search bar, which uses the admin's search_fields
   *   opts.submitOnPick     - submit the form after choosing
   */
  function attachSuggest(input, opts) {
    if (!input || input.dataset.suggestBound === '1') { return; }
    input.dataset.suggestBound = '1';

    var app = opts.app, model = opts.model;
    if (!app || !model) { return; }

    // Derive the admin root so this works whatever prefix admin is mounted on.
    var parts = window.location.pathname.split('/' + app + '/');
    var endpoint = (parts.length > 1 ? parts[0] : '/admin') + '/search-suggest/';

    var anchor = input.parentElement;
    if (!anchor) { return; }
    if (getComputedStyle(anchor).position === 'static') {
      anchor.style.position = 'relative';
    }

    var box = document.createElement('div');
    box.className = 'admin-suggest-box';
    box.setAttribute('role', 'listbox');
    box.hidden = true;
    anchor.appendChild(box);

    var items = [];
    var activeIndex = -1;
    var timer = null;
    var controller = null;
    var lastTerm = null;

    function close() {
      box.hidden = true;
      box.innerHTML = '';
      items = [];
      activeIndex = -1;
      input.setAttribute('aria-expanded', 'false');
    }

    function highlight(index) {
      items.forEach(function (el, i) {
        el.classList.toggle(ACTIVE_CLASS, i === index);
      });
      activeIndex = index;
    }

    function choose(value) {
      input.value = value;
      close();
      if (opts.submitOnPick !== false && input.form) { input.form.submit(); }
    }

    function render(values, term) {
      box.innerHTML = '';
      items = [];
      if (!values.length) { close(); return; }

      var lowerTerm = term.toLowerCase();
      values.forEach(function (value, i) {
        var row = document.createElement('div');
        row.className = 'admin-suggest-item';
        row.setAttribute('role', 'option');

        // Bold the matched substring; textContent everywhere so any
        // markup inside a record's label can never be executed.
        var at = value.toLowerCase().indexOf(lowerTerm);
        if (at === -1) {
          row.textContent = value;
        } else {
          row.appendChild(document.createTextNode(value.slice(0, at)));
          var strong = document.createElement('strong');
          strong.textContent = value.slice(at, at + term.length);
          row.appendChild(strong);
          row.appendChild(document.createTextNode(value.slice(at + term.length)));
        }

        row.addEventListener('mousedown', function (e) {
          e.preventDefault();          // keep focus; blur would close first
          choose(value);
        });
        row.addEventListener('mouseenter', function () { highlight(i); });

        box.appendChild(row);
        items.push(row);
      });

      box.style.width = input.offsetWidth + 'px';
      box.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      activeIndex = -1;
    }

    function fetchSuggestions(term) {
      if (controller) { controller.abort(); }
      controller = ('AbortController' in window) ? new AbortController() : null;

      var url = endpoint + '?app=' + encodeURIComponent(app) +
                '&model=' + encodeURIComponent(model) +
                '&q=' + encodeURIComponent(term) +
                (opts.field ? '&field=' + encodeURIComponent(opts.field) : '');

      fetch(url, {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: controller ? controller.signal : undefined
      })
        .then(function (r) { return r.ok ? r.json() : { results: [] }; })
        .then(function (data) {
          // Ignore a response that arrived after the user kept typing.
          if (input.value.trim() !== term) { return; }
          render(data.results || [], term);
        })
        .catch(function () { /* aborted or offline - stay silent */ });
    }

    input.setAttribute('autocomplete', 'off');
    input.setAttribute('aria-autocomplete', 'list');

    input.addEventListener('input', function () {
      var term = input.value.trim();
      if (timer) { clearTimeout(timer); }
      if (term.length < MIN_CHARS) { close(); lastTerm = null; return; }
      if (term === lastTerm) { return; }
      lastTerm = term;
      timer = setTimeout(function () { fetchSuggestions(term); }, DEBOUNCE_MS);
    });

    input.addEventListener('keydown', function (e) {
      if (box.hidden || !items.length) { return; }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        highlight((activeIndex + 1) % items.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        highlight((activeIndex - 1 + items.length) % items.length);
      } else if (e.key === 'Enter') {
        if (activeIndex >= 0) {
          e.preventDefault();
          choose(items[activeIndex].textContent);
        }
      } else if (e.key === 'Escape') {
        close();
      }
    });

    input.addEventListener('blur', function () {
      // Delay so a click on a suggestion still registers.
      setTimeout(close, 150);
    });

    document.addEventListener('click', function (e) {
      if (e.target !== input && !box.contains(e.target)) { close(); }
    });
  }

  ready(function () {
    var page = pageModel();

    // 1. The main changelist search box (uses the admin's search_fields).
    attachSuggest(document.getElementById('searchbar'), {
      app: page.app,
      model: page.model
    });

    // 2. Sidebar filter boxes that declared a field to suggest from.
    var boxes = document.querySelectorAll('input[data-suggest-field]');
    Array.prototype.forEach.call(boxes, function (el) {
      attachSuggest(el, {
        app: el.getAttribute('data-suggest-app') || page.app,
        model: el.getAttribute('data-suggest-model') || page.model,
        field: el.getAttribute('data-suggest-field')
      });
    });
  });
})();
