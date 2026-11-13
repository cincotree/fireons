# Google and Reddit sign-in setup

Sign-in is Google or Reddit only. A provider's button shows on `/login` only when both its client id and secret are set. Without either, nobody can sign in.

## Settings

Set these in `backend/.env` for local development (and in the API's environment or the `fireons/<APP_ENV>` secret in production):

```env
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
REDDIT_OAUTH_CLIENT_ID=
REDDIT_OAUTH_CLIENT_SECRET=
FRONTEND_URL=http://localhost:3000
OAUTH_REDIRECT_BASE_URL=http://localhost:8000
```

`OAUTH_REDIRECT_BASE_URL` is where the API is reachable from the browser. The redirect URIs to register are `{OAUTH_REDIRECT_BASE_URL}/auth/google/callback` and `{OAUTH_REDIRECT_BASE_URL}/auth/reddit/callback`, and they must match exactly, including `http` or `https` and any port. Restart the backend after changing the file (`docker compose up -d backend` for the Docker stack). Never commit the secrets or paste them into chat.

## Google

1. Open https://console.cloud.google.com and pick or create a project.
2. Go to APIs & Services, then OAuth consent screen (Google Auth platform). Choose External, fill in the app name and your email, and save. The scopes used are `openid`, `email` and `profile`, which need no verification.
3. While the app is in Testing mode, add your own Google account under Test users. Only listed accounts can sign in until you publish the app.
4. Go to Credentials, then Create credentials, then OAuth client ID. Choose Web application.
5. Under Authorized redirect URIs add `http://localhost:8000/auth/google/callback`. Add the production URI too when you deploy. No JavaScript origin is needed, because the flow runs on the backend.
6. Copy the Client ID and Client secret into `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`.

## Reddit

1. Signed in to Reddit, open https://www.reddit.com/prefs/apps and click Create another app.
2. Choose the type web app. Give it a name, and set the redirect uri to `http://localhost:8000/auth/reddit/callback`.
3. After creating it, the client id is the short string shown under the app name and the secret is the `secret` field. Put them in `REDDIT_OAUTH_CLIENT_ID` and `REDDIT_OAUTH_CLIENT_SECRET`.
4. Reddit may ask you to request API access under its developer terms before the app works. Follow the link it shows if sign-in is refused.
5. Reddit does not share an email address, so Reddit users have no email in Fireons and are never linked to an existing account.

## Try it

1. Open http://localhost:3000/login and click Continue with Google or Continue with Reddit.
2. After approving, you land on `/professionals`.
3. If you return to `/login?error=...`, the message names the cause. `provider_failed` usually means a wrong secret or a redirect URI that does not match exactly. `invite_required` means `INVITE_ONLY` is on and you need an invite code on the Join page.

## Production

Set `FRONTEND_URL` to the site's URL and `OAUTH_REDIRECT_BASE_URL` to the API's public URL (https), register the production callback URIs with both providers, and publish the Google app so it is not limited to test users.
