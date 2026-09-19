# Low-cost EU PostgreSQL hosting for Tripper

Research current on **2026-09-19**. Prices exclude VAT unless stated otherwise. Currency conversion is deliberately avoided because exchange rates move; USD and EUR costs are shown separately.

## Decision summary

For Tripper's first release, use **one Hetzner CX23 in Germany or Finland for the Vite/FastAPI application and PostgreSQL, plus PostgreSQL-aware off-host backups in Hetzner Object Storage**. This is the cheaper predictable configuration once the database has regular public traffic: **EUR 10.98/month** before VAT (`EUR 5.49` server + `EUR 0.50` IPv4 + `EUR 4.99` object storage). Hetzner's optional daily whole-server backup adds about **EUR 1.10/month**, bringing the total to about **EUR 12.08/month**. It is useful for fast machine recovery, but it does not replace tested PostgreSQL base-backup/WAL recovery.

The strongest low-cost managed alternative is **the same CX23 application VPS plus Neon Launch in AWS Frankfurt**. Launch has no monthly minimum and costs `$0.106/CU-hour`, `$0.35/GB-month` for database storage, and `$0.20/GB-month` for retained history changes. At very low activity it can cost less than the self-hosted backup repository. At Neon's own example of 140 CU-hours and 1 GB, however, compute plus live storage is already about **$15.19/month** before history/snapshots, on top of the VPS.

The cash crossover is approximately when the Neon database bill reaches the **EUR 4.99/month** avoided object-storage base fee. Treating EUR and USD as roughly comparable only to express an operational trigger, a 1 GB database with about 1 GB-month of retained changes and one 1 GB snapshot leaves about `$4.35` for compute: roughly **41 CU-hours/month**. At the 0.25 CU minimum this is about **164 active database hours/month**, or roughly **2,000 isolated wake-ups/month** if every visit alone keeps the database active for Neon's five-minute idle window. Clustered traffic permits more visits for the same compute. Use actual Neon billing metrics, not the visit approximation, to make the decision.

Therefore:

- Choose the **single VPS** now if low recurring cash cost is the priority and one named operator will own patching, monitoring, backup alerts, and restore drills.
- Choose **Neon Launch immediately** if nobody will reliably own those duties, even if its eventual provider bill is higher.
- Reconsider moving from self-hosted PostgreSQL to managed PostgreSQL when a tested restore can no longer be completed within the tolerated outage, database operations consume recurring engineering time, the database needs independent failure isolation, or the projected Neon bill remains below about EUR 5/month. Cost alone favors self-hosting after roughly 41 CU-hours/month under the stated 1 GB assumptions.

Neither proposal is highly available: one VPS remains a single point of failure, and Neon Launch has no uptime SLA. That matches the stated lack of a contractual HA requirement.

## Concrete baseline

### Shared application/database VPS

Hetzner's current EU **CX23** has 2 shared vCPUs, 4 GB RAM, 40 GB NVMe storage, and 20 TB included traffic. It is available in Nuremberg and Helsinki; Hetzner also lists Falkenstein among its European locations. New-order pricing since 2026-06-15 is **EUR 5.49/month**, excluding IPv4 and VAT. A primary IPv4 is **EUR 0.50/month**; IPv6 is free. [CX23 specifications](https://www.hetzner.com/cloud/cost-optimized/), [2026 price adjustment](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/), [primary IP pricing](https://docs.hetzner.com/cloud/servers/primary-ips/overview/)

The 40 GB disk is shared by the OS, container images/releases, logs, PostgreSQL data, WAL, and temporary space. That is ample for a small Tripper database but requires alerts before the disk fills. There is no provider-imposed PostgreSQL connection limit; practical connection count is bounded by the 4 GB machine and should be kept small with an application pool.

PostgreSQL should listen only on loopback or an internal container network. The operator can select any upstream-supported PostgreSQL version, but also owns minor security updates, extensions, configuration, vacuum/tuning, major upgrades, and operating-system maintenance. PostgreSQL supports each major version for five years. [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)

### Off-host backup baseline

Hetzner's server backups are daily full-disk copies with seven rotating slots and cost **20% of the server price**. They can rebuild the same server or create a new server, but recovery loses changes after the selected backup; attached Volumes are not included. [backup behavior](https://docs.hetzner.com/cloud/servers/backups-snapshots/overview/), [backup billing](https://docs.hetzner.com/cloud/billing/faq/)

