# Hostinger VPS and email options for Tripper

Researched 2026-09-19 against first-party provider documentation and official Greek VAT guidance. Prices and product details can change; the purchase checkout remains authoritative.

## Recommendation

Keep the proposed **Hetzner CX23 in Nuremberg + Hetzner Object Storage + Mailgun Free EU** design for Tripper's first release.

Hostinger is not a cheaper like-for-like replacement once the comparison includes an off-server PostgreSQL backup repository. Its low VPS rate is a 24-month introductory rate paid entirely in advance; renewal is materially higher. Hostinger's bundled weekly whole-server backups are useful as a second recovery path, but they cannot replace `pgBackRest` base backups plus continuous WAL archiving: they are coarse, provider-controlled, cannot be downloaded, and restore the whole VPS destructively.

Hostinger Mail is inexpensive and now supports programmatic sending through Agentic Mail. It is still a hosted mailbox product rather than a mature transactional-delivery service: its only documented webhook event is inbound `message.received`; outbound delivery results are exposed through a 30-day control-panel log, not documented bounce/complaint/delivery webhooks or an application-facing suppression API. Keep Mailgun Free EU for invitations.

If a later checkout or benchmark changes the economics, the least risky alternative is a **mixed design**: Hostinger KVM 2 in Germany for compute, Hetzner Object Storage for `pgBackRest`, and Mailgun Free EU. Do not use Hostinger's same-account VPS backups as Tripper's only backup repository.

## VPS fit

Hostinger's Greek offer lists the following KVM plans. All use AMD EPYC, NVMe storage, KVM virtualization, a 1 Gbps network, a dedicated IP, full root access, managed firewall controls, and a public VPS API. Hostinger explicitly supports Docker/Docker Compose and offers Linux images including Ubuntu. The service remains self-managed even though an AI assistant is included. [Hostinger Greek VPS offer](https://www.hostinger.com/gr/filoksenia-vps) [Hostinger VPS dashboard](https://www.hostinger.com/support/5726606-how-to-use-the-vps-dashboard-in-hostinger/)

| Plan | Resources | Transfer | Advertised intro | Advertised renewal |
| --- | --- | --- | --- | --- |
| KVM 1 | 1 vCPU, 4 GB RAM, 50 GB NVMe | 4 TB | €5.49/month | €11.99/month for 24 months |
| KVM 2 | 2 vCPU, 8 GB RAM, 100 GB NVMe | 8 TB | €7.99/month | €14.99/month for 24 months |
| KVM 4 | 4 vCPU, 16 GB RAM, 200 GB NVMe | 16 TB | €10.99/month | €27.99/month for 24 months |

KVM 1 matches the proposed CX23's memory but has half its vCPU count. KVM 2 is the sensible Hostinger baseline for Caddy, the application container, PostgreSQL, `pgBackRest`, and the email outbox worker; it has the same vCPU count and twice the memory/disk of CX23.

