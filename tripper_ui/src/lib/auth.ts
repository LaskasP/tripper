interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleAccountsApi {
  id: {
    initialize(options: {
      client_id: string;
      callback: (response: GoogleCredentialResponse) => void;
    }): void;
    renderButton(element: HTMLElement, options: Record<string, string>): void;
  };
}

declare global {
  interface Window {
    google?: { accounts: GoogleAccountsApi };
  }
}

function cookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

async function loadGoogleScript(): Promise<void> {
  if (window.google) return;
  await new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Google sign-in could not be loaded."));
    document.head.appendChild(script);
  });
}

export async function renderGoogleSignIn(
  container: HTMLElement,
  onSignedIn: () => void,
): Promise<void> {
  const configResponse = await fetch("/api/auth/google/config");
  if (!configResponse.ok) throw new Error("Google sign-in is unavailable.");
  const config = (await configResponse.json()) as { client_id: string };
  await loadGoogleScript();
  const csrf = crypto.randomUUID();
  document.cookie = `g_csrf_token=${encodeURIComponent(csrf)}; Path=/; Secure; SameSite=Lax`;
  window.google?.accounts.id.initialize({
    client_id: config.client_id,
    callback: async ({ credential }) => {
      const form = new URLSearchParams({ credential, g_csrf_token: csrf });
      const response = await fetch("/api/auth/google", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form,
      });
      if (!response.ok) throw new Error("Google sign-in failed.");
      onSignedIn();
    },
  });
  window.google?.accounts.id.renderButton(container, {
    theme: "outline",
    size: "large",
    text: "signin_with",
  });
  container.querySelectorAll("button").forEach((button) => {
    button.type = "button";
  });
}

export async function signOut(): Promise<void> {
  const csrf = cookie("tripper_csrf");
  const response = await fetch("/api/auth/sign-out", {
    method: "POST",
    credentials: "include",
    headers: csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {},
  });
  if (!response.ok) throw new Error("Sign out failed.");
  clearTripDrafts();
}

export interface CurrentAccount {
  id: string;
  email: string;
  display_name: string;
}

export async function loadCurrentAccount(): Promise<CurrentAccount> {
  const response = await fetch("/api/auth/session", { credentials: "include" });
  if (!response.ok) throw new Error("Sign in to manage your trips.");
  const session = (await response.json()) as { account: CurrentAccount };
  prepareTripDraftsForAccount(session.account.id);
  return session.account;
}

export function sessionCsrfToken(): string | undefined {
  const value = cookie("tripper_csrf");
  return value ? decodeURIComponent(value) : undefined;
}
import { clearTripDrafts, prepareTripDraftsForAccount } from "./drafts";
