"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import { useLocale, useTranslations } from "next-intl";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import LangSwitchButton from "@/components/language-switch-button";
import ThemeToggleButton from "@/components/theme-toggle-button";
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
  const locale = useLocale();

  const [mode, setMode] = useState<AuthMode>("password-login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const [emailError, setEmailError] = useState("");
  const [usernameError, setUsernameError] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const copy = useMemo(
    () =>
      locale === "zh"
        ? {
            loginDescription: "连接你的交易研究工作区。",
            registerDescription: "创建账户后即可开始使用 Deltapex Agent。",
            resetDescription: "输入邮箱，我们会向你发送重置密码链接。",
            resetSent: "重置密码邮件已发送，请检查邮箱。",
            registerNeedsConfirm: "注册成功，请先完成邮箱确认，再返回登录。",
            registerComplete: "注册成功，正在进入系统。",
            resetLinkLabel: "忘记密码？",
            resetBack: "返回登录",
            heroEyebrow: "Deltapex Trading",
            heroTitle: "Order flow intelligence for every trading session.",
            heroDescription: "研究、问答、执行想法与会员体系统一在一套交易工作台里。",
          }
        : {
            loginDescription: "Access your trading workspace.",
            registerDescription: "Create an account and start using Deltapex Agent.",
            resetDescription: "Enter your email and we will send a reset password link.",
            resetSent: "Password reset email sent. Check your inbox.",
            registerNeedsConfirm: "Registration succeeded. Confirm your email before signing in.",
            registerComplete: "Registration succeeded. Redirecting now.",
            resetLinkLabel: "Forgot password?",
            resetBack: "Back to login",
            heroEyebrow: "Deltapex Trading",
            heroTitle: "Order flow intelligence for every trading session.",
            heroDescription: "Research, guided analysis, execution ideas, and member workflows in one desk.",
          },
    [locale]
  );

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
        throw new Error(locale === "zh" ? "登录失败，请重试。" : "Login failed. Please try again.");
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
      const emailRedirectTo =
        appUrl ? `${appUrl.replace(/\/$/, "")}/${locale}/login` : `${window.location.origin}/${locale}/login`;

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
        await finalizeSignedInUser(copy.registerComplete);
      } else {
        toast.success(copy.registerNeedsConfirm);
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
        getPublicEnv("NEXT_PUBLIC_SUPABASE_RESET_REDIRECT_URL") ||
        `${window.location.origin}/${locale}/reset-password`;

      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo,
      });

      if (error) {
        throw error;
      }

      toast.success(copy.resetSent);
      setMode("password-login");
    } catch (error) {
      const message = error instanceof Error ? error.message : t("auth.messages.resetFailed");
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const title =
    mode === "register"
      ? t("pages.login.register")
      : mode === "reset-request"
        ? t("pages.login.resetPassword")
        : t("pages.login.passwordLogin");

  const description =
    mode === "register"
      ? copy.registerDescription
      : mode === "reset-request"
        ? copy.resetDescription
        : copy.loginDescription;

  const submitHandler =
    mode === "register" ? handleRegister : mode === "reset-request" ? handleResetRequest : handlePasswordLogin;

  return (
    <div className="min-h-screen bg-[#f8fafc] px-4 py-6 text-slate-700 dark:bg-background dark:text-foreground">
      <div className="mx-auto flex w-full max-w-6xl justify-end gap-2 pb-4">
        <ThemeToggleButton />
        <LangSwitchButton />
      </div>

      <div className="mx-auto flex min-h-[760px] w-full max-w-6xl items-center justify-center rounded-lg border border-border/70 bg-card shadow-sm">
        <section className="flex w-full max-w-md items-center justify-center bg-white px-6 py-10 dark:bg-card">
          <form onSubmit={submitHandler} className={cn("flex w-full flex-col gap-6")}>
            <div className="flex flex-col gap-5">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-md border border-border/70 bg-white shadow-sm dark:bg-background">
                  <Image src="/deltapex-logo.jpg" alt="Deltapex Agent" width={34} height={34} className="object-contain" />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">{copy.heroEyebrow}</p>
                  <h1 className="text-2xl font-semibold text-slate-900 dark:text-foreground">Deltapex Agent</h1>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="text-3xl font-semibold text-slate-900 dark:text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
            </div>

            <div className="grid gap-5">
              <div className="grid gap-2">
                <Label htmlFor="email">{t("auth.fields.email")}</Label>
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
                  className={`h-11 border-slate-200 bg-slate-50 shadow-none focus-visible:border-primary focus-visible:ring-primary/20 dark:border-border dark:bg-background ${
                    emailError ? "border-red-500 focus-visible:ring-red-500" : ""
                  }`}
                />
                {emailError && <p className="text-sm text-red-500">{emailError}</p>}
              </div>

              {mode === "register" && (
                <div className="grid gap-2">
                  <Label htmlFor="username">{t("auth.fields.username")}</Label>
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
                    className={`h-11 border-slate-200 bg-slate-50 shadow-none focus-visible:border-primary focus-visible:ring-primary/20 dark:border-border dark:bg-background ${
                      usernameError ? "border-red-500 focus-visible:ring-red-500" : ""
                    }`}
                  />
                  {usernameError ? (
                    <p className="text-sm text-red-500">{usernameError}</p>
                  ) : (
                    <p className="text-xs text-muted-foreground">{t("common.validation.usernameLength")}</p>
                  )}
                </div>
              )}

              {mode !== "reset-request" && (
                <div className="grid gap-2">
                  <Label htmlFor="password">{t("auth.fields.password")}</Label>
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
                      className={`h-11 border-slate-200 bg-slate-50 pr-10 shadow-none focus-visible:border-primary focus-visible:ring-primary/20 dark:border-border dark:bg-background ${
                        passwordError ? "border-red-500 focus-visible:ring-red-500" : ""
                      }`}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-11 px-3 hover:bg-transparent"
                      onClick={() => setShowPassword((value) => !value)}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                  {passwordError && <p className="text-sm text-red-500">{passwordError}</p>}
                </div>
              )}

              <Button type="submit" className="h-11 w-full rounded-md bg-primary text-primary-foreground hover:bg-primary/90" disabled={loading}>
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
                      className="font-medium text-primary hover:underline"
                    >
                      {copy.resetLinkLabel}
                    </button>
                    <div className="flex justify-center gap-1">
                      <span className="text-muted-foreground">{t("pages.login.dontHaveAccount")}</span>
                      <button type="button" onClick={() => setMode("register")} className="font-medium text-primary hover:underline">
                        {t("pages.login.registerNow")}
                      </button>
                    </div>
                  </>
                )}

                {mode === "register" && (
                  <div className="flex justify-center gap-1">
                    <span className="text-muted-foreground">{t("pages.login.alreadyHaveAccount")}</span>
                    <button
                      type="button"
                      onClick={() => setMode("password-login")}
                      className="font-medium text-primary hover:underline"
                    >
                      {t("pages.login.backToLogin")}
                    </button>
                  </div>
                )}

                {mode === "reset-request" && (
                  <button
                    type="button"
                    onClick={() => setMode("password-login")}
                    className="font-medium text-primary hover:underline"
                  >
                    {copy.resetBack}
                  </button>
                )}
              </div>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
