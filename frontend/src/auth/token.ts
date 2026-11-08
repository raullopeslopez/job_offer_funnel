import { useSyncExternalStore } from "react";

// Single user: the API token lives in localStorage until the API rejects it.
const KEY = "funnel.authToken";
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) listener();
}

export function getToken(): string | null {
  return localStorage.getItem(KEY);
}

export function saveToken(token: string): void {
  localStorage.setItem(KEY, token);
  notify();
}

export function clearToken(): void {
  localStorage.removeItem(KEY);
  notify();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useToken(): string | null {
  return useSyncExternalStore(subscribe, getToken);
}
