declare global {
  interface Window {
    __APP_ENV__?: Record<string, string | undefined>;
  }
}

export function getPublicEnv(name: string): string | undefined {
  const buildTimeValue = process.env[name];
  if (buildTimeValue) {
    return buildTimeValue;
  }

  if (typeof window !== "undefined") {
    return window.__APP_ENV__?.[name];
  }

  return undefined;
}

