import { getSupabaseBrowserClient } from "@/util/supabase";
import { getPublicEnv } from "@/util/runtime-env";

const ABSOLUTE_URL_PATTERN = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//;

function normalizeApiUrl(value: string): string {
  let normalizedValue = value.trim();

  if (!normalizedValue) {
    return normalizedValue;
  }

  if (normalizedValue.startsWith("//")) {
    normalizedValue = `https:${normalizedValue}`;
  } else if (!ABSOLUTE_URL_PATTERN.test(normalizedValue)) {
    normalizedValue = `https://${normalizedValue}`;
  }

  normalizedValue = normalizedValue.replace(/\/+$/, "");
  normalizedValue = normalizedValue.replace(/\/api\/v1$/i, "");

  return normalizedValue;
}

export function getApiUrl() {
  const publicApiUrl = getPublicEnv("NEXT_PUBLIC_API_URL");
  if (publicApiUrl) {
    return normalizeApiUrl(publicApiUrl);
  }
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  return "http://localhost:8080";
}

export async function getValidAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const supabase = getSupabaseBrowserClient();
    const {
      data: { session },
      error,
    } = await supabase.auth.getSession();

    if (error) {
      console.error("Failed to get Supabase session:", error);
      return null;
    }

    return session?.access_token ?? null;
  } catch (error) {
    console.error("Failed to get access token:", error);
    return null;
  }
}
