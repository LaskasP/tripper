# Transactional email provider for Tripper

Research date: **2026-09-19**. Pricing, free tiers, abuse controls, and legal terms can change; verify them again when provisioning. All sources below are first-party provider documentation or legal pages.

## Recommendation

Use **Mailgun Free in its EU region** for the first release, sending from a dedicated subdomain such as `invites@notify.<domain>` through the HTTPS API.

Why this is the cheapest responsible launch choice:

- It costs **$0/month for up to 100 messages/day**, includes one verified custom domain, the REST API, delivery/bounce webhooks, suppression management, and ticket support. Its free-plan logs and Events API retain data for only one day. This is comfortably above Tripper's expected invitation volume without creating a surprise usage bill. [Mailgun pricing](https://www.mailgun.com/pricing/), [Mailgun free-plan details](https://help.mailgun.com/hc/en-us/articles/203068914-What-does-the-Free-plan-offer)
- Unlike a nominal EU sending endpoint backed by US storage, Mailgun lets the domain be created in Europe and states that messages, event logs, suppressions, tags, statistics, routes, and IP addresses remain in the chosen region. Limited account data, API keys, billing data, and domain names are global. [Mailgun regions](https://www.mailgun.com/about/regions/)
- Production use requires a verified custom domain; SPF and DKIM records are supplied during verification. Publish a DMARC policy as well. [Mailgun domain verification](https://documentation.mailgun.com/docs/mailgun/user-manual/domains/domains-verify)
- The free tier is an ongoing plan, not a one-month trial. A new account must verify email and a mobile phone. Mailgun can additionally place an account on probation and request business verification, so activation must be completed before Tripper's cutover. [Account activation](https://help.mailgun.com/hc/en-us/articles/37182949611419-Account-Activation), [business verification](https://help.mailgun.com/hc/en-us/articles/202850080-Why-did-I-receive-the-error-Business-verification-is-required)

Use **Amazon SES in an EU region** as the fallback if Mailgun approval, delivery tests, or service reliability are unacceptable. SES is the lowest variable-cost option and has strong portability, but it is not the lowest-effort option: every new account/region starts in the SES sandbox and must be approved for production. At current à-la-carte pricing, 10,000 simple invitation emails are approximately **$1 plus message-data charges**; AWS introduced a $0.16/1,000 Essentials plan for new account/region pairs in July 2026, but documents that customers may switch to à-la-carte pricing. [SES pricing](https://aws.amazon.com/ses/pricing/), [SES sandbox and production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

The fallback is deliberately a different operational and abuse-review path. Do not switch providers reactively on a single bounced invitation: first test the authenticated Mailgun domain against Gmail, Outlook, and at least one independent mailbox, and inspect bounce/complaint events.

## Comparison

| Provider | Lowest realistic production cost | Production gate | EU/data-processing position | Fit for Tripper |
|---|---:|---|---|---|
| **Mailgun EU** | **$0**, 100/day; Basic $15/month for 10,000, then $1.80/1,000 | Email + phone activation; sandbox domain only reaches authorized recipients; verified custom domain is required for production; a flagged account may require business verification | EU domain keeps message data, logs, suppressions and statistics region-bound; limited account data is global; DPA/SCC terms are available | **Recommended first release:** no bill at expected volume, short default retention, explicit EU message-data residency, complete delivery tooling |
| **Amazon SES EU** | About $0.10/1,000 à-la-carte (or $0.16/1,000 on the new Essentials plan), plus $0.12/GB attachments; no fixed fee on these options | Mandatory per-region sandbox; while sandboxed, only verified recipients, 200/day and 1/second; AWS says initial review response is normally within 24 hours but can take longer | Multiple EU regional API endpoints; identity, sandbox status, quotas, DKIM, and suppression configuration are region-specific; AWS DPA/SCCs apply automatically when relevant | **Fallback / cost-led option:** extremely cheap and portable, but IAM, SNS/EventBridge plumbing, monitoring, and approval are disproportionate for the launch volume |
| **Brevo** | Free, 300/day; Starter starts at $9/month for 5,000 | Sending is subject to account approval; sender/domain authentication required | Brevo says its database processing/storage is in the EU (OVH France/Germany and Google Cloud Belgium); DPA available | Credible EU alternative, but free messages carry a **Sent with Brevo** footer; paid Starter is the practical branded-product tier |
| **Mailjet** | Free, 6,000/month and 200/day; Starter is €8/month for 8,000 in current EU pricing | API keys and an authenticated sender/domain are required; no universal production-approval SLA was found in the public documentation reviewed | Mailjet says personal data is stored exclusively in EU data centers in Frankfurt and Saint-Ghislain; DPA available | Strong EU-resident alternative, but Free carries Mailjet branding and ticket support lasts only the first 30 days |
| **Resend** | Free, 3,000/month and 100/day; Pro $20/month for 50,000, then $0.90/1,000 | Verify a sending domain; no universal production-approval SLA was found in the public documentation reviewed | DPA and SCCs available, but Resend states email/log data is retained in the US; standard-plan email/log retention is 30 days and backups persist 7 days | Best developer ergonomics and native idempotency, but weaker fit for an EU-first data posture |
| **Postmark** | Free Developer plan is only 100/month; Basic $15/month for 10,000, then $1.80/1,000 | Manual approval; until approved, sends are limited to verified owned domains; weekday review target is under 24 hours | DPA available, but Postmark states its primary data/servers are outside Chicago/AWS and does not offer EU servers | Strong transactional-email product, but neither cheapest nor EU-resident |

### Mailgun detail

**API and Python.** Mailgun exposes an HTTPS REST API and recommends it over SMTP for applications. Its documentation includes Python request examples, but Mailgun's current comparison material does not claim an official Python SDK. A small `httpx` adapter is enough and avoids coupling domain code to an SDK. [Mailgun send API](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/messages/post-v3--domain-name--messages), [Mailgun pricing FAQ](https://www.mailgun.com/pricing/)

**Authentication.** Create a sending subdomain rather than changing mail reception for the apex domain. Add the provider-supplied SPF and DKIM records and a Tripper-controlled DMARC record. MX and tracking CNAME records are unnecessary unless Tripper enables inbound routing or click/open tracking; invitation delivery does not need either. Mailgun's generic verification page lists all record types because it covers those optional features too. [Domain verification](https://documentation.mailgun.com/docs/mailgun/user-manual/domains/domains-verify)

**Events and suppression.** Mailgun includes webhooks, analytics, and reporting on Free, and its API exposes domain webhooks plus bounce, complaint, and unsubscribe suppressions. Process at least `delivered`, permanent failure/bounce, and complaint events. A hard bounce or complaint must mark the recipient unavailable for automatic resend until corrected. [Mailgun pricing](https://www.mailgun.com/pricing/), [Mailgun API reference](https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/messages/post-v3--domain-name--messages)

**Retries and idempotency.** Mailgun's send endpoint does not document a provider idempotency key. A timeout after submitting can therefore leave the caller unsure whether the message was accepted. Tripper must make the database outbox authoritative: give each invitation delivery a stable internal delivery ID, serialize one active attempt at a time, save the provider message ID, and reconcile later events. Do not blindly retry ambiguous sends. This application-level rule also makes a move to SES safe.

**Privacy.** Keep the one-day free-tier log retention. Disable open and click tracking for invitations: it is unnecessary for access control and adds tracking data. Send only the recipient address, sender, subject, and minimal message body. Never put the invitation secret in tags, metadata, webhook configuration, or provider templates. The secret must exist only in the URL fragment already chosen for the invitation flow. Review the current Sinch/Mailgun DPA and subprocessor list before account creation; the public regions page is a residency statement, not by itself a complete GDPR assessment. [Mailgun regions](https://www.mailgun.com/about/regions/), [Sinch DPA](https://www.sinch.com/legal/data-protection-agreement/)

### Amazon SES fallback detail

**Sandbox and identity.** SES sandbox status is per AWS region. In the sandbox it sends only to verified addresses/domains or the mailbox simulator, up to 200 messages in 24 hours and one per second. Production access requires a website URL, use-case classification, and acknowledgement that Tripper handles bounces and complaints. The sender identity remains verified after approval. AWS says an initial answer is normally supplied within 24 hours, but may request more information. [Request production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html)

**EU operation.** Select one EU SES region (for example Ireland or Frankfurt) and keep all identities, DKIM setup, configuration sets, and event destinations there. SES exposes regional HTTPS APIs; `boto3` is the official AWS SDK for Python. The AWS DPA is incorporated into service terms automatically when applicable, and AWS publishes its subprocessors. [SES regions](https://docs.aws.amazon.com/ses/latest/dg/regions.html), [AWS DPA](https://aws.amazon.com/compliance/faq/), [AWS subprocessors](https://aws.amazon.com/compliance/sub-processors/)

**Events and suppressions.** Publish delivery, bounce, and complaint events from a configuration set to SNS/EventBridge (or another supported destination), then deliver them to Tripper's HTTPS handler or queue. The account-level suppression list is regional. This is more setup than Mailgun's direct webhooks. [SES event publishing](https://docs.aws.amazon.com/ses/latest/dg/monitor-sending-activity-using-notifications.html), [SES regions and suppression behavior](https://docs.aws.amazon.com/ses/latest/dg/regions.html)

**Retries.** SES explicitly warns that a timeout/server error can occur after accepting a message, and retrying can create a second message with a new ID. Use the same outbox serialization and reconciliation rule as Mailgun; never treat an HTTP timeout as proof that no invitation was sent. [SES Developer Guide](https://docs.aws.amazon.com/ses/latest/dg/troubleshoot-error-messages.html)

### Other candidates

**Brevo.** The free plan provides 300 sends/day, transactional API/SMTP, webhooks, and no expiry, but adds provider branding. Starter begins at $9/month for 5,000 and removes the daily cap; removal of branding may be an add-on depending on locale/account. Brevo says all of its hosting servers that process/store databases are within the EU. It supports Python and webhook events, and documents UUID idempotency with a 30-minute TTL for batch transactional requests. Its transactional logs and message previews are stored indefinitely by default, so configure a short retention period before production. [Brevo plans](https://help.brevo.com/hc/en-us/articles/208589409-About-Brevo-s-pricing-plans), [free-plan limits](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan), [data storage](https://help.brevo.com/hc/en-us/articles/360001005510-Data-storage-location), [webhooks](https://developers.brevo.com/docs/transactional-webhooks), [retention](https://help.brevo.com/hc/en-us/articles/360021533839-Manage-your-transactional-logs-and-email-previews)

**Mailjet.** Free provides 6,000 messages/month with a 200/day limit, API/SMTP/webhooks, and up to 1,000 contacts, but carries Mailjet branding and includes ticket support only for the first 30 days. Messages above the daily limit queue for at most three days. Current EU-localized pricing lists Starter at €8/month for 8,000 with no daily limit. Mailjet offers an official Python wrapper and event webhooks for sent, bounce, spam, blocked, and related outcomes. It states that personal data is stored exclusively in EU data centers in Frankfurt and Saint-Ghislain. This is a sound fallback candidate if Mailgun cannot be activated, but its broader contact/marketing model and free-tier branding add unnecessary surface for invitation-only mail. [Mailjet plans](https://documentation.mailjet.com/hc/en-us/articles/8625025643803-Mailjet-Subscription-Management), [daily-limit queue](https://documentation.mailjet.com/hc/en-us/articles/360043048393-What-is-this-200-emails-per-day-limit-on-free-accounts), [EU storage](https://documentation.mailjet.com/hc/en-us/articles/360042712274-Where-is-my-personal-data-stored), [API and official wrappers](https://dev.mailjet.com/docs/api-reference), [webhooks](https://dev.mailjet.com/docs/email-api/webhooks/webhooks-overview)

**Resend.** Free includes 3,000/month with a 100/day cap and 30-day retention; Pro is $20/month for 50,000. It has an official asynchronous Python SDK, signed/retried webhooks, automatic suppression for hard bounces/complaints, and 24-hour idempotency keys, which is the cleanest API of the group. Its DPA covers transfers, but Resend states that customer data including message content, delivery logs, webhook payloads, and account records is stored in the US even when sending through Ireland. Use it only if that transfer posture is accepted. [Resend pricing](https://resend.com/pricing), [Python SDK](https://resend.com/python), [idempotency](https://resend.com/changelog/idempotency-keys), [GDPR and retention](https://resend.com/security/gdpr), [DPA](https://resend.com/legal/dpa)

**Postmark.** The free tier's 100 messages/month is suitable for integration testing but too small to be a dependable production allowance. Basic is $15/month for 10,000. Postmark manually reviews every new account and limits unapproved accounts to owned verified domains; the stated review target is under 24 weekday hours. It has an official async Python SDK, delivery/bounce/complaint webhooks, and automatic deactivation/suppression after hard bounces and complaints. Its default content history is 45 days. Postmark explicitly says it has no EU servers. [Postmark pricing](https://postmarkapp.com/pricing), [approval](https://postmarkapp.com/support/article/1084-how-does-the-account-approval-process-work), [Python SDK](https://postmarkapp.com/developer/integration/official-libraries), [webhooks](https://postmarkapp.com/developer/webhooks/webhooks-overview), [EU privacy](https://postmarkapp.com/eu-privacy)

## Provider-independent implementation contract

The provider choice should not escape the infrastructure boundary. Define one adapter operation such as `send_invitation(delivery_id, recipient, subject, text, html) -> provider_message_id` and normalize provider events into `delivered`, `temporary_failure`, `permanent_failure`, and `complaint`.

Use these rules regardless of provider:

1. Insert the invitation and an outbox row in the same PostgreSQL transaction.
2. A worker claims one outbox row, sends through HTTPS, and records attempt state and provider message ID. Never use VPS port 25.
3. Treat an explicit provider rejection as failed/retryable according to status. Treat a timeout after submission as **ambiguous**, not as unsent; reconcile events before manual retry.
4. Verify webhook authenticity according to the provider, deduplicate webhook events, and return success only after durable receipt (or queue handoff).
5. Stop automatic resend after permanent bounce or complaint. Allow the Creator to correct the address and issue a new invitation/token.
6. Keep templates and plain-text/HTML rendering in Tripper, not provider-hosted templates, so changing providers is configuration plus adapter work.
7. Publish SPF and DKIM and start DMARC at `p=none` with aggregate reporting; tighten the policy after observing legitimate traffic. Use a dedicated sending subdomain to isolate reputation.
8. Do not enable open/click tracking. Do not expose secrets in logs, tags, metadata, email subjects, or webhook payloads.

## Pre-cutover acceptance check

This research makes a recommendation; it does not create or configure accounts. Before production cutover:

- Activate a Mailgun account and create the custom domain specifically in the **EU region**.
- Confirm the account is not on probation and can send to arbitrary, non-authorized recipients.
- Verify SPF and DKIM; publish and validate DMARC.
- Send a test invitation to Gmail, Outlook, and one independent provider. Confirm inbox placement and that the invitation fragment is not present in provider event metadata.
- Trigger/test delivery, hard-bounce, and complaint webhook paths and confirm deduplication.
- Confirm Free still includes the public features and limits documented above; set a hard account/message limit where available.
- Review and archive the then-current DPA/subprocessor information.
- If any of approval, EU-region availability, or delivery acceptance fails, begin SES EU production-access review while keeping Mailgun disabled; do not silently fail over between providers for live invitations.

## Decision

Adopt **Mailgun Free, EU region** for Tripper's first release, subject to the pre-cutover acceptance check. Keep **Amazon SES in an EU region** as the documented fallback. Revisit the choice when invitation volume approaches 80 messages/day, Mailgun changes the free tier or residency terms, or measured delivery performance is unacceptable.
