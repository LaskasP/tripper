# Google identity and FastAPI session requirements

## Decision

Direct Google Identity Services (GIS) is sufficient for Tripper's Google-only authentication. An identity intermediary is not required for the current scope because Tripper needs only a verified Google identity, not access to Google APIs or multiple identity providers. FastAPI should validate the Google credential once at sign-in, link the Google subject to a local account, and then issue its own browser session.

Google-only sign-in can safely support email-addressed invitations for Gmail and Google Workspace identities. It cannot, by itself, prove continuing control of an external email address used by a consumer Google Account. Google explicitly says it is authoritative for `@gmail.com`, and for `email_verified=true` with an `hd` claim; when the email is non-Gmail and `hd` is absent, `email_verified=true` records Google's earlier verification but does not prove that the Google-account holder still controls that third-party mailbox. Google recommends an additional challenge in that case. [Google: verify the Google ID token](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)

For Tripper's provider-only model, accept an invitation without another challenge only when the freshly validated ID token has the invited email and either:

- the email ends in `@gmail.com`; or
- `email_verified` is `true` and `hd` is present.

Non-Gmail consumer Google Accounts (`hd` absent) may still sign in and use memberships already tied to their stable account, but they cannot satisfy an email-addressed invitation solely from Google's email assertion. Supporting that case requires a Tripper-owned mailbox challenge, such as a single-use code or link delivered to the invited address. That is an additional verification mechanism rather than a second sign-in provider. If provider-only is interpreted strictly as no Tripper-owned recovery or verification challenge, the user-visible constraint must instead say that such accounts cannot accept invitations.

## Identity and invitation model

Persist a local account with `(issuer, subject)` as its external identity key, using Google's issuer and the ID token's `sub`. Google defines `sub` as unique among Google Accounts, never reused, and stable when an account's email changes; Google warns that `email` can change and must not be the primary account identifier. [Google OpenID Connect API reference](https://developers.google.com/identity/openid-connect/reference)

Store the current email as a mutable, observed attribute with its verification and hosted-domain facts. Memberships refer to the local account ID, never to email. An email change therefore does not create a second Tripper person or remove existing trip access.

An invitation remains addressed to a normalized email value until acceptance. At acceptance, require a fresh, successfully validated Google ID token, compare its current `email` to the invitation's normalized email, and apply the authority rule above. Link the resulting membership to the local account identified by `(issuer, sub)`. A changed email does not retroactively retarget a pending invitation; the creator must revoke and replace it.

Do not infer Workspace membership from the suffix of `email`. Google requires the `hd` claim for hosted-domain restrictions, and absence of `hd` means the account is not in a Google-hosted organization. The `hd` request parameter is only a UI hint; enforce any domain rule against the returned, validated claim. [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)

## Sign-in validation contract

Use the GIS Sign in with Google authentication flow with `openid email profile`. Authentication is separate from authorization to Google APIs; Tripper does not need OAuth access or refresh tokens merely to sign users in. Google states that Sign in with Google supplies an ID token for authentication and does not manage the application's session. [Google integration considerations](https://developers.google.com/identity/gsi/web/guides/integrate)

The FastAPI sign-in endpoint must:

1. Receive the GIS `credential` over HTTPS. For GIS's server POST, reject the request unless the `g_csrf_token` cookie and body value are both present and exactly equal. Google documents this double-submit check as the CSRF defense for that submission. [Google: verify the Google ID token](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
2. Verify the JWT signature using Google's rotating public keys, honoring their cache lifetime; verify `aud` against Tripper's exact web client ID, `iss` against Google's accepted issuer, and `exp`. Use Google's Python verification library rather than the debugging-only `tokeninfo` endpoint. [Google: verify the Google ID token](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
3. Require `sub`, `email`, and `email_verified=true` for a Tripper account. Apply the stronger Gmail/Workspace authority rule separately when accepting an invitation. If Tripper initiates an OIDC authorization request with `nonce`, require the returned nonce to match; OIDC Core requires clients to check a nonce they sent. [OpenID Connect Core 1.0, ID Token validation](https://openid.net/specs/openid-connect-core-1_0-18.html#IDTokenValidation)
4. Find or create the local account by `(issuer, sub)`, update its observed email/profile fields, and issue a new Tripper session. Do not use the Google ID token itself as the long-lived API session and do not store Google access or refresh tokens for authentication-only scope.

## Browser session contract

Issue a same-origin cookie that contains only an opaque, high-entropy Tripper session ID. Keep the session record server-side with the local account ID, creation time, absolute expiry, last-seen time if idle expiry is desired, and revocation time. Rotate the session ID after Google sign-in; revoke it on logout. A practical initial lifetime is 7 days with renewal only after activity, while requiring a new Google sign-in after absolute expiry.

Set the cookie `HttpOnly`, `Secure` in production, `SameSite=Lax`, `Path=/`, and no broad `Domain` attribute. Starlette documents `HttpOnly`, `SameSite`, expiry, path, domain, and `https_only`/`Secure` controls. Its built-in `SessionMiddleware` stores signed cookie data that is readable by the client, so it is suitable only if Tripper intentionally accepts client-held session state. The opaque server-side record is the better fit here because logout/revocation and account disablement need immediate enforcement. [Starlette SessionMiddleware](https://www.starlette.io/middleware/#sessionmiddleware)

Resolve `request -> session -> local account` in `require_current_user`. Every protected trip read or write must then load the current membership and role from persistence. Never copy a trip role into a session as an authorization fact. This makes contributor removal or role change effective on the next protected request even while the user's authentication session remains valid. Anonymous published-guide and JSON-fallback reads bypass the session dependency.

If frontend and API use different origins, credentialed CORS must list exact allowed origins, methods, and headers; FastAPI documents that wildcard origins/methods/headers cannot be combined with credentials. Prefer serving them from one origin to reduce cookie and CSRF complexity. [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)

## Recovery and visible constraints

Tripper has no password, password reset, recovery email, or recovery codes. A person regains Tripper access by recovering the same Google Account and signing in again; Google directs users to its account-recovery flow, while managed work or school accounts may require their administrator. [Google Account recovery](https://support.google.com/accounts/answer/7682439)

Because identity is keyed by `sub`, regaining the same Google Account restores the same Tripper account even if its email changed. Signing in with a different Google Account, including one that now owns the old external mailbox, does not restore membership. If Google account recovery fails or the account is deleted, Tripper cannot recover that identity under the provider-only policy. The already-agreed ownership-transfer flow is therefore the only preventive escape hatch; Tripper must not automatically promote another participant.

The sign-in screen and invitation errors should state these constraints plainly:

- a Google Account is required;
- Tripper account recovery is handled by Google (or a Workspace administrator);
- an existing membership belongs to the Google Account, not permanently to its displayed email;
- Gmail and Google Workspace accounts can accept verified-email invitations directly;
- a consumer Google Account using another provider's email needs a Tripper mailbox challenge, or cannot accept invitations while the strict provider-only policy remains.

## Intermediary comparison

An intermediary would centralize session and provider integration and could add passwordless email verification, but it does not improve Google's `sub`, `email_verified`, or `hd` guarantees. It adds another identity namespace, dependency, account-linking policy, and recovery surface. Adopt one only if Tripper later chooses multiple providers or wants the intermediary to supply the mailbox challenge for non-Gmail consumer accounts. Direct GIS plus a local account/session table meets the currently selected single-provider scope.
