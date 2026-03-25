/** Minimal `window.Clerk` surface used by the API client (full SDK types are heavier). */
export {};

declare global {
  interface Window {
    Clerk?: {
      loaded?: boolean;
      session?: {
        getToken: (options?: { template?: string }) => Promise<string | null>;
      };
    };
  }
}
