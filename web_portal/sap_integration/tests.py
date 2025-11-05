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