Hostinger subscriptions are paid upfront. KVM VPS supports 1-, 12-, or 24-month renewal periods, while the advertised rate is presented with a 24-month renewal. The calculations below therefore assume the advertised introductory price also requires a 24-month checkout; this must be confirmed in checkout before purchase. All post-intro billing cycles are charged at regular rates, so the current renewal display is not a perpetual price lock. [Hostinger advance-payment rules](https://www.hostinger.com/support/1583589-how-to-pay-for-hostinger-services-in-advance/) [Hostinger billing-cycle rules](https://www.hostinger.com/support/1583235-how-to-change-your-billing-cycle-at-hostinger/)

The Greek price page says prices exclude VAT. The ordinary Greek VAT rate is 24%, although the customer's tax status can affect the invoice. [Hostinger Greek VPS offer](https://www.hostinger.com/gr/filoksenia-vps) [Greek Independent Authority for Public Revenue](https://www.aade.gr/exypiretisi-enimerosi/hristikoi-odigoi/enarxi-epiheirimatikis-drastiriotitas/basikoi-syntelestes-fpa)

KVM VPS purchases and renewals paid by a non-cryptocurrency method are eligible for the 30-day refund policy. A successful VPS refund starts a 180-day cooldown before another VPS refund is available. Outside refund eligibility, disabling auto-renewal leaves the service active to term; expiration then deletes it and its data. A refund terminates the service and erases its data immediately. [Hostinger refund policy](https://www.hostinger.com/support/9088216-what-is-hostinger-refund-policy/) [Hostinger cancellation behavior](https://www.hostinger.com/support/1583775-how-to-cancel-a-hosting-plan-at-hostinger/)

### Networking uncertainties

The dashboard exposes IPv4 and IPv6 and permits PTR configuration. The marketing page describes a dedicated IP but does not clearly state, before checkout, whether both address families are guaranteed in every selected location. Confirm both in checkout or with sales. [Hostinger VPS dashboard](https://www.hostinger.com/support/5726606-how-to-use-the-vps-dashboard-in-hostinger/)

Hostinger's European VPS choices are France, Germany, Lithuania, and the United Kingdom (some first-party pages inconsistently mention the Netherlands; the current VPS-specific list excludes it). Germany is the most sensible first test for a Greek audience, but city and routing matter more than country distance. Hostinger has no public per-location test files comparable to Hetzner's; its setup flow detects the lowest latency from the purchaser's current connection, and its official post-provision guidance is to run Ookla Speedtest CLI from the VPS. [Hostinger server locations](https://www.hostinger.com/support/1583267-where-are-hostinger-servers-located/) [Hostinger location selection](https://www.hostinger.com/support/10469992-how-to-migrate-your-vps-from-openvz-to-kvm-at-hostinger/) [Hostinger network-test guidance](https://www.hostinger.com/support/how-to-test-vps-network-speed-using-the-official-speedtest-cli/)

A VPS location is fixed after setup. Moving requires a destructive reinstall; Hostinger says this deletes server data, backups, and snapshots, so data must be exported first. [Hostinger VPS relocation](https://www.hostinger.com/support/10289743-how-to-transfer-your-vps-to-a-different-location-in-hostinger/)

## Backups, monitoring, and recovery

Hostinger includes automatic weekly whole-VPS backups and one manual snapshot. Only one snapshot is retained, a new one overwrites it, and it expires after 20 days. Daily backups are a paid upgrade; current documentation is inconsistent about exact retention, variously describing selected restore points or two daily plus two weekly copies. Treat the checkout/dashboard as authoritative. [Hostinger VPS backup and restore](https://www.hostinger.com/support/1583232-how-to-back-up-or-restore-a-vps) [Hostinger daily backups](https://www.hostinger.com/support/1665153-how-to-activate-daily-backups-in-hostinger/)

Restoring a Hostinger backup or snapshot overwrites the current server, is irreversible, and deletes the existing snapshot. VPS backups and snapshots cannot be directly downloaded. Reinstalling or changing location can remove recovery artifacts. These controls are useful for quick rollback, but they are not a portable, account-independent disaster-recovery repository. [Hostinger VPS backup and restore](https://www.hostinger.com/support/1583232-how-to-back-up-or-restore-a-vps) [Hostinger operating-system rebuild](https://www.hostinger.com/support/4965922-how-to-change-the-operating-system-of-your-vps-at-hostinger/)

Hostinger does not document a general S3-compatible object-storage product bundled with VPS. Root access permits `pgBackRest` to archive to any compatible external service; the like-for-like design therefore keeps Hetzner Object Storage. This is also intentionally outside the Hostinger account/failure boundary.

The Hostinger dashboard provides CPU, RAM, load, traffic, process, uptime, and action history plus firewall management and emergency mode. The reviewed first-party material does not promise alert rules for backup failure, WAL archive failure, disk pressure, container restarts, or application readiness. Tripper still needs its agreed external uptime check and its own host/application alerts. [Hostinger VPS dashboard](https://www.hostinger.com/support/5726606-how-to-use-the-vps-dashboard-in-hostinger/)

For a failed server, the documented paths are whole-server restore, emergency mode, or a clean reinstall followed by manual restoration. Tripper's responsible rebuild procedure remains infrastructure documentation plus a fresh Ubuntu VPS, Docker Compose deployment, restored `pgBackRest` base backup, replayed WAL, and smoke tests. Hostinger support does not manage PostgreSQL for the customer.

## PostgreSQL

Hostinger offers **self-hosted PostgreSQL on VPS**, including a one-click template, not a managed PostgreSQL service with provider-run patching, high availability, database backups, or point-in-time recovery. Hostinger explicitly describes VPS as self-managed and says PostgreSQL requires VPS. [Hostinger database support](https://www.hostinger.com/support/which-databases-and-data-tools-are-supported-at-hostinger/) [Hostinger PostgreSQL VPS](https://www.hostinger.com/applications/postgresql)

This does not reduce Tripper's operating responsibility relative to Hetzner: the operator must patch PostgreSQL, monitor replication/WAL and disk health, run `pgBackRest`, test restores, and respond to failures.

## Hostinger Mail versus Mailgun

Hostinger Mail is no longer SMTP-only. Agentic Mail, included in all current email plans, provides a REST API that can send and manage mailbox messages. The Starter plan advertises 1,000 messages/day; standard mailbox SMTP/IMAP access is also available. Transactional invitations are permitted when solicited and within limits. [Hostinger Mail API offer](https://www.hostinger.com/gr/mail-api) [Hostinger Agentic Mail](https://www.hostinger.com/support/how-to-use-agentic-mail-in-hostinger/) [Hostinger permitted email](https://www.hostinger.com/support/1583510-is-mass-mailing-supported-at-hostinger/)

The Greek 48-month prepaid offers per mailbox are:

| Plan | Intro | 48-month prepaid total | Renewal |
| --- | --- | --- | --- |
| Starter | €0.39/month | €18.72 ex VAT | €1.59/month for 48 months (€76.32 ex VAT) |
| Standard | €0.99/month | €47.52 ex VAT | €2.79/month for 48 months (€133.92 ex VAT) |
| Premium | €1.99/month | €95.52 ex VAT | €3.99/month for 48 months (€191.52 ex VAT) |

[Hostinger Greek email pricing](https://www.hostinger.com/gr/filoksenia-email)

Hostinger supports custom SPF and DKIM; its setup guidance recommends DMARC. Delivery logs show successful/failed outcomes and server errors in the control panel for 30 days. [Hostinger DNS authentication](https://www.hostinger.com/support/8650765-set-up-a-domain-for-hostinger-email/) [Hostinger delivery logs](https://www.hostinger.com/support/6404796-how-to-check-delivery-logs-for-hostinger-email/)

The decisive gaps for Tripper's reliable invitation outbox are:

- Agentic Mail documents only the inbound `message.received` webhook. It does not document outbound accepted, delivered, deferred, bounced, or complaint webhook events.
- The public docs do not expose an application-facing bounce/complaint suppression-management contract comparable to Mailgun's. Agentic Mail's allow/block list is mailbox send control, not automatic bounce/complaint suppression.
- The reviewed first-party material does not make a clear EU-only residency commitment for Hostinger Mail message/event data. Selecting a European VPS does not establish mailbox residency.
- Without delivery webhooks, an API timeout leaves the application's outbox with retry ambiguity: the message might have been accepted even though the response was lost. Tripper would need an idempotency guarantee or provider event identifier verified in API documentation and testing before relying on retries.

Mailgun Free currently provides 100 messages/day, a REST API and SMTP relay, one custom sending domain, tracking/analytics/webhooks, two API keys, and one day of logs at $0. Its EU region keeps message data, events, suppressions, mailing lists, tags, statistics, routes, and IP addresses region-bound. This is a better semantic match for invitation sending even though one-day logs require Tripper to ingest events promptly. [Mailgun pricing](https://www.mailgun.com/pricing/) [Mailgun regions](https://www.mailgun.com/about/regions/)

## Like-for-like costs

All euro amounts below exclude VAT; parenthesized values apply 24% Greek VAT for illustration. Mailgun Free adds $0. The Hetzner comparison uses current post-15-June-2026 CX23 pricing: €5.49/month, €0.50/month for IPv4, and the previously selected €6.49/month Object Storage base, totaling **€12.48/month**. Hetzner server backups add 20% of the server price, currently €1.098/month. [Hetzner 2026 price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/) [Hetzner IPv4 pricing](https://docs.hetzner.com/cloud/servers/primary-ips/overview/) [Hetzner backup billing](https://docs.hetzner.com/cloud/billing/faq/) [Hetzner Object Storage model](https://docs.hetzner.com/storage/object-storage/overview/)

| Design | Normalized monthly | 24-month total | Commitment |
| --- | ---: | ---: | --- |
| Hetzner CX23 + IPv4 + Object Storage | €12.48 (€15.48) | €299.52 (€371.40) | Hourly billing capped monthly; no 24-month prepayment |
| Same, plus Hetzner 7-slot server backup | €13.578 (€16.84) | €325.87 (€404.08) | Same flexibility |
| Hostinger KVM 1 promo + Hetzner Object Storage | €11.98 (€14.86) | €287.52 (€356.52) | €131.76 VPS portion prepaid for 24 months; only 1 vCPU |
| Hostinger KVM 2 promo + Hetzner Object Storage | €14.48 (€17.96) | €347.52 (€430.92) | €191.76 VPS portion prepaid for 24 months |
| Hostinger KVM 2 renewal + Hetzner Object Storage | €21.48 (€26.64) | €515.52 (€639.24) | Current regular rate, prepaid for 24 months |

Hostinger KVM 2 without off-host Object Storage is €7.99/month promotional (€191.76 ex VAT prepaid; €237.78 with illustrative VAT), but that is not like-for-like with the approved PostgreSQL recovery design. KVM 1 plus external storage is slightly cheaper during the promotion, but sacrifices half the vCPU count. KVM 2 is more expensive even in the introductory term and substantially more expensive at renewal.

The exact Hostinger first-purchase term, daily-backup add-on price, taxes, and selected-location availability must be verified in checkout. The public offer can change, and availability is capacity-dependent.

## Pre-cutover validation gates

Regardless of provider, do not cut over until all of these pass:

1. Confirm the final checkout price, VAT treatment, renewal date/amount, refund eligibility, selected German location/city, IPv4 and IPv6, and whether the offer is a 24-month prepayment.
2. Measure p50/p95 HTTPS latency from at least one Greek fixed connection and two Greek mobile networks over several periods. For Hostinger, provision under the refund window and compare Germany with the established Hetzner Nuremberg result; do not infer routing from geography alone.
3. Run sustained CPU, disk, and PostgreSQL workload checks; verify Docker Compose, firewall rules, IPv6, PTR, disk alerts, and container restart behavior.
4. Complete an encrypted `pgBackRest` full backup, continuous WAL archive, destructive clean-server restore, and point-in-time recovery. Prove the recovery key exists outside the VPS and provider account.
5. Keep Mailgun in the EU region; verify domain SPF, DKIM, and DMARC, webhook signatures, suppression behavior, outbox idempotency, and Gmail/Outlook/independent-mailbox delivery. Ingest webhook events within the one-day Free-plan retention window.
6. If reconsidering Hostinger Mail later, first prove through current API documentation and integration tests: a stable idempotency mechanism, outbound delivery/bounce/complaint webhooks, automatic suppression behavior, retry semantics, EU data location, and acceptable deliverability. The current public documentation does not establish these.
7. Test the documented clean rebuild runbook, external readiness/liveness checks, backup/WAL failure alerts, disk-pressure alerts, and a rollback from a pinned application image.

## Decision summary

Hostinger is a credible self-managed VPS provider and KVM 2 has ample resources for Tripper, but its apparent saving disappears when normalized to the same recoverability and after the introductory period. Its prepayment also gives Tripper less migration flexibility. The responsible first-release choice remains **Hetzner compute and Object Storage, PostgreSQL self-hosted with `pgBackRest`/WAL, and Mailgun Free EU**.
