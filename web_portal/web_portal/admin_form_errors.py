"""
Site-wide detailed validation errors for admin add/change forms.

Django's default when a form fails is a bare "Please correct the errors below."
at the top and a generic "This field is required." beside each input. That is
hard to act on here: several fieldsets are collapsed, and inline formsets sit
far down the page, so the field that actually blocked the save is often not
even on screen.

This mixin adds one message at the top naming every field that failed, by its
human label, with the reason - including inline rows, identified by row number.

Applied once in web_portal/admin.py by wrapping AdminSite.register(), so every
ModelAdmin gets it without touching each of the ~60 classes (same approach as
the export actions in admin_export.py).
"""
from django.contrib import messages
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

# Errors past this point are summarised as "... and N more" so a form with a
# large inline formset cannot produce an unreadable wall of text.
MAX_LISTED = 12


def _field_label(form, name):
    """Human label for a bound field, falling back to a tidied field name."""
    if name == NON_FIELD_ERRORS:
        return 'Form'
    field = form.fields.get(name)
    label = getattr(field, 'label', None) if field else None
    if not label:
        label = name.replace('_', ' ')
    return str(label).strip().rstrip(':').capitalize()


def _form_problems(form, prefix=''):
    """[(location, reason)] for every error on one form."""
    problems = []
    for name, errors in form.errors.items():
        if name == NON_FIELD_ERRORS:
            # Not tied to one input; the row prefix alone is the best location.
            where = prefix or 'Form'
        else:
            label = _field_label(form, name)
            where = f'{prefix} - {label}' if prefix else label
        for error in errors:
            text = str(error)
            # The default required message says nothing about which input it
            # belongs to; the label is already in `where`, so make it explicit.
            if text == 'This field is required.':
                text = 'is empty - this field must be filled in.'
            problems.append((where, text))
    return problems


def _formset_problems(inline_formset):
    """[(location, reason)] for an inline formset, rows numbered as displayed."""
    formset = inline_formset.formset
    try:
        title = str(inline_formset.opts.verbose_name).capitalize()
    except Exception:
        title = 'Inline'

    problems = [(title, str(e)) for e in formset.non_form_errors()]
    for index, form in enumerate(formset.forms, start=1):
        if not form.errors:
            continue
        # Skip blank extra rows the user never touched.
        if not form.has_changed() and not form.instance.pk:
            continue
        problems += _form_problems(form, prefix=f'{title} row {index}')
    return problems


class DetailedFormErrorsMixin:
    """Name the offending fields at the top of an admin add/change form."""

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        try:
            self._report_form_errors(request, context)
        except Exception:
            # A summary is a convenience; never let it break the form itself.
            pass
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def _report_form_errors(self, request, context):
        problems = []

        adminform = context.get('adminform')
        form = getattr(adminform, 'form', None)
        if form is not None and getattr(form, 'errors', None):
            problems += _form_problems(form)

        for inline_formset in context.get('inline_admin_formsets') or []:
            problems += _formset_problems(inline_formset)

        if not problems:
            return

        shown = problems[:MAX_LISTED]
        items = format_html_join(
            '', '<li><strong>{}</strong> {}</li>',
            ((where, reason) for where, reason in shown),
        )
        remaining = len(problems) - len(shown)
        more = format_html('<li>... and {} more</li>', remaining) if remaining > 0 else ''
        count = len(problems)
        messages.error(request, mark_safe(format_html(
            'Not saved - {} problem{} found:<ul style="margin:6px 0 0 18px;">{}{}</ul>',
            count, '' if count == 1 else 's', items, more,
        )))
