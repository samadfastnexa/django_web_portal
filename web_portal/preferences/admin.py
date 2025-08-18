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
    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(attrs)
        if not value:
            value = {}
        elif isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = {}
        elif not isinstance(value, dict):
            value = {}

        html = '<div id="json-fields">'

        for i, (k, v) in enumerate(value.items()):
            html += f'''
                <div>
                    <input type="text" name="{name}_key_{i}" value="{k}" placeholder="Key"> :
                    <input type="text" name="{name}_value_{i}" value="{v}" placeholder="Value">
                    <button type="button" class="remove">Remove</button>
                </div>
            '''

        html += '</div><button type="button" id="add">Add</button>'

        html += f'''
        <script>
        let count = {len(value)};
        document.getElementById("add").onclick = function() {{
            const container = document.getElementById("json-fields");
            const div = document.createElement("div");
            div.innerHTML = `<input type="text" name="{name}_key_${{count}}" placeholder="Key"> :
                             <input type="text" name="{name}_value_${{count}}" placeholder="Value">
                             <button type="button" class="remove">Remove</button>`;
            container.appendChild(div);
            div.querySelector(".remove").onclick = function() {{ div.remove(); }};
            count++;
        }};
        document.querySelectorAll(".remove").forEach(btn => {{
            btn.onclick = function() {{ btn.parentElement.remove(); }};
        }});
        </script>
        '''
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        result = {}
        i = 0
        while True:
            key = data.get(f'{name}_key_{i}')
            value = data.get(f'{name}_value_{i}')
            if key is None and value is None:
                break
            if key:
                val = value.strip() if value else ''
                val_lower = val.lower()
                if val_lower in ['true', 'false']:
                    parsed_value = val_lower == 'true'
                else:
                    try:
                        parsed_value = int(val)
                    except ValueError:
                        try:
                            parsed_value = float(val)
                        except ValueError:
                            parsed_value = val
                result[key] = parsed_value
            i += 1
        return result


# ✅ Step 2: Custom Form
class SettingForm(forms.ModelForm):
    class Meta:
        model = Setting
        fields = '__all__'
        widgets = {
            'value': JSONKeyValueWidget()
        }

    def clean_value(self):
        value = self.cleaned_data.get('value')
        if not isinstance(value, dict):
            raise forms.ValidationError("Value must be a valid key-value dictionary.")
        return value


# ✅ Step 3: Admin Registration
@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    form = SettingForm
    list_display = ('slug', 'user', 'created_at', 'updated_at', 'is_active')
    search_fields = ('slug', 'user__username')
    list_filter = ('is_active', 'created_at', 'updated_at')