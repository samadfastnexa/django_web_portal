# from django.contrib import admin
# from .models import UserSetting

# @admin.register(UserSetting)
# class UserSettingAdmin(admin.ModelAdmin):
#     list_display = ['slug', 'user', 'type', 'color_theme', 'dark_mode', 'language', 'radius_km']
#     list_filter = ['user', 'language', 'dark_mode']
#     search_fields = ['slug', 'user__username', 'language']
#     ordering = ['slug']

#     def type(self, obj):
#         return 'global' if obj.user is None else 'user'
#     type.short_description = 'Setting Type'

from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from .models import Setting
import json


# # ✅ Custom Widget for dynamic key-value JSON input
# class JSONKeyValueWidget(forms.Widget):
#     def render(self, name, value, attrs=None, renderer=None):
#         if not value:
#             value = {}
#         elif isinstance(value, str):
#             try:
#                 value = json.loads(value)
#             except json.JSONDecodeError:
#                 value = {}

#         html = '<div id="json-fields">'
#         for k, v in value.items():
#             html += f'<div><input type="text" name="{name}_key" value="{k}"> : '
#             html += f'<input type="text" name="{name}_value" value="{v}"> '
#             html += '<button type="button" class="remove">Remove</button></div>'
#         html += '</div><button type="button" id="add">Add</button>'
#         html += f'''
#         <script>
#         document.getElementById("add").onclick = function() {{
#             const container = document.getElementById("json-fields");
#             const div = document.createElement("div");
#             div.innerHTML = '<input type="text" name="{name}_key"> : <input type="text" name="{name}_value"> <button type="button" class="remove">Remove</button>';
#             container.appendChild(div);
#             div.querySelector(".remove").onclick = function() {{ div.remove(); }};
#         }};
#         document.querySelectorAll(".remove").forEach(btn => {{
#             btn.onclick = function() {{ btn.parentElement.remove(); }};
#         }});
#         </script>
#         '''
#         return mark_safe(html)

#     def value_from_datadict(self, data, files, name):
#         keys = data.getlist(f'{name}_key')
#         values = data.getlist(f'{name}_value')

#         result = {}
#         for key, value in zip(keys, values):
#             value = value.strip().lower()
#             if value in ['true', 'false']:
#                 parsed_value = value == 'true'
#             else:
#                 try:
#                     parsed_value = int(value)
#                 except ValueError:
#                     try:
#                         parsed_value = float(value)
#                     except ValueError:
#                         parsed_value = value  # string fallback
#             result[key] = parsed_value

#         return json.dumps(result)  # ✅ Save as JSON string


# # ✅ Custom form with validation
# class SettingForm(forms.ModelForm):
#     class Meta:
#         model = Setting
#         fields = '__all__'
#         widgets = {
#             'value': JSONKeyValueWidget()
#         }

#     def clean_value(self):
#         value = self.cleaned_data.get('value')
#         if isinstance(value, str):
#             try:
#                 value = json.loads(value)
#             except json.JSONDecodeError:
#                 raise forms.ValidationError("Value must be a valid JSON dictionary.")
#         if not isinstance(value, dict):
#             raise forms.ValidationError("Value must be a key-value dictionary.")
#         return json.dumps(value)


# # ✅ Admin registration
# @admin.register(Setting)
# class SettingAdmin(admin.ModelAdmin):
#     form = SettingForm
#     list_display = ('slug', 'user')
#     search_fields = ('slug', 'user__username')


    
from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
import json
from .models import Setting

