export interface ApplicationConfig {
  invitations_enabled: boolean;
}

export async function loadApplicationConfig(): Promise<ApplicationConfig> {
  const response = await fetch("/api/config");
  if (!response.ok) throw new Error("Application configuration is unavailable.");
  return (await response.json()) as ApplicationConfig;
}
