import React, { useEffect, useState } from "react";
import { Shield, User as UserIcon } from "lucide-react";

import { getSupabaseBrowserClient } from "@/util/supabase";

export function formatTokenCount(count: number): string {
  if (count <= 0) {
    return "0";
  }
  const k = Math.ceil(count / 1000);
  return `${k}k`;
}

export interface UserTypeUtils {
  getUserTypeIcon: (type: string) => React.ReactElement;
  getUserTypeColor: (type: string) => string;
  getUserTypeText: (type: string, t: (key: string) => string) => string;
  isAdminUser: (userType: string) => boolean;
}

export const getUserTypeIcon = (type: string): React.ReactElement => {
  switch (type) {
    case "admin":
      return <Shield className="w-2.5 h-2.5" />;
    case "user":
    default:
      return <UserIcon className="w-2.5 h-2.5" />;
  }
};

export const getUserTypeColor = (type: string) => {
  switch (type) {
    case "admin":
      return "bg-purple-50 text-purple-400 dark:bg-purple-950 dark:text-purple-500";
    case "user":
    default:
      return "bg-slate-50 text-slate-400 dark:bg-slate-900 dark:text-slate-500";
  }
};

export const getUserTypeText = (type: string, t: (key: string) => string) => {
  switch (type) {
    case "admin":
      return t("admin.users.filters.admin");
    case "user":
    default:
      return t("admin.users.filters.user");
  }
};

export const getAdminUserTypeText = (type: string, t: (key: string) => string) => {
  switch (type) {
    case "admin":
      return t("common.userTypes.admin");
    case "user":
    default:
      return t("common.userTypes.user");
  }
};

export const isAdminUser = (userType: string) => userType === "admin";

export const getMembershipLevelText = (level: string, t: (key: string) => string) => {
  switch (level) {
    case "monthly":
      return t("membership.monthly");
    case "yearly":
      return t("membership.yearly");
    case "free":
    default:
      return t("membership.free");
  }
};

export const useUserStatus = (userEmail: string) => {
  const [userType, setUserType] = useState<string>("user");
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const checkUserStatus = () => {
      const storedUserType = localStorage.getItem("user_type") || "user";
      setUserType(storedUserType);
      setIsAdmin(isAdminUser(storedUserType));
    };

    if (userEmail) {
      checkUserStatus();
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "user_type") {
        checkUserStatus();
      }
    };

    const handleUserTypeChange = () => {
      checkUserStatus();
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener("user-type-changed", handleUserTypeChange);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener("user-type-changed", handleUserTypeChange);
    };
  }, [userEmail]);

  return { userType, isAdmin };
};

export const handleLogout = async (
  router: { push: (path: string) => void },
  t: (key: string) => string,
  toast: { success: (message: string) => void }
) => {
  try {
    const supabase = getSupabaseBrowserClient();
    await supabase.auth.signOut();
  } catch (error) {
    console.error("Supabase sign out failed:", error);
  }

  localStorage.removeItem("user_type");
  window.dispatchEvent(new CustomEvent("user-type-changed"));
  router.push("/login");
  toast.success(t("auth.messages.logoutSuccess"));
};
