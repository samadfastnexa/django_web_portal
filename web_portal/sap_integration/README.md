# SAP Integration — Policies API

This module exposes endpoints to list policy records stored in the local database and to synchronize policies from SAP Projects (via `U_pol` field) into the database. It also provides a simple UI page for browsing and syncing policies.

## Endpoints

- `GET /api/sap/policy-records/`
  - Lists policies from the database.
  - Query params:
    - `search` (optional): fuzzy search against `code`, `name`, `policy`.
    - `active` (optional): `true` or `false` to filter by status.
    - `valid_from` (optional): ISO date `YYYY-MM-DD`, minimum effective date.
    - `valid_to` (optional): ISO date `YYYY-MM-DD`, maximum effective date.
  - Response:
    ```json
    { "success": true, "count": 12, "data": [ { "code": "P001", "name": "...", "policy": "...", "valid_from": "2024-01-01", "valid_to": "2025-01-01", "active": true, "created_at": "...", "updated_at": "..." } ] }
    ```

- `POST /api/sap/policies/sync/`
  - Synchronizes policies from SAP Projects into the DB using the `U_pol` field.
  - Behavior:
    - Creates new records where `code` does not exist.
    - Updates existing records matched by `code`.
  - Response:
    ```json
    { "success": true, "created": 5, "updated": 7 }
    ```

- `GET /api/sap/policies/view/`
  - Renders a responsive page with a table of policies and a "Sync" button.
  - Uses the two endpoints above under the hood.

## Security

- Reads (`GET /policy-records/`) are safe by default; add authentication/permissions as needed.
- Sync (`POST /policies/sync/`) expects same-origin requests and CSRF token. The UI includes CSRF via cookie. Optionally enforce login-only access.

## Notes

- Policies are derived from SAP Projects via `U_pol` (assumed string). If policies live elsewhere or the field differs, update `sap_client.get_all_policies()` accordingly.
- The UI page uses fetch with `credentials: 'same-origin'` and shows loading and toast notifications.
- Unit tests in `sap_integration/tests.py` cover listing and sync logic with mocks.