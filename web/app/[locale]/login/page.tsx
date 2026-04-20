"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import InteractiveHeroBackground from "@/components/marketing/interactive-hero-background";
import GlassPanel from "@/components/marketing/glass-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import { fetcher } from "@/util/fetcher";
import { getPublicEnv } from "@/util/runtime-env";
import { getSupabaseBrowserClient } from "@/util/supabase";

type AuthMode = "password-login" | "register" | "reset-request";

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidUsername(username: string) {
  if (!username || username.length < 4 || username.length > 12) {
    return false;
  }
  return /^[a-zA-Z0-9_]+$/.test(username);
}

function isValidPassword(password: string) {
  return password.length >= 6;
}

export default function LoginPage() {
  const t = useTranslations();
  const router = useRouter();

  const [mode, setMode] = useState<AuthMode>("password-login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const [emailError, setEmailError] = useState("");
  const [usernameError, setUsernameError] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const validateForm = () => {
    let valid = true;
    setEmailError("");
    setUsernameError("");
    setPasswordError("");

    if (!isValidEmail(email)) {
      setEmailError(t("common.validation.emailFormat"));
      valid = false;
    }

    if (mode === "register" && !isValidUsername(username)) {
      setUsernameError(
        username.length < 4 || username.length > 12
          ? t("common.validation.usernameLength")
          : t("common.validation.usernameFormat")
      );
      valid = false;
    }

    if (mode !== "reset-request" && !isValidPassword(password)) {
      setPasswordError(t("common.validation.passwordLength"));
      valid = false;
    }

    return valid;
  };

  const finalizeSignedInUser = async (successMessage: string) => {
    const userProfile = (await fetcher("/auth/me", {
      method: "GET",
      auth: true,
    })) as { user_type: string } | undefined;

    const userType = userProfile?.user_type || "user";
    localStorage.setItem("user_type", userType);
    window.dispatchEvent(new CustomEvent("user-type-changed"));

    toast.success(successMessage);
    setTimeout(() => {
      router.push(userType === "admin" ? "/admin" : "/");
    }, 600);
  };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        throw error;
      }

      if (!data.session) {
        throw new Error("Login failed. Please try again.");
      }

      await finalizeSignedInUser(t("auth.messages.loginSuccess"));
    } catch (error) {
      const message = error instanceof Error ? error.message : t("auth.messages.loginFailed");
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const appUrl = getPublicEnv("NEXT_PUBLIC_APP_URL");
      const emailRedirectTo = appUrl ? `${appUrl.replace(/\/$/, "")}/zh/login` : `${window.location.origin}/zh/login`;

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { username },
          emailRedirectTo,
        },
      });

      if (error) {
        throw error;
      }

      if (data.session) {
        await finalizeSignedInUser(t("marketing.login.registerComplete"));
      } else {
        toast.success(t("marketing.login.registerNeedsConfirm"));
        setMode("password-login");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("auth.messages.registerFailed");
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const redirectTo =
        getPublicEnv("NEXT_PUBLIC_SUPABASE_RESET_REDIRECT_URL") || `${window.location.origin}/zh/reset-password`;

      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo,
      });

      if (error) {
        throw error;
      }

      toast.success(t("marketing.login.resetSent"));
      setMode("password-login");
    } catch (error) {
      const message = error instanceof Error ? error.message : t("auth.messages.resetFailed");
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const description =
    mode === "register"
      ? t("marketing.login.registerDescription")
      : mode === "reset-request"
        ? t("marketing.login.resetDescription")
        : t("marketing.login.loginDescription");

  const descriptionNode =
    mode === "password-login" ? (
      <div className="flex h-[4rem] items-end overflow-visible sm:h-[4.7rem]">
        <div className="inline-flex -translate-y-1 items-end gap-0.5 pb-2 sm:-translate-y-1.5">
          <span className="animate-brand-shimmer inline-block bg-[linear-gradient(90deg,#7f1d1d_0%,#d32f2f_18%,#fb7185_34%,#ffffff_48%,#fb7185_62%,#d32f2f_78%,#7f1d1d_100%)] bg-[length:220%_100%] bg-clip-text text-[2.35rem] font-bold leading-none text-transparent drop-shadow-[0_10px_18px_rgba(211,47,47,0.16)] sm:text-[2.8rem]">
            D
          </span>
          <span className="animate-brand-shimmer inline-block bg-[linear-gradient(90deg,#7f1d1d_0%,#d32f2f_18%,#fb7185_34%,#ffffff_48%,#fb7185_62%,#d32f2f_78%,#7f1d1d_100%)] bg-[length:220%_100%] bg-clip-text text-[1.72rem] font-semibold leading-none tracking-[0.01em] text-transparent sm:text-[2.05rem]">
            eltapex-Agent
          </span>
        </div>
      </div>
    ) : (
      <p className="text-sm leading-7 text-slate-600">{description}</p>
    );

  const submitHandler =
    mode === "register" ? handleRegister : mode === "reset-request" ? handleResetRequest : handlePasswordLogin;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f6f3f1] text-slate-900">
      <InteractiveHeroBackground />

      <div className="relative z-10 flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
        <GlassPanel className="w-full max-w-xl border-[#e9dfd7] bg-white/96 p-8 shadow-[0_28px_80px_rgba(15,23,42,0.10)] sm:p-10">
          <form onSubmit={submitHandler} className="flex flex-col gap-7">
            <div className="space-y-3">
              {descriptionNode}
            </div>

            <div className="mt-3 grid gap-6">
              <div className="grid gap-2.5">
                <Label htmlFor="email" className="text-[15px] text-slate-700">
                  {t("auth.fields.email")}
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder={t("auth.placeholders.enterEmail")}
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (emailError) setEmailError("");
                  }}
                  maxLength={60}
                  required
                  autoFocus
                  className={cn(
                    "h-14 rounded-md border-[#e7ddd6] bg-[#fdfbfa] px-4 text-base text-slate-900 shadow-none placeholder:text-slate-400 focus-visible:border-[#d32f2f]/50 focus-visible:ring-[#d32f2f]/20",
                    emailError ? "border-[#d32f2f]/60 focus-visible:ring-[#d32f2f]/25" : ""
                  )}
                />
                {emailError && <p className="text-sm text-[#d32f2f]">{emailError}</p>}
              </div>

              {mode === "register" && (
                <div className="grid gap-2.5">
                  <Label htmlFor="username" className="text-[15px] text-slate-700">
                    {t("auth.fields.username")}
                  </Label>
                  <Input
                    id="username"
                    type="text"
                    placeholder={t("common.placeholders.username")}
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      if (usernameError) setUsernameError("");
                    }}
                    maxLength={12}
                    required
                    className={cn(
                      "h-14 rounded-md border-[#e7ddd6] bg-[#fdfbfa] px-4 text-base text-slate-900 shadow-none placeholder:text-slate-400 focus-visible:border-[#d32f2f]/50 focus-visible:ring-[#d32f2f]/20",
                      usernameError ? "border-[#d32f2f]/60 focus-visible:ring-[#d32f2f]/25" : ""
                    )}
                  />
                  {usernameError ? (
                    <p className="text-sm text-[#d32f2f]">{usernameError}</p>
                  ) : (
                    <p className="text-xs text-slate-500">{t("common.validation.usernameLength")}</p>
                  )}
                </div>
              )}

              {mode !== "reset-request" && (
                <div className="grid gap-2.5">
                  <Label htmlFor="password" className="text-[15px] text-slate-700">
                    {t("auth.fields.password")}
                  </Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      placeholder={t("auth.placeholders.enterPassword")}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (passwordError) setPasswordError("");
                      }}
                      required
                      className={cn(
                        "h-14 rounded-md border-[#e7ddd6] bg-[#fdfbfa] px-4 pr-12 text-base text-slate-900 shadow-none placeholder:text-slate-400 focus-visible:border-[#d32f2f]/50 focus-visible:ring-[#d32f2f]/20",
                        passwordError ? "border-[#d32f2f]/60 focus-visible:ring-[#d32f2f]/25" : ""
                      )}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-14 px-4 text-slate-400 hover:bg-transparent hover:text-slate-700"
                      onClick={() => setShowPassword((value) => !value)}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                  {passwordError && <p className="text-sm text-[#d32f2f]">{passwordError}</p>}
                </div>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="h-14 rounded-md bg-[#d32f2f] text-[17px] font-semibold text-white shadow-[0_16px_36px_rgba(211,47,47,0.24)] hover:bg-[#b71c1c]"
              >
                {loading
                  ? mode === "register"
                    ? t("auth.actions.registering")
                    : mode === "reset-request"
                      ? t("auth.actions.resettingPassword")
                      : t("auth.actions.loggingIn")
                  : mode === "register"
                    ? t("pages.login.registerButton")
                    : mode === "reset-request"
                      ? t("pages.login.resetPasswordButton")
                      : t("pages.login.loginButton")}
              </Button>

              <div className="flex flex-col gap-2 text-center text-sm">
                {mode === "password-login" && (
                  <>
                    <button
                      type="button"
                      onClick={() => setMode("reset-request")}
                      className="font-medium text-[#d32f2f] transition hover:text-[#b71c1c]"
                    >
                      {t("marketing.login.resetLinkLabel")}
                    </button>
                    <div className="flex justify-center gap-1">
                      <span className="text-slate-500">{t("pages.login.dontHaveAccount")}</span>
                      <button
                        type="button"
                        onClick={() => setMode("register")}
                        className="font-medium text-[#d32f2f] transition hover:text-[#b71c1c]"
                      >
                        {t("pages.login.registerNow")}
                      </button>
                    </div>
                  </>
                )}

                {mode === "register" && (
                  <div className="flex justify-center gap-1">
                    <span className="text-slate-500">{t("pages.login.alreadyHaveAccount")}</span>
                    <button
                      type="button"
                      onClick={() => setMode("password-login")}
                      className="font-medium text-[#d32f2f] transition hover:text-[#b71c1c]"
                    >
                      {t("pages.login.backToLogin")}
                    </button>
                  </div>
                )}

                {mode === "reset-request" && (
                  <button
                    type="button"
                    onClick={() => setMode("password-login")}
                    className="font-medium text-[#d32f2f] transition hover:text-[#b71c1c]"
                  >
                    {t("marketing.login.resetBack")}
                  </button>
                )}
              </div>
            </div>
          </form>
        </GlassPanel>
      </div>
    </div>
  );
}
