import { getSupabaseBrowserClient } from "@/util/supabase";

export function getApiUrl() {
  if (process.env.NODE_ENV === "development") {
    return process.env.NEXT_PUBLIC_API_URL;
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
