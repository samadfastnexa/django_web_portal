/* Company Admin Branding JS
   - Key-value editor for extra_settings (single JSON field for all theme settings)
   - Inline color pickers for any hex-value entries
   - Live theme preview card reads primary_color / secondary_color from the JSON
   - Logo file preview
*/
(function () {
    'use strict';

    function isValidHex(hex) {
        return /^#[0-9A-Fa-f]{6}$/.test(hex);
    }

    // ── Parse / write helpers ──────────────────────────────────────────────────

    function readJSON(textarea) {
        var raw = (textarea.value || '').trim();
        if (!raw) return {};
        try {
            var parsed = JSON.parse(raw);
            return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : {};
        } catch (e) {
            return {};
        }
    }

    function writeJSON(textarea, data) {
        textarea.value = Object.keys(data).length ? JSON.stringify(data, null, 2) : '';
    }

    // ── Live theme preview ────────────────────────────────────────────────────

    function updatePreview(textarea) {
        var data = readJSON(textarea);
        var primary   = isValidHex(data.primary_color)   ? data.primary_color   : '#3B82F6';
        var secondary = isValidHex(data.secondary_color) ? data.secondary_color : '#10B981';
        var nameInput = document.querySelector('#id_Company_name');
        var companyName = nameInput ? (nameInput.value || 'Company Name') : 'Company Name';

        var card = document.getElementById('company-theme-preview-card');
        if (!card) {
            card = document.createElement('div');
            card.id = 'company-theme-preview-card';
            card.className = 'company-theme-preview';
            card.innerHTML = [
                '<div class="preview-header" id="preview-header">',
                '  <span id="preview-company-name"></span>',
                '</div>',
                '<div class="preview-body">',
                '  Sample portal layout<br>',
                '  <span class="preview-btn" id="preview-btn">Action</span>',
                '</div>'
            ].join('');

            var target = textarea.closest('.form-row') || textarea.closest('p') || textarea.parentNode;
            if (target && target.parentNode) {
                target.parentNode.insertBefore(card, target.nextSibling);
            }
        }

        document.getElementById('preview-header').style.backgroundColor = primary;
        document.getElementById('preview-btn').style.backgroundColor = secondary;
        document.getElementById('preview-company-name').textContent = companyName;
    }

    // ── Logo preview ──────────────────────────────────────────────────────────

    function setupLogoPreview() {
        var logoField = document.querySelector('#id_logo');
        if (!logoField) return;

        var container = logoField.closest('.field-logo')
                     || logoField.closest('.form-row')
                     || logoField.parentNode;

        /* Append preview inside .field-box so it sits to the right via CSS flex */
        var fieldBox = container.querySelector('.field-box') || container;

        var wrap = document.createElement('div');
        wrap.className = 'company-logo-preview-wrap';
        wrap.id = 'logo-preview-wrap';
        wrap.innerHTML =
            '<span class="preview-label">Current Logo</span>' +
            '<img id="logo-preview-img" src="" alt="Logo preview" style="display:none">' +
            '<span class="logo-no-preview" id="logo-no-preview">No logo uploaded</span>';
        fieldBox.appendChild(wrap);

        /* Size hint — inserted after the <p class="file-upload"> */
        var fileUploadP = container.querySelector('.file-upload') || logoField.parentNode;
        var hint = document.createElement('p');
        hint.className = 'logo-size-hint';
        hint.innerHTML =
            'Recommended: <strong>200\u2009\u00d7\u200960\u2009px</strong> &nbsp;&middot;&nbsp; ' +
            'Max <strong>2\u2009MB</strong> &nbsp;&middot;&nbsp; ' +
            'Formats: JPG, PNG, SVG, WebP';
        fileUploadP.parentNode.insertBefore(hint, fileUploadP.nextSibling);

        /* Show existing logo */
        var currentLink = container.querySelector('a[href*="/media/"]')
                       || container.querySelector('.file-upload a')
                       || container.querySelector('p a[href]');
        if (currentLink) {
            var img = document.getElementById('logo-preview-img');
            img.src = currentLink.getAttribute('href');
            img.style.display = 'block';
            document.getElementById('logo-no-preview').style.display = 'none';
        }

        /* Preview newly selected file */
        logoField.addEventListener('change', function () {
            var file = logoField.files && logoField.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    var img = document.getElementById('logo-preview-img');
                    var noPreview = document.getElementById('logo-no-preview');
                    img.src = e.target.result;
                    img.style.display = 'block';
                    if (noPreview) noPreview.style.display = 'none';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // ── Key-value editor ──────────────────────────────────────────────────────

    function buildKeyValueEditor(textarea) {
        textarea.style.display = 'none';

        var data = readJSON(textarea);

        var editor = document.createElement('div');
        editor.className = 'kv-editor';

        /* ── header ── */
        var header = document.createElement('div');
        header.className = 'kv-editor-header';

        var title = document.createElement('span');
        title.className = 'kv-editor-title';
        title.textContent = 'Settings';

        var headerRight = document.createElement('div');
        headerRight.className = 'kv-header-right';

        var helpBtn = document.createElement('button');
        helpBtn.type = 'button';
        helpBtn.className = 'kv-help-btn';
        helpBtn.innerHTML = '&#9432; How to use';

        var addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'kv-add-btn';
        addBtn.textContent = '+ Add setting';

        headerRight.appendChild(helpBtn);
        headerRight.appendChild(addBtn);
        header.appendChild(title);
        header.appendChild(headerRight);
        editor.appendChild(header);

        /* ── collapsible help panel ── */
        var helpPanel = document.createElement('div');
        helpPanel.className = 'kv-help-panel';
        helpPanel.style.display = 'none';
        helpPanel.innerHTML = [
            '<div class="kv-help-body">',
            '  <p class="kv-help-intro">',
            '    Each setting is a <strong>key\u202F:\u202Fvalue</strong> pair saved as JSON. ',
            '    Click <strong>+ Add setting</strong> to add a new one. ',
            '    Keys from saved data are <strong>locked</strong> — only their values can be changed. ',
            '    Hex color values (e.g. <code>#3B82F6</code>) automatically show a color picker.',
            '  </p>',
            '  <table class="kv-help-table">',
            '    <thead>',
            '      <tr><th>Key</th><th>Example value</th><th>Used for</th></tr>',
            '    </thead>',
            '    <tbody>',
            '      <tr>',
            '        <td><code>primary_color</code></td>',
            '        <td><span class="kv-swatch" style="background:#3B82F6"></span><code>#3B82F6</code></td>',
            '        <td>Navbar, primary buttons</td>',
            '      </tr>',
            '      <tr>',
            '        <td><code>secondary_color</code></td>',
            '        <td><span class="kv-swatch" style="background:#10B981"></span><code>#10B981</code></td>',
            '        <td>Secondary buttons, links</td>',
            '      </tr>',
            '      <tr>',
            '        <td><code>accent_color</code></td>',
            '        <td><span class="kv-swatch" style="background:#F59E0B"></span><code>#F59E0B</code></td>',
            '        <td>Highlights, badges, tags</td>',
            '      </tr>',
            '      <tr>',
            '        <td><code>sidebar_bg</code></td>',
            '        <td><span class="kv-swatch" style="background:#1E293B"></span><code>#1E293B</code></td>',
            '        <td>Sidebar background color</td>',
            '      </tr>',
            '      <tr>',
            '        <td><code>sidebar_text</code></td>',
            '        <td><span class="kv-swatch" style="background:#F1F5F9"></span><code>#F1F5F9</code></td>',
            '        <td>Sidebar text color</td>',
            '      </tr>',
            '      <tr>',
            '        <td><code>font_family</code></td>',
            '        <td><code>Inter</code></td>',
            '        <td>UI font (must be loaded separately)</td>',
            '      </tr>',
            '      <tr>',
            '        <td><code>language</code></td>',
            '        <td><code>en</code></td>',
            '        <td>Default UI language code</td>',
            '      </tr>',
            '    </tbody>',
            '  </table>',
            '</div>'
        ].join('');
        editor.appendChild(helpPanel);

        helpBtn.addEventListener('click', function () {
            var open = helpPanel.style.display !== 'none';
            helpPanel.style.display = open ? 'none' : 'block';
            helpBtn.classList.toggle('kv-help-btn--active', !open);
        });

        /* ── rows ── */
        var rowsWrap = document.createElement('div');
        rowsWrap.className = 'kv-rows';
        editor.appendChild(rowsWrap);

        /* ── footer hint ── */
        var hint = document.createElement('p');
        hint.className = 'kv-hint';
        hint.innerHTML = 'Common: <code>primary_color</code>, <code>secondary_color</code>, <code>accent_color</code>, <code>font_family</code>';
        editor.appendChild(hint);

        textarea.parentNode.insertBefore(editor, textarea.nextSibling);

        /* sync all rows → hidden textarea → live preview */
        function sync() {
            var result = {};
            rowsWrap.querySelectorAll('.kv-row').forEach(function (row) {
                var k = row.querySelector('.kv-key').value.trim();
                var v = row.querySelector('.kv-val').value.trim();
                if (k) result[k] = v;
            });
            writeJSON(textarea, result);
            updatePreview(textarea);
        }

        /*
         * isNew = true  → user clicked "+ Add setting": key is editable
         * isNew = false → loaded from saved JSON: key is read-only (locked)
         */
        function makeRow(key, value, isNew) {
            var row = document.createElement('div');
            row.className = 'kv-row';

            /* lock icon — only for saved keys */
            var lockIcon = document.createElement('span');
            lockIcon.className = 'kv-lock-icon';
            lockIcon.title = 'Locked — key cannot be renamed';
            lockIcon.style.display = (!isNew && key) ? 'inline-flex' : 'none';

            var keyInput = document.createElement('input');
            keyInput.type = 'text';
            keyInput.className = 'kv-key' + ((!isNew && key) ? ' kv-key-locked' : '');
            keyInput.placeholder = 'key  (e.g. accent_color)';
            keyInput.value = key || '';
            if (!isNew && key) {
                keyInput.readOnly = true;
                keyInput.title = 'Key is locked — only the value can be edited.';
            }

            var sep = document.createElement('span');
            sep.className = 'kv-sep';
            sep.textContent = ':';

            var valInput = document.createElement('input');
            valInput.type = 'text';
            valInput.className = 'kv-val';
            valInput.placeholder = 'value';
            valInput.value = value || '';

            /* inline color picker for hex values */
            var picker = document.createElement('input');
            picker.type = 'color';
            picker.className = 'kv-color-picker';
            var initHex = valInput.value.trim();
            picker.value = isValidHex(initHex) ? initHex : '#ffffff';
            picker.style.display = isValidHex(initHex) ? 'inline-block' : 'none';

            picker.addEventListener('input', function () {
                valInput.value = picker.value.toUpperCase();
                sync();
            });
            valInput.addEventListener('input', function () {
                var v = valInput.value.trim();
                picker.value = isValidHex(v) ? v : picker.value;
                picker.style.display = isValidHex(v) ? 'inline-block' : 'none';
                sync();
            });
            keyInput.addEventListener('input', sync);

            row.appendChild(lockIcon);
            row.appendChild(keyInput);
            row.appendChild(sep);
            row.appendChild(valInput);
            row.appendChild(picker);
            return row;
        }

        /* populate from saved data — all locked */
        Object.keys(data).forEach(function (k) {
            rowsWrap.appendChild(makeRow(k, data[k], false));
        });

        /* "+ Add setting" creates a new editable row */
        addBtn.addEventListener('click', function () {
            var row = makeRow('', '', true);
            rowsWrap.appendChild(row);
            row.querySelector('.kv-key').focus();
            sync();
        });

        /* initial preview render */
        updatePreview(textarea);
    }

    // ── Init ──────────────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', function () {
        setupLogoPreview();

        var nameInput = document.querySelector('#id_Company_name');
        var extraTextarea = document.querySelector('#id_extra_settings');

        if (extraTextarea) {
            buildKeyValueEditor(extraTextarea);
            if (nameInput) nameInput.addEventListener('input', function () { updatePreview(extraTextarea); });
        }
    });
})();
