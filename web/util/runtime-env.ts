declare global {
  interface Window {
    __APP_ENV__?: Record<string, string | undefined>;
  }
}

export function getPublicEnv(name: string): string | undefined {
  if (typeof window !== "undefined") {
    const runtimeValue = window.__APP_ENV__?.[name];
    if (runtimeValue) {
      return runtimeValue;
    }
  }

  const buildTimeValue = process.env[name];
  if (buildTimeValue) {
    return buildTimeValue;
  }

  return undefined;
}