For a responsible database recovery path, configure encrypted `pgBackRest` base backups plus continuous WAL archiving to storage outside the VPS, retain at least two full backup chains, alert on failed archiving/backups, and perform a restore drill before launch and quarterly thereafter. PostgreSQL documents that base backups plus archived WAL enable point-in-time recovery; `pgBackRest` supports encryption, retention, restore verification, PITR, and S3-compatible repositories. [PostgreSQL continuous archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html), [pgBackRest user guide](https://pgbackrest.org/user-guide.html)

Hetzner Object Storage is S3-compatible in Falkenstein, Nuremberg, and Helsinki. Its **EUR 4.99/month** base price includes 1 TB storage and 1 TB egress; ingress, S3 operations, and internal EU-central traffic are free. This is far more capacity than Tripper needs, but it is the minimum account-level charge while a bucket exists. [Object Storage pricing announcement](https://www.hetzner.com/pressroom/object-storage/), [Object Storage behavior and regions](https://docs.hetzner.com/storage/object-storage/overview/)

Do not count a raw live-disk copy as the only PostgreSQL backup. PostgreSQL warns that file-system snapshots must be simultaneous/consistent; database-aware backup plus WAL is the portable, testable recovery mechanism. Hetzner's whole-server backup remains an optional second layer for quickly restoring the OS and application configuration.

## Managed alternative: Hetzner application VPS plus Neon Launch

Neon has AWS regions in **Frankfurt** and London. A project's region is immutable; changing region requires a new project and database migration. Place both the Hetzner VPS and Neon project in Germany/Frankfurt for the lowest expected latency. [Neon regions](https://neon.com/docs/introduction/regions)

Use the paid **Launch** plan, not Free, as the production baseline:

| Item | Launch limit or price |
| --- | --- |
| Minimum fee | None; pay for use |
| Compute | `$0.106/CU-hour` |
| Minimum compute size | 0.25 CU / 1 GB RAM |
| Scale to zero | After five idle minutes; can be disabled |
| Live storage | `$0.35/GB-month`; no hard paid-plan size cap |
| History/PITR data | `$0.20/GB-month` based on changes retained; window up to 7 days |
| Snapshots | 100 manual; scheduled daily/weekly/monthly snapshots are `$0.09/GB-month` |
| Network transfer | 500 GB/project included, then `$0.10/GB` |
| Direct connections at 0.25 CU | 104 |
| Pooled connections | Up to 10,000 client connections |
| Uptime SLA | None on Launch; SLA is a Scale feature |

Sources: [Neon plans and current unit prices](https://neon.com/docs/introduction/plans), [compute sizes and connection limits](https://neon.com/docs/manage/endpoints/), [Neon pricing](https://neon.com/pricing).

Neon currently supports PostgreSQL 14 through 18, applies new minor releases automatically on a compute restart, and aligns support with PostgreSQL's five-year window. A major-version upgrade is not in-place: create a new project at the target version and migrate. [Neon PostgreSQL version support](https://neon.com/docs/postgresql/postgres-version-support)

The application connects over the public internet because private networking and IP allowlisting are not Launch features. Neon rejects non-TLS connections and recommends `sslmode=verify-full`; keep the connection string in the VPS secret store/environment and restrict PostgreSQL credentials to the application role. [secure connections](https://neon.com/docs/connect/connect-securely)

For recovery, retain up to seven days of history and schedule snapshots. Neon restores a branch to a selected timestamp/LSN with a brief connection interruption, or restores a snapshot into a new branch for inspection/cutover. Keep an occasional encrypted logical `pg_dump` outside Neon as an independent, portable escape copy. [point-in-time restore](https://neon.com/blog/announcing-point-in-time-restore), [scheduled snapshots](https://neon.com/blog/three-ways-to-use-your-snapshots)

## Operational comparison

| Concern | App + PostgreSQL on one CX23 | CX23 app + Neon Launch |
| --- | --- | --- |
| Predictable minimum | EUR 10.98/month with off-host DB backups; about EUR 12.08 with optional server backups | EUR 5.99/month for VPS plus variable USD database usage; no Neon minimum |
| Failure domain | VPS, OS, disk, app, and database fail together | VPS failure leaves database intact; Neon or internet-path failure still makes database-backed features unavailable |
| Expected outage | Provision/rebuild VPS, restore base backup, replay WAL, redeploy app, verify | VPS rebuild is independent; PITR normally causes a brief reconnect, but provider outages are outside operator control |
| Backup/PITR | Operator configures, monitors, and tests all of it | Managed history and snapshots; operator still chooses retention, initiates restores, and should keep an independent dump |
| Maintenance | OS, firewall, TLS proxy, PostgreSQL minors/majors, disk/WAL, vacuum, backup jobs | Neon handles infrastructure and minor releases; operator handles schema, query performance, credentials, usage/cost, and major-version migration |
| Connections | No hard service cap; 4 GB RAM is the constraint | 104 direct at 0.25 CU; pooled endpoint up to 10,000 |
| Storage growth | 40 GB total machine disk; resize/migrate before it fills | Paid storage grows with usage at `$0.35/GB-month` |
| Downtime during maintenance | OS/PostgreSQL restart and major upgrades are operator-scheduled outages | Compute can cold-start after idle; minor update applies on restart; major upgrade requires a new project/migration |
| Portability | Standard PostgreSQL on a conventional Linux host; highest control | Standard PostgreSQL wire protocol and dumps; extensions/settings differ, and region/project migration is explicit |
| Support/SLA | Hetzner advertises 99.9% cloud uptime, but the design has one node | Launch has billing support but no uptime SLA |

### Restore runbooks

**Single VPS:** create a fresh CX23, apply infrastructure configuration, install the same PostgreSQL major and `pgBackRest`, restore the latest base backup from Object Storage, replay WAL to the chosen time, deploy the application, run integrity/smoke checks, then repoint the custom domain if the IP changed. Keep the old server isolated until verification. The restore drill must measure this path rather than assume a recovery time.

**Neon:** use Time Travel Assist/branch restore to validate the target timestamp, restore the production branch (briefly disconnecting clients) or create a recovery branch and switch the application connection string, then run integrity/smoke checks. A region or major-version move instead requires creating a new project and migrating data.

## Free tiers and cheaper-looking alternatives

They are useful for development but should not define the production decision:

- **Neon Free** currently includes 100 CU-hours/project, 0.5 GB storage, 5 GB transfer, a five-minute scale-to-zero policy, and only a six-hour/1 GB-month history window. It is described for prototypes, side projects, and small teams; it has no SLA. Hitting a project quota can suspend its compute. Current AWS-region documentation does not state an inactivity-deletion policy, but that absence is not a durability guarantee. [Neon plans](https://neon.com/docs/introduction/plans)
- **Aiven Developer** starts at `$5/month`, has 8 GB disk and daily backup, but Aiven explicitly calls it a test/personal tier without PITR, advanced networking, provider/region selection, or production positioning. [Aiven Developer tier](https://aiven.io/blog/new-developer-tier-for-aiven-for-postgres)
- **DigitalOcean** single-node managed PostgreSQL starts at `$15/month` with 1 GiB RAM; DigitalOcean recommends the single-node shape for development/testing. HA starts with a `$30` primary plus at least one matching `$30` standby. [DigitalOcean PostgreSQL pricing](https://docs.digitalocean.com/products/databases/postgresql/details/pricing/)
- **Supabase Free** pauses after one inactive week and has no automatic backups. Pro starts at `$25/month` with seven daily backups; seven-day PITR is about another `$100/month` and requires at least Small compute. [Supabase pricing](https://supabase.com/pricing), [Supabase backup documentation](https://supabase.com/docs/guides/platform/backups)

These checks make Neon Launch the only examined managed option that can be both responsibly recoverable and cheaper than the self-hosted/off-host-backup baseline at Tripper's very lowest activity level. It is not necessarily cheaper once anonymous reading produces regular database wake time.

## Acceptance guardrails for either implementation

Before cutover, demonstrate all of the following:

1. PostgreSQL is not publicly reachable on the one-VPS design; Neon uses `sslmode=verify-full` on the managed design.
2. Backup monitoring alerts on a missed base backup or failed WAL/archive operation.
3. A clean restore into a separate target succeeds, migrations apply, row counts/integrity checks pass, and the application smoke test passes.
4. The measured recovery time and last recoverable timestamp are recorded.
5. Disk usage (self-hosted) or compute/storage spending (Neon) has warning thresholds.
6. Major-version and provider-exit procedures are documented around `pg_dump`/`pg_restore`; provider-native recovery is not the only copy.

