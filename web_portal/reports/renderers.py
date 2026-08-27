from rest_framework.renderers import BaseRenderer, JSONRenderer


class BinaryFileRenderer(BaseRenderer):
    """Passes bytes through unchanged; satisfies content negotiation for file downloads.

    The view's success path returns a raw HttpResponse directly and never reaches
    this renderer. Error responses (from the DRF exception handler) do go through
    it whenever the client's Accept header selected this renderer - those hand it
    a plain {"error": ...} dict, not bytes. Falling through to JSON here keeps
    error messages readable instead of letting HttpResponse's content setter
    silently iterate the dict down to just its keys.
    """

    media_type = "application/octet-stream"
    format = "bin"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, (bytes, bytearray)):
            return data
        return JSONRenderer().render(data, accepted_media_type, renderer_context)
