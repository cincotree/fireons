# Invite-only registration

In production, registering needs an invite code. Invites live in the `invites` table and are managed with SQL (Neon SQL editor or `psql`). There is no admin page.

## How it works

- The API reads `INVITE_ONLY`. When it is `true`, `POST /api/auth/register` requires a valid `invite_code`. Terraform sets it to `true` for production (`invite_only` in `infra/environments/production`).
- When it is unset or `false` (local development, the e2e suite), registration is open and `invite_code` is ignored.
- `GET /api/auth/registration` returns `{"invite_required": true|false}`. The register page uses it to show an invite code field.
- `/register?invite=<code>` prefills the field, so you can send people a link.
- An invite is valid until it is revoked, expired, or used `max_uses` times. The check and the use count update happen in one statement, so two people cannot use the last slot at once.
- A registration that fails for another reason (for example a taken username) does not use up the invite.
- Rejections always return `400 Invalid or expired invite code`, whatever the reason.

## Tables

`invites`: `id`, `code` (unique), `label`, `max_uses`, `use_count`, `expires_at`, `revoked_at`, `created_at`.

`invite_redemptions`: `invite_id`, `user_id` (unique), `created_at`. One row per user who registered with an invite.

## Create an invite

Generate a code:

```bash
openssl rand -base64 12 | tr '+/' '-_' | tr -d '='
```

Insert it:

```sql
insert into invites (id, code, label, max_uses, expires_at)
values (gen_random_uuid(), '<code>', 'for Asha', 1, now() + interval '14 days');
```

Use a larger `max_uses` for a code you share with a group. Leave `expires_at` out for no expiry. Send the person `https://app.fireons.com/register?invite=<code>`.

## Revoke, extend or inspect

```sql
update invites set revoked_at = now() where code = '<code>';

update invites set expires_at = now() + interval '7 days' where code = '<code>';

update invites set max_uses = max_uses + 5 where code = '<code>';
```

See every invite and who used it:

```sql
select i.label, i.use_count, i.max_uses, i.expires_at, i.revoked_at, u.username as used_by
from invites i
left join invite_redemptions r on r.invite_id = i.id
left join users u on u.id = r.user_id
order by i.created_at desc;
```

Revoking an invite does not remove users who already registered with it. To find everyone who used a leaked code, run the query above filtered with `where i.code = '<code>'`.

## Try it locally

Start the backend with `INVITE_ONLY=true`, insert an invite with the SQL above into the local database, then register at `http://localhost:3000/register?invite=<code>`.

## Tests

- Backend: `backend/tests/test_invites.py`
- Browser: `e2e-tests/tests/registration-invites.spec.ts` (the invite field, prefill, and a server rejection)
