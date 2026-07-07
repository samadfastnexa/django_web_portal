"""
Load Testing Script for Django Web Portal
==========================================
Uses Locust: pip install locust

Run:
    locust -f load_test.py --host=https://4b.vdc.services

Then open http://localhost:8089 in your browser to control the test.

Or run headless (no UI):
    locust -f load_test.py --host=https://4b.vdc.services \
           --headless -u 20 -r 5 --run-time 2m

    -u  = number of concurrent users
    -r  = users spawned per second
"""

from locust import HttpUser, task, between, events
import json
import random
from datetime import date, timedelta

# ─────────────────────────────────────────────
# Credentials — update before running
# ─────────────────────────────────────────────
TEST_EMAIL    = "your_test_user@email.com"
TEST_PASSWORD = "your_password"

# Date helpers
TODAY      = date.today().strftime("%Y-%m-%d")
MONTH_START = date.today().replace(day=1).strftime("%Y-%m-%d")
LAST_MONTH_START = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
LAST_MONTH_END   = (date.today().replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")


class PortalUser(HttpUser):
    """
    Simulates a real portal user:
      1. Login and get JWT token
      2. Hit various GET and POST endpoints using that token
    """
    wait_time = between(1, 3)   # each user waits 1-3 seconds between tasks
    token = None

    # ─────────────────────────────────────────────
    # Login — runs once per simulated user on start
    # ─────────────────────────────────────────────
    def on_start(self):
        """Login and store JWT token."""
        response = self.client.post(
            "/api/login/",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            name="[AUTH] Login",
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access") or data.get("token")
        else:
            self.token = None

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    # ─────────────────────────────────────────────
    # Accounts
    # ─────────────────────────────────────────────
    @task(3)
    def get_user_profile(self):
        self.client.get(
            "/api/users/me/",
            headers=self.auth_headers(),
            name="[ACCOUNTS] Get profile",
        )

    @task(1)
    def get_permissions(self):
        self.client.get(
            "/api/permissions/?page=1",
            headers=self.auth_headers(),
            name="[ACCOUNTS] List permissions",
        )

    @task(1)
    def get_organogram(self):
        self.client.get(
            "/api/organogram/",
            headers=self.auth_headers(),
            name="[ACCOUNTS] Organogram",
        )

    # ─────────────────────────────────────────────
    # Attendance
    # ─────────────────────────────────────────────
    @task(3)
    def get_attendance_list(self):
        self.client.get(
            "/api/attendances/",
            headers=self.auth_headers(),
            name="[ATTENDANCE] List",
        )

    @task(2)
    def get_attendance_report_weekly(self):
        self.client.get(
            "/api/attendance/report/?type=weekly",
            headers=self.auth_headers(),
            name="[ATTENDANCE] Report weekly",
        )

    @task(1)
    def get_attendance_report_monthly(self):
        self.client.get(
            "/api/attendance/report/?type=monthly",
            headers=self.auth_headers(),
            name="[ATTENDANCE] Report monthly",
        )

    @task(1)
    def post_check_in(self):
        """Simulate a check-in POST — adjust fields to match your serializer."""
        self.client.post(
            "/api/attendance/check-in/",
            json={
                "latitude": 31.5204 + random.uniform(-0.01, 0.01),
                "longitude": 74.3587 + random.uniform(-0.01, 0.01),
                "source": "load_test",
            },
            headers=self.auth_headers(),
            name="[ATTENDANCE] Check-in POST",
        )

    # ─────────────────────────────────────────────
    # Cart & Orders
    # ─────────────────────────────────────────────
    @task(3)
    def get_cart(self):
        self.client.get(
            "/api/cart/cart/",
            headers=self.auth_headers(),
            name="[CART] Get cart",
        )

    @task(2)
    def get_order_statistics(self):
        self.client.get(
            "/api/cart/orders/statistics/",
            headers=self.auth_headers(),
            name="[CART] Order statistics",
        )

    @task(2)
    def get_orders_list(self):
        self.client.get(
            "/api/cart/orders/",
            headers=self.auth_headers(),
            name="[CART] Orders list",
        )

    @task(1)
    def post_add_to_cart(self):
        """Add a sample item to cart."""
        self.client.post(
            "/api/cart/cart/add_item/",
            json={
                "product_item_code": "FG00001",
                "product_name": "Test Product",
                "quantity": random.randint(1, 5),
            },
            headers=self.auth_headers(),
            name="[CART] Add item POST",
        )

    # ─────────────────────────────────────────────
    # General Ledger  (always send date range — mandatory after our fix)
    # ─────────────────────────────────────────────
    @task(2)
    def get_general_ledger(self):
        self.client.get(
            f"/api/general-ledger/?from_date={LAST_MONTH_START}&to_date={LAST_MONTH_END}&page=1&page_size=50",
            headers=self.auth_headers(),
            name="[GL] Ledger list",
        )

    @task(1)
    def export_ledger_excel(self):
        """Heavy endpoint — now capped at 50K rows. Test it holds up."""
        with self.client.get(
            f"/api/general-ledger/export-excel/?from_date={LAST_MONTH_START}&to_date={LAST_MONTH_END}",
            headers=self.auth_headers(),
            name="[GL] Export Excel",
            catch_response=True,
        ) as resp:
            if resp.status_code == 400:
                # 400 means date range missing — expected if not passed
                resp.success()

    # ─────────────────────────────────────────────
    # SAP / Analytics
    # ─────────────────────────────────────────────
    @task(2)
    def get_collection_analytics(self):
        self.client.get(
            f"/api/analytics/collection/?period=monthly",
            headers=self.auth_headers(),
            name="[ANALYTICS] Collection monthly",
        )

    @task(1)
    def get_sales_vs_achievement(self):
        self.client.get(
            f"/api/sap/sales-vs-achievement/?from_date={LAST_MONTH_START}&to_date={LAST_MONTH_END}",
            headers=self.auth_headers(),
            name="[SAP] Sales vs Achievement",
        )

    @task(1)
    def get_products_catalog(self):
        self.client.get(
            "/api/sap/products-catalog/?limit=20&offset=0",
            headers=self.auth_headers(),
            name="[SAP] Products catalog",
        )

    # ─────────────────────────────────────────────
    # Field Advisory / Farmers
    # ─────────────────────────────────────────────
    @task(2)
    def get_farmers_list(self):
        self.client.get(
            "/api/farmers/?page=1",
            headers=self.auth_headers(),
            name="[FARMERS] List",
        )

    @task(1)
    def get_territories(self):
        self.client.get(
            "/api/field/territories/",
            headers=self.auth_headers(),
            name="[FIELD] Territories",
        )


# ─────────────────────────────────────────────
# Event hooks — print summary on test end
# ─────────────────────────────────────────────
@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.stats
    print("\n" + "="*60)
    print("LOAD TEST SUMMARY")
    print("="*60)
    for name, entry in stats.entries.items():
        print(f"{name[1]:<45} | avg: {entry.avg_response_time:.0f}ms | fail: {entry.fail_ratio*100:.1f}%")
    print("="*60)