# ✅ Step 1: Custom Widget
class JSONKeyValueWidget(forms.Widget):
    template_name = None  # Use custom render() method instead of template
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        final_attrs = self.build_attrs(attrs, {'type': 'hidden'})
        
        # Debug: Print what we're receiving
        print(f"DEBUG JSONKeyValueWidget - name: {name}, value type: {type(value)}, value: {value}")
        
        # Normalize value to dict
        if not value:
            value = {}
        elif isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                print(f"DEBUG: Failed to parse JSON string: {value}")
                value = {}
        
        # Ensure value is a dict
        if not isinstance(value, dict):
            print(f"DEBUG: Converting non-dict value to empty dict. Was: {type(value)}")
            value = {}

        print(f"DEBUG: Final normalized value: {value}")

        # Generate unique ID for this widget instance
        widget_id = final_attrs.get('id', name.replace('-', '_'))
        
        # Build HTML
        html = f'<div style="border: 1px solid #ccc; padding: 15px; background: #f9f9f9; border-radius: 5px;">'
        html += f'<h4 style="margin-top: 0;">Key-Value Pairs</h4>'
        html += f'<div id="json-fields-{widget_id}" class="json-key-value-widget" style="margin: 10px 0;">'

        # Render existing key-value pairs
        if value:
            for i, (k, v) in enumerate(value.items()):
                # Escape HTML entities in key and value
                k_escaped = str(k).replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                v_escaped = str(v).replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                
                html += f'''
                    <div class="key-value-pair" style="margin-bottom: 10px; display: flex; align-items: center;">
                        <input type="text" name="{name}_key_{i}" value="{k_escaped}" placeholder="Key" style="width: 200px; padding: 5px; margin-right: 10px;"> 
                        <span style="margin-right: 10px;">:</span>
                        <input type="text" name="{name}_value_{i}" value="{v_escaped}" placeholder="Value" style="width: 300px; padding: 5px; margin-right: 10px;">
                        <button type="button" class="remove-btn" style="padding: 5px 10px; cursor: pointer; background: #dc3545; color: white; border: none; border-radius: 3px;">Remove</button>
                    </div>
                '''
        else:
            html += '<p style="color: #666; font-style: italic;">No key-value pairs yet. Click "Add" to create one.</p>'
        
        html += f'</div><button type="button" id="add-btn-{widget_id}" style="margin-top: 10px; padding: 8px 15px; cursor: pointer; background: #28a745; color: white; border: none; border-radius: 3px;">Add Key-Value Pair</button>'
        html += '</div>'

        # JavaScript for dynamic add/remove
        html += f'''
        <script>
        (function() {{
            let count = {len(value) if value else 0};
            const widgetId = "{widget_id}";
            const container = document.getElementById("json-fields-" + widgetId);
            const addBtn = document.getElementById("add-btn-" + widgetId);
            
            console.log("JSONKeyValueWidget initialized with", count, "items");
            
            if (!addBtn) {{
                console.error("Add button not found for widget:", widgetId);
                return;
            }}
            
            if (!container) {{
                console.error("Container not found for widget:", widgetId);
                return;
            }}
            
            // Add button handler
            addBtn.onclick = function(e) {{
                e.preventDefault();
                console.log("Adding new key-value pair, count:", count);
                
                const div = document.createElement("div");
                div.className = "key-value-pair";
                div.style.marginBottom = "10px";
                div.style.display = "flex";
                div.style.alignItems = "center";
                div.innerHTML = `
                    <input type="text" name="{name}_key_${{count}}" placeholder="Key" style="width: 200px; padding: 5px; margin-right: 10px;"> 
                    <span style="margin-right: 10px;">:</span>
                    <input type="text" name="{name}_value_${{count}}" placeholder="Value" style="width: 300px; padding: 5px; margin-right: 10px;">
                    <button type="button" class="remove-btn" style="padding: 5px 10px; cursor: pointer; background: #dc3545; color: white; border: none; border-radius: 3px;">Remove</button>
                `;
                
                // Remove the "no pairs" message if it exists
                const noDataMsg = container.querySelector('p');
                if (noDataMsg) {{
                    noDataMsg.remove();
                }}
                
                container.appendChild(div);
                
                // Add remove handler for new row
                const removeBtn = div.querySelector(".remove-btn");
                if (removeBtn) {{
                    removeBtn.onclick = function(e) {{ 
                        e.preventDefault();
                        console.log("Removing row");
                        div.remove(); 
                    }};
                }}
                
                count++;
            }};
            
            // Remove button handlers for existing rows
            const removeBtns = container.querySelectorAll(".remove-btn");
            console.log("Found", removeBtns.length, "existing remove buttons");
            removeBtns.forEach(btn => {{
                btn.onclick = function(e) {{ 
                    e.preventDefault();
                    console.log("Removing existing row");
                    btn.closest('.key-value-pair').remove(); 
                }};
            }});
        }})();
        </script>
        '''
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        result = {}
        i = 0
        
        # Collect all key-value pairs
        while True:
            key = data.get(f'{name}_key_{i}')
            value = data.get(f'{name}_value_{i}')
            
            # Stop when no more pairs found
            if key is None and value is None:
                break
            
            # Only add if key is not empty
            if key and key.strip():
                val = value.strip() if value else ''
                val_lower = val.lower()
                
                # Type conversion
                if val_lower in ['true', 'false']:
                    parsed_value = val_lower == 'true'
                elif val_lower == 'null' or val_lower == 'none':
                    parsed_value = None
                else:
                    try:
                        parsed_value = int(val)
                    except ValueError:
                        try:
                            parsed_value = float(val)
                        except ValueError:
                            parsed_value = val
                
                result[key.strip()] = parsed_value
            
            i += 1
        
        return result


# ✅ Step 2: Custom Form
class SettingForm(forms.ModelForm):
    class Meta:
        model = Setting
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Force our custom widget on the value field
        self.fields['value'].widget = JSONKeyValueWidget()
        self.fields['value'].required = False
        self.fields['value'].help_text = "Enter key-value pairs for this setting"

    def clean_value(self):
        value = self.cleaned_data.get('value')
        # Return the dict as-is since JSONField handles it
        if isinstance(value, (dict, list, str, int, float, bool, type(None))):
            return value
        raise forms.ValidationError("Value must be a valid JSON type.")


# ✅ Step 3: Admin Registration
@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    form = SettingForm
    list_display = ('slug', 'user', 'created_at', 'updated_at', 'is_active')
    search_fields = ('slug', 'user__username')
    list_filter = ('is_active', 'created_at', 'updated_at')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # For simple string values (like SAP_COMPANY_DB), use TextInput
        if obj and obj.slug in ('SAP_COMPANY_DB',):
            form.base_fields['value'].widget = forms.TextInput(attrs={'size': '60'})
        else:
            # For all other settings, ensure our custom widget is used
            form.base_fields['value'].widget = JSONKeyValueWidget()
        return form
