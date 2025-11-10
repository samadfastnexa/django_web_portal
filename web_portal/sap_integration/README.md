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

## Admin Styling (Theme Toggle)

- Location: `web_portal/sap_integration/static/sap_integration/admin.css`
- The admin header theme toggle is icon-only with a fully transparent background (no box).
- CSS variables control colors and transitions:
  - `--theme-icon-color: #ffffff` (icon glyph color for contrast on orange header)
  - `--hover-bg` defines subtle overlay for links/buttons (not applied to the toggle)
- States:
  - Normal: transparent background, smooth transitions (≈240ms)
  - Hover/Focus: transparent background + subtle ring (`--hover-ring`)
  - Active: transparent background + small press translation
- Accessibility:
  - Toggle is a `role="switch"` with `aria-checked` and dynamic `aria-label`.
  - Respects `prefers-reduced-motion` by disabling transitions.
- Cross-mode behavior:
  - Sun/Moon icons (inline SVG) cross-fade via `opacity` based on `data-theme` on `<html>`.

Appearance specifications
- Container: `24px` square; icon sized `18px` and centered.
- Color: `currentColor` set by `--theme-icon-color` (`#ffffff`).
- No background, border, or shadow at rest.
- Position: right side of `#user-tools`.

Assets and fallback
- Inline SVG is injected into `.theme-toggle` using `currentColor` for theme-aware coloring.
- Backup assets exist under `static/sap_integration/icons/` (`sun.svg`, `moon.svg`).
- If icons fail to render, the script replaces them with emoji `☀`/`🌙` automatically.

## Approved Color Palette and Hover Behavior

- Primary orange: `#E26830` (rgba(226, 104, 48, 1))
- Orange dark (active/pressed): `#C75A2A`
- Orange soft background: `#FFE4D6`
- Orange soft border: `#F7BFA8`
- Orange contrast block: `#B64C1E` (AA with white text)
- Header/user-tools hover overlay: `rgba(0, 0, 0, 0.22)` to keep white text readable.

Defined in `static/sap_integration/admin.css` via variables:

```
:root {
  --orange: #E26830;
  --orange-dark: #C75A2A;
  --orange-soft: #FFE4D6;
  --orange-soft-border: #F7BFA8;
  --orange-contrast: #B64C1E;
  --orange-contrast-text: #ffffff;
  --accent-orange: #E26830;
  --hover-bg: rgba(0,0,0,0.22);
}
```

### Design Audit Checklist

1. Verify buttons, headers, highlights use the variables above (no hard-coded hex).
2. Compare side-by-side with the `#FFA500` reference in header, buttons, and sidebar.
3. Confirm hover uses dark overlay (not white), preserving white text visibility.
4. Test in Chrome, Edge, Firefox, Safari; adjust only variables if discrepancies arise.
5. Record findings and keep this palette as the source of truth.