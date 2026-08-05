"""
Small image previews for the admin.

Shared by the User / Sales Staff Profile (profile photo), Attendance
(check-in / check-out selfies) and the Field Advisory / Field Day attachment
inlines so the markup, sizing, the download button and the missing-file
handling live in one place.

The image tag is always emitted when the field holds a name; whether the file
can actually be fetched is decided in the browser via `onerror`. A server-side
existence check is deliberately NOT used as the gate: with media served by
nginx (or any remote storage) the file is frequently unreadable from Django's
own filesystem while the URL resolves perfectly for the user, and gating on
that would hide every working image. The check is still used to word the
message on change forms, where naming a missing file is genuinely useful.
"""
import os

from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe

EMPTY = mark_safe('<span style="color:#999">&mdash;</span>')

# Extensions rendered as a picture; anything else (pdf/doc/xls) gets a name chip.
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}

# Hide the broken image and reveal the sibling placeholder instead. Kept on one
# line because Django escapes attribute values, not this format string.
_ONERROR = (
    "var w=this.closest('.adm-thumb');"
    "w.querySelector('.adm-thumb-link').style.display='none';"
    "w.querySelector('.adm-thumb-missing').style.display='inline';"
    # Nothing to save either, so the button must not offer a 404 page as a file.
    "var d=w.querySelector('.adm-dl');if(d)d.style.display='none';"
    "this.onerror=null;"
)


def file_exists(field):
    """True when the file is readable from Django's own filesystem.

    A False here does not mean the browser cannot load it - see module docstring.
    """
    name = getattr(field, 'name', None)
    if not name:
        return False
    try:
        storage = getattr(field, 'storage', None)
        if storage is not None:
            try:
                return storage.exists(name)
            except NotImplementedError:
                pass
        return os.path.isfile(os.path.join(str(settings.MEDIA_ROOT), name))
    except Exception:
        return False


def _has_name(field):
    return bool(getattr(field, 'name', None))


def _url(field):
    """The file's URL, or None when the field is empty / has no storage URL."""
    if not _has_name(field):
        return None
    try:
        return field.url
    except Exception:
        return None


def is_image(field):
    """True when the stored file is one the browser can render as a picture."""
    name = getattr(field, 'name', None)
    if not name:
        return False
    return os.path.splitext(name)[1].lower() in IMAGE_EXTS


def download(field, label='Download', compact=False):
    """Button that SAVES the file instead of opening it in a tab.

    The `download` attribute does the work rather than a Django view: MEDIA_URL
    is same-origin ('/media/', served by nginx in production), which is exactly
    where browsers honour the attribute, so no request is routed through Django
    and no extra URL has to be secured. It also names the saved file after the
    upload instead of whatever the URL ends in.

    `compact` is the icon-only variant used under changelist thumbnails, where a
    full-width button would push the rows apart.
    """
    url = _url(field)
    if not url:
        return EMPTY
    filename = os.path.basename(field.name)
    css = 'adm-dl adm-dl-compact' if compact else 'adm-dl'
    text = '⬇' if compact else format_html('⬇ {}', label)
    return format_html(
        '<a class="{}" href="{}" download="{}" title="Download {}">{}</a>',
        css, url, filename, filename, text,
    )


def thumb(field, size=40, radius='50%', missing=None, downloadable=False):
    """Clickable square thumbnail for an ImageField.

    Falls back to `missing` (a dash by default) only if the browser fails to
    load the image, so an image Django cannot see but nginx can still shows.
    `downloadable` adds the small save-to-disk button underneath.
    """
    url = _url(field)
    if not url:
        return EMPTY
    style = (
        f'width:{size}px;height:{size}px;object-fit:cover;'
        f'border-radius:{radius};border:1px solid #e5e7eb;'
        'box-shadow:0 1px 2px rgba(0,0,0,.08);vertical-align:middle;display:block'
    )
    return format_html(
        '<span class="adm-thumb">'
        '<a class="adm-thumb-link" href="{}" target="_blank" title="Open full size">'
        '<img src="{}" style="{}" loading="lazy" onerror="{}" /></a>'
        '<span class="adm-thumb-missing" style="display:none">{}</span>'
        '{}'
        '</span>',
        url, url, style, _ONERROR, missing or EMPTY,
        download(field, compact=True) if downloadable else '',
    )


def preview(field, size=140, downloadable=False):
    """Larger preview for a change form, with the file name underneath.

    When the field is set but the file is not readable server-side, the caption
    says so and names the file - much more actionable than "No image uploaded",
    which wrongly implied nothing had ever been attached.

    `downloadable` adds a Download button below the caption. The button is still
    offered when the file is unreadable from Django: as in `thumb`, whoever
    serves media may well have it (see the module docstring).
    """
    if not _has_name(field):
        return mark_safe('<span style="color:#999">No image uploaded.</span>')

    name = field.name
    missing_note = format_html(
        '<span style="color:#b45309">Image file not found on the server:</span>'
        '<div style="font-size:11px;color:#777">{}</div>', name,
    )
    caption = os.path.basename(name)
    if not file_exists(field):
        caption = format_html(
            '{} <span style="color:#b45309">(file missing on this server)</span>', caption
        )
    return format_html(
        '<div>{}<div style="margin-top:4px;font-size:11px;color:#777">{}</div>{}</div>',
        thumb(field, size=size, radius='8px', missing=missing_note),
        caption,
        download(field) if downloadable else '',
    )


def file_cell(field, size=64):
    """Preview + download for an attachment that may not be an image.

    The meeting / field-day attachment inlines accept pdf, doc and xls as well
    as photos, so a plain <img> would be a permanently broken icon for half the
    rows. Images get a thumbnail; everything else gets its file name, and both
    get the same Download button.
    """
    url = _url(field)
    if not url:
        return EMPTY
    filename = os.path.basename(field.name)
    if is_image(field):
        body = thumb(field, size=size, radius='6px')
    else:
        body = format_html(
            '<a class="adm-file-chip" href="{}" target="_blank" title="Open {}">{}</a>',
            url, filename, filename,
        )
    return format_html(
        '<div class="adm-file-cell">{}{}</div>', body, download(field),
    )
