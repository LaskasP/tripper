# Trip planning

The shared language for trips, their daily guides, and the people who maintain or follow them.

## Language

**Trip**:
A shareable journey with a stable identity, required date range, one or more destinations, and optional daily plans. Its details may change without making it a different trip.

**Destination**:
A named place visited during a trip, with its own timezone and an optional geographic point. A trip may include multiple destinations with different timezones.

**Creator**:
The one person with full authority over a particular trip and its management. A trip has exactly one creator at a time, and the same person can have a different role on another trip.
_Avoid_: Contributor, when referring to full trip authority.

**Contributor**:
A trip member permitted to maintain its planning content, including trip metadata, dates, and additions or removals of daily content, but not its membership, roles, ownership, or whole-trip existence.
_Avoid_: Creator, when referring only to content editing authority.

**Traveller**:
A signed-in member of a particular trip whose durable association makes the trip available through My Trips. A traveller has read-only access to its guide, including while the trip is a draft.
_Avoid_: Public visitor, when referring to an identified trip member.

**Trip membership**:
The durable relationship between a person and a particular trip, with exactly one effective creator, contributor, or traveller role. A pending invitation is not a trip membership.

**Participant**:
Any person with an accepted trip membership, regardless of whether their role is creator, contributor, or traveller.

**Trip invitation**:
A creator's time-limited offer to an intended person, identified by email, to join a particular trip as a contributor or traveller. It becomes membership only when accepted; while pending, it grants no participant access.

**Ownership handover**:
A creator's time-limited offer to an existing participant to become a trip's sole creator. Acceptance makes the recipient creator and the previous creator a contributor; until then, the current creator retains ownership.

**Trip roster**:
The member-only list of a trip's current participants, showing each participant's display name and trip role. It excludes pending invitees and former or removed participants.
_Avoid_: Traveller, when referring to participants of every role.

**My Trips**:
The collection of past and present trips in which a signed-in person currently has an accepted trip membership, with that person's role shown for each trip.
_Avoid_: Public trip directory, when referring to a person's own memberships.

**Public visitor**:
Someone who reads a published trip guide without needing to sign in.
Unlike a participant, a public visitor cannot view the trip roster.
_Avoid_: Traveller, when referring merely to an anonymous reader.

**Draft**:
The current state of a trip before its guide is published, or while publication is disabled. Every participant can read it, while only the creator and contributors can change its planning content. A trip does not maintain a separate draft after publication.

**Published guide**:
The trip's current saved guide content, deliberately made available to anyone with its unlisted public link. Successful content edits become public immediately. The published guide excludes the trip roster and any other private membership information.

**Public link**:
The stable, unlisted address through which anyone can read a published guide without signing in. Normal trip changes do not alter it. Its creator may disable it by unpublishing the guide or permanently replace it by rotating the link.

**Daily plan**:
The planning content for a particular date at a trip's primary destination for that date, which may include a summary, stay, scheduled activities, and photos. A daily plan may have no stay, activities, or photos.

**Unplanned date**:
A date within a trip's date range that has no daily plan. It remains visible in the guide as "Not planned yet".

**Timeline entry**:
An independent scheduled activity within a daily plan, identified by a title and local time, with optional description, place, and associated destination. Its local time uses the associated destination's timezone, or otherwise the daily plan's primary destination; equal or overlapping times do not imply alternatives or choices.

**Stay**:
The optional accommodation shown for a daily plan, identified by its name and any address, check-in, check-out, or public listing information. A daily plan has at most one stay; editing it does not change other dates showing the same accommodation.

**Public listing URL**:
An HTTPS address for an accommodation's publicly viewable listing. It is guide content, not a private reservation-management link.

**Location**:
A geographic point associated with a trip, stay, or timeline entry.
