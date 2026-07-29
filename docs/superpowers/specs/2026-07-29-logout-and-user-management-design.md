# Logout Button & User Management CRUD — Design Spec

## Goal

Add a functional logout button to the sidebar and implement full user management (CRUD) in the Admin panel, including fixing the login flow to authenticate against Supabase `app_users` in addition to the hardcoded admin user.

## Current State

- `_logout()` exists in `webapp/main.py:77` but no UI element calls it
- Sidebar renders the user section as static HTML via `ui.html()` — no interactive elements
- Login (`do_login()` in `main.py:123`) only checks the hardcoded `USERS` dict — users created via access request approval in `app_users` table cannot log in
- Admin panel lists users read-only and handles access request approval, but has no edit/delete/create capabilities
- `admin.py` uses `datetime` without importing it (latent bug on lines 83, 96)

## Design

### 1. Logout Button

**Location**: Sidebar bottom section (`.s-bottom`), next to the user avatar and name.

**Implementation**: Replace the static HTML user section in `_sidebar()` (`main.py:70-72`) with native NiceGUI components — a `ui.row()` containing the avatar, name, and a power-off icon button. The button calls `_logout()` on click.

**CSS**: Add a `.s-logout` style for the button — small, ghost-style, `var(--text-3)` color, hover to `var(--miss)`.

### 2. Login Fix — Authenticate Against Supabase

**Flow change in `do_login()`** (`main.py:123`):

1. Check hardcoded `USERS` dict first (preserves the system admin `ivan`)
2. If not found, query `app_users` table in Supabase by `username`
3. If found and `is_active == True`, verify password with `bcrypt.checkpw()`
4. If `must_change_password == True`, set a flag in `app.storage.user` to trigger the password change dialog
5. Store `authenticated`, `username`, `name`, `role` in `app.storage.user`

**Password change dialog**: After login, if `must_change_password` is set, `_page_shell()` shows a modal dialog (NiceGUI `ui.dialog`) asking for new password + confirmation. On submit, hash with bcrypt, update Supabase, clear the flag. The dialog is non-dismissable — user cannot navigate until password is changed.

### 3. Admin CRUD — User Management

Replace the static HTML user table in `admin.py` with interactive NiceGUI components.

**User table** — each row shows: username, email, role, status, and an actions column with:

| Action | UI Element | Behavior |
|--------|-----------|----------|
| Edit role | Button toggling `viewer` ↔ `admin` | Updates `app_users.role` in Supabase, refreshes row |
| Toggle active | Button toggling `is_active` | Updates `app_users.is_active` in Supabase, refreshes row |
| Reset password | Button | Generates 10-char random password, hashes with bcrypt, updates `app_users.password_hash` + sets `must_change_password = True`, shows password in `ui.notify()` |
| Delete user | Button (with confirmation) | Deletes row from `app_users`, refreshes table |

**Create user form** — expandable section at the top with fields:
- Nombre (required)
- Email (required)
- Username (required, auto-suggested from email)
- Rol (select: viewer/admin, default viewer)

On submit: generates temporary password, hashes with bcrypt, inserts into `app_users` with `must_change_password = True`, shows the temporary password via `ui.notify()`.

**System user (`ivan`)**: Displayed in the table but with no action buttons — the hardcoded admin cannot be modified from the UI.

### 4. Import Fix

Add `from datetime import datetime, timezone` to `admin.py` — currently uses `datetime` without importing it (lines 83, 96 in the access request approve/reject handlers).

## Files to Modify

| File | Changes |
|------|---------|
| `webapp/main.py` | Sidebar: replace static user HTML with NiceGUI components + logout button. Login: add Supabase auth fallback. Page shell: add password change dialog check. |
| `webapp/pages/admin.py` | Replace static user table with interactive CRUD components. Add create user form. Fix datetime import. |
| `webapp/theme.py` | Add `.s-logout` button CSS. |

## Supabase Schema (existing)

Table `app_users` already has all needed columns:
- `id` (uuid, PK)
- `username` (text, unique)
- `name` (text)
- `email` (text)
- `password_hash` (text)
- `role` (text: "viewer" | "admin")
- `is_active` (boolean)
- `must_change_password` (boolean)
- `created_at` (timestamptz)

No schema changes required.

## Out of Scope

- User self-registration (handled by existing access request flow)
- Email notifications on account creation
- Password complexity requirements
- Session timeout / auto-logout
