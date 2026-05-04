"use client"

import * as React from "react"
import { useEffect, useCallback } from "react"
import Image from "next/image"
import { useTranslations } from 'next-intl'

import { PlusCircleIcon, Command } from "lucide-react"

import { Avatar } from "@/components/ui/avatar"
import {
  Sidebar,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarMenuBadge,
} from "@/components/ui/sidebar"
import { NavChatList } from "@/components/sidebar/nav-chat-list"
import { NavUser } from "@/components/sidebar/nav-user"
import { useGlobalUserData } from '@/hooks/use-global-user-data'
import type { Chat } from "@/app/[locale]/types" 

export interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  onSelectChat?: (chat: Chat) => void;
  onNewChat?: () => void;
  chats: Chat[];
  currentChatId?: string;
}

export function AppSidebar({ onSelectChat, onNewChat, chats, currentChatId, ...props }: AppSidebarProps) {
  const t = useTranslations();
  const { userProfile } = useGlobalUserData();
  
  // 从全局用户数据中获取用户信息，如果没有则使用默认值
  const email = userProfile?.email || 'not_found@example.com';
  const username = userProfile?.username || 'User';

  // Handle new chat shortcut
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'i') {
      event.preventDefault();
      onNewChat?.();
    }
  }, [onNewChat]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader className="border-b border-sidebar-border/70 px-3 py-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="h-auto cursor-default gap-3 px-2 py-1 hover:bg-transparent active:bg-transparent">
              <Avatar className="h-10 w-10 rounded-md border border-border/70 bg-white">
                <Image src="/deltapex-logo.jpg" alt="Deltapex Agent" width={32} height={32} className="object-contain" />
              </Avatar>
              <div className="grid text-left leading-tight">
                <span className="text-sm font-semibold tracking-wide text-foreground">Deltapex Agent</span>
                <span className="text-xs text-muted-foreground">Trading intelligence workspace</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <SidebarMenu className="mt-3">
          <SidebarMenuItem className="flex items-center gap-2">
            <SidebarMenuButton
              tooltip="New Chat"
              className="rounded-md border border-border/70 bg-card text-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground"
              onClick={onNewChat}
            >
              <PlusCircleIcon className="text-primary" />
              <span>{t('chat.newChat')}</span>
              <SidebarMenuBadge className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
                <Command className="w-3 h-3" />
                <span>I</span>
              </SidebarMenuBadge>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent className="border-y border-sidebar-border/70 bg-sidebar">
        <NavChatList
          chats={chats}
          onSelectChat={onSelectChat}
          currentChatId={currentChatId}
        />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={{ name: username, email: email }} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
