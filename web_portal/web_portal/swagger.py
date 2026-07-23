from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema


class CustomAutoSchema(SwaggerAutoSchema):
    def add_manual_parameters(self, parameters):
        """
        Advertise the global export on every GET operation: ?format=csv|xlsx
        downloads the (unpaginated) results as a file. Skipped if the view
        already documents a `format` parameter.
        """
        parameters = super().add_manual_parameters(parameters)
        if getattr(self, 'method', '').upper() == 'GET' and not any(
            getattr(p, 'name', None) == 'format' for p in parameters
        ):
            parameters = list(parameters) + [openapi.Parameter(
                'format', openapi.IN_QUERY,
                description='Response format. Use "csv" or "xlsx" to download an '
                            'export of the results (pagination is bypassed for exports).',
                type=openapi.TYPE_STRING, required=False, enum=['json', 'csv', 'xlsx'],
            )]
        return parameters

    def get_tags(self, operation_keys=None):
        tags = super().get_tags(operation_keys)
        view = getattr(self, "view", None)
        path = getattr(self, "path", "") or ""
        module = getattr(view, "__module__", "") if view else ""

        if tags:
            tags = ["Crop manage" if t == "crop_manage" else t for t in tags]

        if not tags:
            if path.startswith("/api/sap/") or module.startswith("sap_integration"):
                return ["SAP"]
            if module.startswith("crop_manage"):
                return ["Crop manage"]

        if module.startswith("sap_integration") and ("SAP" not in tags):
            return ["SAP"]

        return tags
