from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from reports.models import Report, UserReportAccess


class Command(BaseCommand):
    help = (
        "Grants a user access to one report, or to all of them. "
        "Usage: grant_report_access <user> <ReportName> | "
        "grant_report_access <user> --all. "
        "<user> is an email address or a username."
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Email address or username.")
        parser.add_argument("report_name", nargs="?", help="Report to grant. Omit with --all.")
        parser.add_argument("--all", action="store_true", help="Grant every active report.")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        report_name = options["report_name"]

        # This project authenticates by email (USERNAME_FIELD = "email") but keeps
        # a username column, so accept either identifier.
        user = User.objects.filter(email__iexact=username).first()
        if user is None:
            user = User.objects.filter(username__iexact=username).first()
        if user is None:
            raise CommandError(f"No user matching '{username}' (tried email and username).")

        if options["all"]:
            reports = list(Report.objects.filter(is_active=True))
            if not reports:
                raise CommandError("No active reports to grant. Run `manage.py migrate reports` first.")
        else:
            if not report_name:
                raise CommandError("Give a report name, or pass --all.")
            report = Report.objects.filter(name=report_name).first()
            if report is None:
                known = ", ".join(Report.objects.values_list("name", flat=True)) or "none"
                raise CommandError(f"No report named '{report_name}'. Known reports: {known}.")
            reports = [report]

        for report in reports:
            _, created = UserReportAccess.objects.get_or_create(user=user, report=report)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Granted '{user}' access to '{report.name}'."))
            else:
                self.stdout.write(f"'{user}' already has access to '{report.name}'.")
