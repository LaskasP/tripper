import {
  createInvitation,
  loadInvitations,
  replaceInvitation,
  revokeInvitation,
  type TripDetail,
  type TripInvitation,
} from "../../lib/trips";

function roleLabel(role: TripInvitation["role"]): string {
  return role[0].toUpperCase() + role.slice(1);
}

function deliveryLabel(status: TripInvitation["delivery_status"]): string {
  const labels: Record<TripInvitation["delivery_status"], string> = {
    pending: "Queued",
    delivering: "Sending",
    sent: "Submitted",
    failed: "Delivery failed",
    ambiguous: "Delivery uncertain",
    cancelled: "Cancelled",
    delivered: "Delivered",
    complained: "Complaint",
  };
  return labels[status];
}

export function createInvitationManager(trip: TripDetail): HTMLElement {
  const section = document.createElement("section");
  section.className = "invitation-manager";
  const title = document.createElement("h2");
  title.textContent = "Pending invitations";
  const status = document.createElement("p");
  status.className = "invitation-manager__status";
  status.setAttribute("role", "status");
  status.textContent = "Loading invitations…";
  const list = document.createElement("ul");
  list.className = "trip-planner__roster";
  const form = document.createElement("form");
  form.className = "invitation-manager__form";
  const emailLabel = document.createElement("label");
  emailLabel.textContent = "Email";
  const email = document.createElement("input");
  email.type = "email";
  email.required = true;
  email.autocomplete = "email";
  emailLabel.appendChild(email);
  const invitationRoleLabel = document.createElement("label");
  invitationRoleLabel.textContent = "Trip role";
  const role = document.createElement("select");
  for (const value of ["contributor", "traveller"] as const) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = roleLabel(value);
    role.appendChild(option);
  }
  invitationRoleLabel.appendChild(role);
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.textContent = "Send invitation";
  form.append(emailLabel, invitationRoleLabel, submit);

  const renderInvitations = (invitations: TripInvitation[]): void => {
    list.replaceChildren();
    for (const invitation of invitations) {
      const item = document.createElement("li");
      item.className = "trip-planner__roster-item invitation-manager__item";
      const details = document.createElement("span");
      details.textContent = `${invitation.email} · ${roleLabel(invitation.role)} · ${deliveryLabel(invitation.delivery_status)}`;
      const actions = document.createElement("span");
      actions.className = "invitation-manager__actions";
      const replace = document.createElement("button");
      replace.type = "button";
      replace.textContent = "Replace";
      replace.addEventListener("click", () => {
        if (!window.confirm(`Replace the invitation for ${invitation.email}? The previous link will stop working.`)) return;
        replace.disabled = true;
        void replaceInvitation(trip.id, invitation.id)
          .then((replacement) => {
            renderInvitations(invitations.map((current) =>
              current.id === invitation.id ? replacement : current));
            status.textContent = `Replacement queued for ${replacement.email}.`;
          })
          .catch((caught: unknown) => {
            status.textContent = caught instanceof Error ? caught.message : "Could not replace invitation.";
            replace.disabled = false;
          });
      });
      const revoke = document.createElement("button");
      revoke.type = "button";
      revoke.textContent = "Revoke";
      revoke.addEventListener("click", () => {
        if (!window.confirm(`Revoke the invitation for ${invitation.email}? Its link will stop working.`)) return;
        revoke.disabled = true;
        void revokeInvitation(trip.id, invitation.id)
          .then(() => {
            renderInvitations(invitations.filter(({ id }) => id !== invitation.id));
            status.textContent = `Invitation for ${invitation.email} revoked.`;
          })
          .catch((caught: unknown) => {
            status.textContent = caught instanceof Error ? caught.message : "Could not revoke invitation.";
            revoke.disabled = false;
          });
      });
      actions.append(replace, revoke);
      item.append(details, actions);
      list.appendChild(item);
    }
    if (invitations.length === 0) status.textContent = "No pending invitations.";
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit.disabled = true;
    status.textContent = "Queuing invitation…";
    void createInvitation(
      trip.id,
      email.value,
      role.value as TripInvitation["role"],
    )
      .then(async (created) => {
        email.value = "";
        renderInvitations(await loadInvitations(trip.id));
        status.textContent = `Invitation queued for ${created.email}.`;
      })
      .catch((caught: unknown) => {
        status.textContent = caught instanceof Error ? caught.message : "Could not queue invitation.";
      })
      .finally(() => { submit.disabled = false; });
  });

  section.append(title, form, status, list);
  void loadInvitations(trip.id)
    .then(renderInvitations)
    .catch((caught: unknown) => {
      status.textContent = caught instanceof Error ? caught.message : "Could not load invitations.";
    });
  return section;
}
