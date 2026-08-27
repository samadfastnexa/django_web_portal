from django.conf import settings
from django.db import models

FORMAT_CHOICES = (
    ("pdf", "PDF"),
    ("excel", "Excel"),
    ("word", "Word"),
)


class Report(models.Model):
    """A report the Crystal Reports service can render.

    ``name`` must match the .rpt filename (without extension) on the
    Crystal Reports service and the ``report_name`` sent by the frontend.
    """

    name = models.SlugField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    default_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="pdf")
    is_active = models.BooleanField(default=True)
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="UserReportAccess", related_name="accessible_reports"
    )

    def __str__(self):
        return self.name


class UserReportAccess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="report_access")
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="user_access")
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "report")
        verbose_name = "User report access"
        verbose_name_plural = "User report access"

    def __str__(self):
        return f"{self.user} -> {self.report}"


class BranchAccess(models.Model):
    """Restricts a user to specific SAP Business One branches.

    A user with no rows here is treated as unrestricted by branch.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="branch_access")
    branch_id = models.CharField(max_length=50)

    class Meta:
        unique_together = ("user", "branch_id")
        verbose_name = "Branch access"
        verbose_name_plural = "Branch access"

    def __str__(self):
        return f"{self.user} -> branch {self.branch_id}"


class SalesEmployeeAccess(models.Model):
    """Restricts a user to specific SAP Business One sales employees.

    A user with no rows here is treated as unrestricted by sales employee.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales_employee_access")
    sales_employee_id = models.CharField(max_length=50)

    class Meta:
        unique_together = ("user", "sales_employee_id")
        verbose_name = "Sales employee access"
        verbose_name_plural = "Sales employee access"

    def __str__(self):
        return f"{self.user} -> sales employee {self.sales_employee_id}"
