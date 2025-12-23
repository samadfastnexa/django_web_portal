from drf_yasg.inspectors import SwaggerAutoSchema


class CustomAutoSchema(SwaggerAutoSchema):
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
