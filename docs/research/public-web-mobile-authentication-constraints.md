# Public web and mobile authentication constraints

Status: research resolution for [Establish public web and mobile authentication constraints](https://github.com/LaskasP/tripper/issues/42), 2026-09-20.

## Question

Which protocol, browser, native-app, and mobile-store constraints must Tripper's public release satisfy when it supports Google, Apple, and passwordless email across a same-origin browser app and a React Native mobile app? Which requirements can eliminate or qualify identity-platform options?

## Answer

The public release needs one account system exposed through two different client security models:

- The same-origin browser app should use a backend-for-frontend (BFF): the backend is the confidential OAuth/OIDC client, keeps provider tokens out of browser JavaScript, and gives the browser an opaque cookie session.
- Each React Native app installation is a public client. It cannot keep a client secret and must use Authorization Code with PKCE through an external user-agent (a system browser or platform browser tab), then return through a securely claimed redirect.
- Google, Apple, and passwordless email must all resolve to Tripper identities without using email as the identity key. A stable provider identifier (`issuer` plus `subject`, or an equivalently stable provider-owned identifier for non-OIDC email authentication) is required. Linking two identities must require authenticated proof of both; email equality is not proof.

These constraints do **not** make an intermediary OIDC/CIAM provider mandatory. Tripper could integrate Google, Apple, and an email service directly and implement its own account-linking and lifecycle layer. They do, however, define a substantial integration surface. A broker is justified only if it demonstrably owns that surface across web, iOS, and Android without weakening the protocol requirements below. Provider selection should therefore compare qualified direct, managed, and self-hosted options rather than assuming that "mobile" alone requires a broker.

## Hard qualification gates

Any identity-platform option for the public release must satisfy all of these gates.

### 1. Standards-correct browser flow

The web deployment should use a BFF pattern. The current IETF browser-app guidance orders BFF, token-mediating backend, and browser-only client patterns from higher to lower security. In the BFF pattern, the server acts as a confidential client and keeps OAuth access and refresh tokens in a cookie-backed server context rather than exposing them to browser code. It requires `Secure` and `HttpOnly` cookies, recommends `SameSite=Strict`, and requires CSRF protection. The browser-facing application must use Authorization Code rather than Implicit, exact registered redirect URIs, and PKCE where supported/recommended. [RFC 10017, sections 6.1, 6.1.3.2, 6.1.3.3, and 7.2](https://www.rfc-editor.org/rfc/rfc10017.html)

This fits Tripper's same-origin browser architecture and preserves the existing opaque-session-cookie boundary. A candidate that requires long-lived provider tokens in `localStorage`, exposes refresh tokens to frontend JavaScript, or depends on the Implicit flow fails this gate.

### 2. Native public-client flow

Native apps are public clients: a secret shipped in a React Native bundle is not confidential. Native authorization requests must use an external user-agent, not an embedded WebView, and public native clients must use Authorization Code with PKCE. Shared client secrets must not be treated as authentication for a native client. [RFC 8252, sections 4, 6, 8.4, and 8.12](https://www.rfc-editor.org/rfc/rfc8252.html) Google independently prohibits OAuth requests in developer-controlled embedded user-agents. [Google OAuth 2.0 policies](https://developers.google.com/identity/protocols/oauth2/policies)

A candidate fails if its React Native integration embeds the provider login page, requires a recoverable secret in the app, lacks PKCE with `S256`, or cannot register the iOS and Android applications as public clients. PKCE's `S256` method protects against authorization-request observation; `plain` is permitted only for constrained environments that cannot use `S256`. [RFC 7636, section 4.2](https://www.rfc-editor.org/rfc/rfc7636.html#section-4.2)

### 3. Safe redirect handling

Authorization servers must compare redirect URIs using exact string matching, and clients must prevent CSRF and mix-up attacks. Public clients must use PKCE; confidential clients should also use it. [RFC 9700, section 2.1](https://www.rfc-editor.org/rfc/rfc9700.html)

For mobile, claimed HTTPS redirects (iOS Universal Links and Android App Links) have better ownership properties than arbitrary custom schemes. React Native's own security guidance warns that custom-scheme deep links can be claimed by malicious apps, requires PKCE for OAuth redirects, and recommends Universal Links for secure linking. [React Native security guidance](https://reactnative.dev/docs/security) Android recommends verified App Links (`android:autoVerify`) to prevent deep-link hijacking. [Android unsafe deep-link guidance](https://developer.android.com/privacy-and-security/risks/unsafe-use-of-deeplinks)

A candidate must document exact per-platform redirect registration and support claimed HTTPS redirects, or provide a clearly justified platform-native alternative with equivalent protections. This is also a practical Google constraint: Google's installed-app documentation says custom URI schemes are no longer supported for Android and Chrome-app OAuth clients and deprecates loopback redirects on mobile. [Google OAuth 2.0 for native apps](https://developers.google.com/identity/protocols/oauth2/native-app)

### 4. Correct identity keys and token validation

OIDC clients must validate at least issuer, audience, signature, expiration, and the transaction nonce when used. [OpenID Connect Core 1.0, section 3.1.3.7](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation) OIDC explicitly says email, phone number, username, and name must not be used as unique user identifiers. [OpenID Connect Core 1.0, section 5.7](https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability) Google's OIDC reference likewise says `sub`, not email, is its stable user identifier. [Google OIDC API reference](https://developers.google.com/identity/openid-connect/reference)

Consequently, Tripper must key an external identity by its provider/issuer and stable subject. Email is a contact or verification attribute only. A platform that auto-merges Google, Apple, and email identities merely because their email strings match fails the requirement; it must support explicit linking after fresh proof of control.

### 5. Apple login and private-email behavior

Because Tripper will use Google to establish the user's primary account in its iOS app, Apple's App Review Guideline 4.8 requires an equivalent login option that limits collection to name and email, lets users keep email private, and does not collect app interactions for advertising without consent. Apple's listed exemptions do not describe Tripper's planned public consumer app. Sign in with Apple is the straightforward conforming option and is already a product requirement. [Apple App Review Guidelines, section 4.8](https://developer.apple.com/app-store/review/guidelines/#login-services)

Apple web login is not a standalone website-only registration: Apple requires a Services ID associated with a primary Sign in with Apple-enabled App ID, registered web domains and absolute return URLs, and a private key. Sending mail to users who choose Hide My Email also requires registering outbound email sources and authenticating them with SPF and/or DKIM. [Apple: Configuring your environment for Sign in with Apple](https://developer.apple.com/documentation/signinwithapple/configuring-your-environment-for-sign-in-with-apple) [Apple: Configure Sign in with Apple for the web](https://developer.apple.com/help/account/capabilities/configure-sign-in-with-apple-for-the-web) [Apple: Configure private email relay](https://developer.apple.com/help/account/capabilities/configure-private-email-relay-service)

A platform must preserve Apple's stable subject and private relay address behavior, support native Apple sign-in plus the associated website, and expose the Apple account-change/revocation lifecycle rather than flattening Apple identities to email. It must also preserve the profile data supplied at first authorization rather than assuming Apple will resend all user fields on every login. [Apple: Authenticating users with Sign in with Apple](https://developer.apple.com/documentation/signinwithapple/authenticating-users-with-sign-in-with-apple)

### 6. Account deletion and upstream revocation

Both stores impose account-lifecycle requirements independent of login protocol:

- Apple requires apps that support account creation to let users initiate deletion in the app. For Sign in with Apple, the app should revoke the user's Apple tokens. [Apple account-deletion guidance](https://developer.apple.com/support/offering-account-deletion-in-your-app)
- Google Play requires an in-app deletion path and a web resource where users can request deletion of the app account and associated data. [Google Play account-deletion requirements](https://support.google.com/googleplay/android-developer/answer/13327111)

The architecture must therefore provide a Tripper-owned account-deletion workflow across clients and a way to unlink/revoke each upstream identity. A platform with no revocation API, no deletion hooks, or no exportable mapping from Tripper account to upstream identities fails this gate.

### 7. Mobile token storage and session lifecycle

If the mobile client holds refresh or access tokens, they must be stored using platform-protected storage, not React Native Async Storage. React Native documents Async Storage as unencrypted and unsuitable for tokens and points to iOS Keychain and Android secure-storage facilities. [React Native security guidance](https://reactnative.dev/docs/security) Apple describes Keychain as encrypted storage for small secrets. [Apple Keychain Services](https://developer.apple.com/documentation/security/keychain-services)

The candidate must support revocation, expiry, rotation/reuse detection where refresh tokens are issued, logout on one device without corrupting other sessions, and recovery from provider-side credential revocation. OAuth security best practice requires refresh tokens issued to public clients to be sender-constrained or rotated. [RFC 9700, section 2.2.2](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.2.2) The candidate must state exactly which component stores each token and how compromise is bounded.

### 8. Three distinct client registrations and one account domain

Web, iOS, and Android have different redirect and client-authentication properties and should be represented as distinct registered clients under one logical Tripper identity tenant. Google, for example, distinguishes web and installed/mobile clients, requires exact authorized redirects for web, and binds Android clients to package name and signing-certificate fingerprint. [Google Cloud: Manage OAuth clients](https://support.google.com/cloud/answer/15549257)

A platform must support environment-separated and platform-separated client registrations while presenting one account domain and one explicit identity-linking model. Reusing a web client secret in mobile is disqualifying.

## Passwordless email implications

Passwordless email is an authentication method, not evidence that all three login methods naturally share an OIDC subject. The selected architecture must define:

- whether the email factor is a magic link, one-time code, or both;
- short expiry and single use;
- rate limiting and anti-enumeration behavior;
- what happens when a link is opened on a different device from the one that started sign-in;
- how the app returns safely from the mail client without putting a reusable credential in an interceptable deep link;
- how a passwordless identity is linked to Google or Apple only after fresh authentication, never by email matching.

These are qualification questions for a provider comparison. The cited OAuth/OIDC standards do not standardize passwordless email delivery itself, so a vendor claim of "OIDC support" is insufficient evidence for this requirement.

## Consequences for provider selection

The next comparison can eliminate any managed or self-hosted option that lacks even one of the hard gates. Among qualifying options, compare:

1. Native standards compliance and SDK quality: external browser, PKCE, claimed HTTPS redirects, no embedded secret.
2. First-class Google, Apple, and passwordless email support on all three clients.
3. Explicit, auditable identity linking without email-based auto-merge.
4. Web BFF compatibility and the ability to keep provider tokens server-side.
5. Account deletion, unlinking, upstream token revocation, webhook reliability, audit logs, and exportability.
6. Operational burden, hosted-region/privacy terms, pricing at expected active-user counts, lock-in, and a tested exit path.

Direct integration remains a valid baseline in that comparison. Its cost is not the core Google or Apple redirect alone; it is owning the combined linking, passwordless-email abuse controls, client registrations, token/session lifecycle, deletion/revocation, and operational monitoring. A broker earns its place only by reducing that burden while preserving Tripper-owned authorization and portable account mappings.

## Decision unlocked

This research narrows, but does not itself select, the public authentication architecture:

- **Not forced:** an OIDC/CIAM intermediary solely because React Native is planned.
- **Forced:** a standards-compliant split between web confidential-client/BFF behavior and native public-client behavior; Google and Apple support; a separately specified passwordless-email method; stable non-email identity keys; explicit linking; and full store-compliant deletion/revocation lifecycle.
- **Selection rule:** compare direct integration, managed CIAM, and self-hosted identity only among candidates that pass every hard gate above. Then choose based on whole-lifecycle implementation and operating cost, not login-screen convenience.

No additional decision ticket is required from this research alone: the existing platform-strategy/provider-comparison work can apply these gates. Provider-specific rollout and migration details remain appropriately in the map's fog until that selection is made.
