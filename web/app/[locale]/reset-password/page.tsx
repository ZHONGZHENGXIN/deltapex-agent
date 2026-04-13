"use client";

import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRouter } from "@/i18n/navigation";
import { getSupabaseBrowserClient } from "@/util/supabase";

function isValidPassword(password: string) {
  return password.length >= 6;
}

export default function ResetPasswordPage() {
  const t = useTranslations();
  const locale = useLocale();
  const router = useRouter();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hasRecoverySession, setHasRecoverySession] = useState(false);

  const copy = useMemo(
    () =>
      locale === "zh"
        ? {
            title: "设置新密码",
            description: "通过邮件链接验证后，在这里提交你的新密码。",
            confirmLabel: "确认新密码",
            confirmPlaceholder: "再次输入新密码",
            invalidSession: "重置链接无效或已过期，请重新发起找回密码。",
            passwordMismatch: "两次输入的密码不一致。",
            success: "密码已更新，请重新登录。",
            submit: "更新密码",
          }
        : {
            title: "Set a new password",
            description: "After opening the recovery link from email, submit your new password here.",
            confirmLabel: "Confirm new password",
            confirmPlaceholder: "Enter the new password again",
            invalidSession: "This recovery link is invalid or expired. Request a new password reset email.",
            passwordMismatch: "The two passwords do not match.",
            success: "Password updated. Please sign in again.",
            submit: "Update password",
          },
    [locale]
  );

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();

    const syncSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      setHasRecoverySession(Boolean(session));
    };

    void syncSession();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setHasRecoverySession(Boolean(session));
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!hasRecoverySession) {
      toast.error(copy.invalidSession);
      return;
    }

    if (!isValidPassword(password)) {
      toast.error(t("common.validation.passwordLength"));
      return;
    }

    if (password !== confirmPassword) {
      toast.error(copy.passwordMismatch);
      return;
    }

    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const { error } = await supabase.auth.updateUser({ password });
      if (error) {
        throw error;
      }

      await supabase.auth.signOut();
      localStorage.removeItem("user_type");
      window.dispatchEvent(new CustomEvent("user-type-changed"));
      toast.success(copy.success);
      router.push("/login");
    } catch (error) {
      const message = error instanceof Error ? error.message : t("auth.messages.resetFailed");
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f8fafc] p-4 dark:bg-background">
      <div className="w-full max-w-md rounded-lg border border-border/70 bg-white p-8 shadow-sm dark:bg-card">
        <div className="mb-6 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">Deltapex Trading</p>
          <h1 className="mt-3 text-2xl font-semibold">{copy.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{copy.description}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="password">{t("auth.fields.newPassword")}</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t("auth.placeholders.enterNewPassword")}
                className="pr-10 border-slate-200 bg-slate-50 shadow-none focus-visible:border-primary focus-visible:ring-primary/20 dark:border-border dark:bg-background"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                onClick={() => setShowPassword((value) => !value)}
              >
                {showPassword ? <EyeOff className="h-4 w-4 text-muted-foreground" /> : <Eye className="h-4 w-4 text-muted-foreground" />}
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">{copy.confirmLabel}</Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={copy.confirmPlaceholder}
                className="pr-10 border-slate-200 bg-slate-50 shadow-none focus-visible:border-primary focus-visible:ring-primary/20 dark:border-border dark:bg-background"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                onClick={() => setShowConfirmPassword((value) => !value)}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
          </div>

          {!hasRecoverySession && <p className="text-sm text-red-500">{copy.invalidSession}</p>}

          <Button type="submit" className="w-full bg-primary text-primary-foreground hover:bg-primary/90" disabled={loading || !hasRecoverySession}>
            {loading ? t("auth.actions.resettingPassword") : copy.submit}
          </Button>
        </form>
      </div>
    </div>
  );
}
