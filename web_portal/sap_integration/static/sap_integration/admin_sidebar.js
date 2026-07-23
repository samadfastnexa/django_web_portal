/*
 * Admin sidebar: collapsible rail + expandable menu groups.
 *
 * Both states persist in localStorage:
 *   adminSidebarCollapsed -> "1" | "0"
 *   adminSidebarOpenGroups -> JSON array of group keys
 *
 * The group containing the current page is always opened, so navigating never
 * hides where you are.
 */
(function () {
  'use strict';

  var COLLAPSE_KEY = 'adminSidebarCollapsed';
  var GROUPS_KEY = 'adminSidebarOpenGroups';

  function ready(fn) {
    if (document.readyState !== 'loading') { fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  function readOpenGroups() {
    try {
      var raw = window.localStorage.getItem(GROUPS_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) { return []; }
  }

  function writeOpenGroups(keys) {
    try { window.localStorage.setItem(GROUPS_KEY, JSON.stringify(keys)); }
    catch (e) { /* private mode - state just won't persist */ }
  }

  ready(function () {
    var sidebar = document.getElementById('nav-sidebar');
    if (!sidebar) { return; }

    /* ---------------- collapse / expand the whole rail ---------------- */
    var toggle = document.getElementById('sidebar-toggle');

    function applyCollapsed(collapsed) {
      document.body.classList.toggle('sidebar-collapsed', collapsed);
      if (toggle) {
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        var label = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
        toggle.setAttribute('aria-label', label);
        toggle.setAttribute('title', label);
      }
    }

    var startCollapsed = false;
    try { startCollapsed = window.localStorage.getItem(COLLAPSE_KEY) === '1'; }
    catch (e) { /* ignore */ }
    applyCollapsed(startCollapsed);

    if (toggle) {
      toggle.addEventListener('click', function () {
        var collapsed = !document.body.classList.contains('sidebar-collapsed');
        applyCollapsed(collapsed);
        try { window.localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0'); }
        catch (e) { /* ignore */ }
      });
    }

    /* ---------------- expandable groups ---------------- */
    var groups = Array.prototype.slice.call(sidebar.querySelectorAll('.nav-group'));
    var open = readOpenGroups();

    function keyOf(group) { return group.getAttribute('data-group') || ''; }

    function setOpen(group, isOpen, persist) {
      group.classList.toggle('is-open', isOpen);
      var header = group.querySelector('.nav-group-header');
      if (header) { header.setAttribute('aria-expanded', isOpen ? 'true' : 'false'); }

      var list = group.querySelector('.nav-group-items');
      if (list) {
        // Animate to the measured height, then release so nested changes fit.
        if (isOpen) {
          list.style.maxHeight = list.scrollHeight + 'px';
          window.setTimeout(function () {
            if (group.classList.contains('is-open')) { list.style.maxHeight = 'none'; }
          }, 220);
        } else {
          list.style.maxHeight = list.scrollHeight + 'px';
          void list.offsetHeight;               // force reflow so the transition runs
          list.style.maxHeight = '0px';
        }
      }

      if (persist === false) { return; }
      var key = keyOf(group);
      var idx = open.indexOf(key);
      if (isOpen && idx === -1) { open.push(key); }
      else if (!isOpen && idx > -1) { open.splice(idx, 1); }
      writeOpenGroups(open);
    }

    groups.forEach(function (group) {
      var header = group.querySelector('.nav-group-header');
      var hasActive = !!group.querySelector('.menu-item.is-active');
      // Restore saved state; always open the group holding the current page.
      var shouldOpen = hasActive || open.indexOf(keyOf(group)) > -1;

      // Apply the initial state without animating on first paint.
      group.classList.add('no-anim');
      setOpen(group, shouldOpen, hasActive ? true : false);
      window.setTimeout(function () { group.classList.remove('no-anim'); }, 60);

      if (header) {
        header.addEventListener('click', function () {
          // In the collapsed rail the children are hidden, so a click would
          // appear to do nothing. Expand the rail first, then open the group.
          if (document.body.classList.contains('sidebar-collapsed')) {
            applyCollapsed(false);
            try { window.localStorage.setItem(COLLAPSE_KEY, '0'); }
            catch (e) { /* ignore */ }
            setOpen(group, true);
            return;
          }
          setOpen(group, !group.classList.contains('is-open'));
        });
      }
    });

    /* ---------------- filter box ---------------- */
    var filter = document.getElementById('nav-filter');
    var empty = sidebar.querySelector('.sidebar-empty');
    var searchField = sidebar.querySelector('.search-field');
    var clearBtn = sidebar.querySelector('.search-clear');
    if (filter) {
      filter.addEventListener('input', function () {
        var q = filter.value.trim().toLowerCase();
        var anyVisible = false;
        if (searchField) { searchField.classList.toggle('has-value', filter.value.length > 0); }

        // Plain (non-group) links.
        Array.prototype.forEach.call(
          sidebar.querySelectorAll('#nav-sidebar-models > .menu-item'),
          function (li) {
            var hit = !q || li.textContent.toLowerCase().indexOf(q) > -1;
            li.hidden = !hit;
            if (hit) { anyVisible = true; }
          }
        );

        groups.forEach(function (group) {
          var header = group.querySelector('.nav-group-header');
          var groupName = header ? header.textContent.toLowerCase() : '';
          var groupHit = !!q && groupName.indexOf(q) > -1;
          var childHit = false;

          Array.prototype.forEach.call(
            group.querySelectorAll('.nav-group-items .menu-item'),
            function (li) {
              var hit = !q || groupHit || li.textContent.toLowerCase().indexOf(q) > -1;
              li.hidden = !hit;
              if (hit) { childHit = true; }
            }
          );

          var show = !q || groupHit || childHit;
          group.hidden = !show;
          if (show) { anyVisible = true; }

          if (q && show) {
            // Reveal matches while searching, without persisting that.
            group.classList.add('is-open');
            var list = group.querySelector('.nav-group-items');
            if (list) { list.style.maxHeight = 'none'; }
          } else if (!q) {
            var stillOpen = open.indexOf(keyOf(group)) > -1 ||
                            !!group.querySelector('.menu-item.is-active');
            setOpen(group, stillOpen, false);
          }
        });

        if (empty) { empty.hidden = anyVisible; }
      });

      // Clear button resets the filter and re-runs it.
      if (clearBtn) {
        var doClear = function () {
          filter.value = '';
          filter.dispatchEvent(new Event('input'));
          filter.focus();
        };
        clearBtn.addEventListener('click', doClear);
        clearBtn.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); doClear(); }
        });
      }
    }
  });
})();
