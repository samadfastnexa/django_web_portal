from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from .models import Policy


class PolicyListAndSyncTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed some policies
        Policy.objects.create(code="P001", name="Policy A", policy="A", active=True)
        Policy.objects.create(code="P002", name="Policy B", policy="B", active=False)

    def test_list_db_policies_basic(self):
        url = reverse('policy_records')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('count'), 2)
        self.assertEqual(len(payload.get('data', [])), 2)

    def test_list_db_policies_filters(self):
        url = reverse('policy_records')
        resp = self.client.get(url, { 'active': 'true', 'search': 'Policy' })
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('count'), 1)
        row = payload['data'][0]
        self.assertEqual(row['code'], 'P001')

    @patch('sap_integration.views.SAPClient.__enter__')
    @patch('sap_integration.views.SAPClient.__exit__')
    @patch('sap_integration.views.SAPClient.get_all_policies')
    def test_sync_policies_creates_and_updates(self, mock_get_pols, mock_exit, mock_enter):
        # Configure context manager behavior
        mock_enter.return_value = None
        mock_exit.return_value = None

        # Existing policy to update, and new to create
        mock_get_pols.return_value = [
            {
                'code': 'P001', 'name': 'Policy A Updated', 'policy': 'A1',
                'valid_from': '2024-01-01', 'valid_to': '2025-01-01', 'active': True,
            },
            {
                'code': 'P003', 'name': 'Policy C', 'policy': 'C',
                'valid_from': '2024-06-01', 'valid_to': '2026-06-01', 'active': True,
            },
        ]

        url = reverse('policies_sync')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('updated'), 1)
        self.assertEqual(payload.get('created'), 1)

        # Verify DB state
        p1 = Policy.objects.get(code='P001')
        self.assertEqual(p1.name, 'Policy A Updated')
        self.assertEqual(p1.policy, 'A1')
        p3 = Policy.objects.get(code='P003')
        self.assertEqual(p3.name, 'Policy C')


class SalesVsAchievementApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        import types, sys
        os.environ['HANA_HOST'] = 'localhost'
        os.environ['HANA_PORT'] = '30015'
        os.environ['HANA_USER'] = 'tester'
        os.environ['HANA_PASSWORD'] = 'secret'
        os.environ['HANA_SCHEMA'] = '4B-ORANG_APP'

        class FakeCursor:
            def execute(self, sql):
                return None
            def close(self):
                return None

        class FakeConn:
            def cursor(self):
                return FakeCursor()
            def close(self):
                return None

        fake_hdbcli = types.ModuleType('hdbcli')
        fake_hdbcli.dbapi = types.SimpleNamespace(connect=lambda **kwargs: FakeConn())
        self._orig_hdbcli = sys.modules.get('hdbcli')
        sys.modules['hdbcli'] = fake_hdbcli

    def tearDown(self):
        import sys
        if self._orig_hdbcli is not None:
            sys.modules['hdbcli'] = self._orig_hdbcli
        else:
            sys.modules.pop('hdbcli', None)

    @patch('sap_integration.views.sales_vs_achievement')
    def test_territory_dg_khan_unscaled_by_default(self, mock_sales):
        mock_sales.return_value = [
            {
                'TERRITORYID': 45,
                'TERRITORYNAME': 'D.G Khan Territory',
                'SALES_TARGET': 5000000.0,
                'ACCHIVEMENT': 3500000.0,
                'F_REFDATE': '2025-10-01',
                'T_REFDATE': '2025-10-30',
            }
        ]
        url = reverse('sales_vs_achievement_api')
        resp = self.client.get(url, {'territory': 'D.G Khan Territory'})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('count'), 1)
        row = payload['data'][0]
        self.assertEqual(row.get('TERRITORYNAME'), 'D.G Khan Territory')
        self.assertEqual(row.get('SALES_TARGET'), 5000000.0)
        self.assertEqual(row.get('ACCHIVEMENT'), 3500000.0)
        self.assertNotIn('Sales_Target', row)
        self.assertNotIn('Achievement', row)

    @patch('sap_integration.views.sales_vs_achievement')
    def test_in_millions_true_scales_values(self, mock_sales):
        mock_sales.return_value = [
            {
                'TERRITORYID': 45,
                'TERRITORYNAME': 'D.G Khan Territory',
                'SALES_TARGET': 5000000.0,
                'ACCHIVEMENT': 3500000.0,
                'F_REFDATE': '2025-10-01',
                'T_REFDATE': '2025-10-30',
            }
        ]
        url = reverse('sales_vs_achievement_api')
        resp = self.client.get(url, {'territory': 'D.G Khan Territory', 'in_millions': 'true'})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('count'), 1)
        row = payload['data'][0]
        self.assertEqual(row.get('TERRITORYNAME'), 'D.G Khan Territory')
        self.assertEqual(row.get('SALES_TARGET'), 5.0)
        self.assertEqual(row.get('ACCHIVEMENT'), 3.5)

    @patch('sap_integration.views.sales_vs_achievement')
    def test_in_millions_false_keeps_raw_values(self, mock_sales):
        mock_sales.return_value = [
            {
                'TERRITORYID': 45,
                'TERRITORYNAME': 'D.G Khan Territory',
                'SALES_TARGET': 12000000.0,
                'ACCHIVEMENT': 9000000.0,
                'F_REFDATE': '2025-01-01',
                'T_REFDATE': '2025-12-31',
            }
        ]
        url = reverse('sales_vs_achievement_api')
        resp = self.client.get(url, {'territory': 'D.G Khan Territory', 'in_millions': 'false'})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        row = payload['data'][0]
        self.assertEqual(row.get('SALES_TARGET'), 12000000.0)
        self.assertEqual(row.get('ACCHIVEMENT'), 9000000.0)

    @patch('sap_integration.views.sales_vs_achievement')
    def test_group_by_territory_aggregates_rows(self, mock_sales):
        mock_sales.return_value = [
            {
                'TERRITORYID': 45,
                'TERRITORYNAME': 'D.G Khan Territory',
                'SALES_TARGET': 1000000.0,
                'ACCHIVEMENT': 500000.0,
                'F_REFDATE': '2025-10-01',
                'T_REFDATE': '2025-10-30',
            },
            {
                'TERRITORYID': 45,
                'TERRITORYNAME': 'D.G Khan Territory',
                'SALES_TARGET': 2000000.0,
                'ACCHIVEMENT': 1000000.0,
                'F_REFDATE': '2025-11-01',
                'T_REFDATE': '2025-11-30',
            }
        ]
        url = reverse('sales_vs_achievement_api')
        resp = self.client.get(url, {'group_by': 'territory'})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get('success'))
        self.assertEqual(payload.get('count'), 1)
        row = payload['data'][0]
        self.assertEqual(row.get('TERRITORYNAME'), 'D.G Khan Territory')
        self.assertEqual(row.get('SALES_TARGET'), 3000000.0)
        self.assertEqual(row.get('ACCHIVEMENT'), 1500000.0)
