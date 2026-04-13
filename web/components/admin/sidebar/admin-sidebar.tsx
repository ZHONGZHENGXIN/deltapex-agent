"use client"

import * as React from "react"
// import { useState, useEffect } from "react"
import Image from "next/image"
import { useTranslations } from 'next-intl'

import { BarChart3, Users, MessageSquare, Bot, Package } from "lucide-react"

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
} from "@/components/ui/sidebar"
import { NavUser } from "@/components/admin/sidebar/nav-user"
import { useGlobalUserData } from '@/hooks/use-global-user-data'

export interface AdminSidebarProps extends React.ComponentProps<typeof Sidebar> {
  currentPage: string;
  onNavigate: (page: string) => void;
}

export function AdminSidebar({ currentPage, onNavigate, ...props }: AdminSidebarProps) {
  const t = useTranslations();
  const { userProfile } = useGlobalUserData();
  
  // 从全局用户数据中获取用户信息，如果没有则使用默认值
  const email = userProfile?.email || 'admin@example.com';
  const username = userProfile?.username || userProfile?.email?.split('@')[0] || 'Admin';

  const navigationItems = [
    {
      id: 'dashboard',
      label: t('admin.navigation.dashboard'),
      icon: <BarChart3 className="w-4 h-4" />,
    },
    {
      id: 'agents',
      label: t('admin.navigation.agentManagement'),
      icon: <Bot className="w-4 h-4" />,
    },
    {
      id: 'chats',
      label: t('admin.navigation.chatManagement'),
      icon: <MessageSquare className="w-4 h-4" />,
    },
    {
      id: 'users',
      label: t('admin.navigation.userManagement'),
      icon: <Users className="w-4 h-4" />,
    },
    {
      id: 'orders',
      label: t('admin.navigation.orderManagement'),
      icon: <Package className="w-4 h-4" />,
    },
  ];

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
                <span className="text-xs text-muted-foreground">Admin console</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent className="border-y border-sidebar-border/70 bg-sidebar p-2">
        <SidebarMenu>
          {navigationItems.map((item) => (
            <SidebarMenuItem key={item.id}>
              <SidebarMenuButton
                size="lg"
                onClick={() => onNavigate(item.id)}
                isActive={currentPage === item.id}
                className="group-data-[collapsible=icon]:!justify-center gap-4 rounded-md px-4 text-sidebar-foreground transition-colors hover:bg-accent hover:text-accent-foreground data-[active=true]:bg-accent data-[active=true]:text-accent-foreground"
                tooltip={item.label}
              >
                {item.icon}
                <span className="group-data-[collapsible=icon]:hidden">{item.label}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      
      <SidebarFooter>
        <NavUser user={{ name: username, email: email }} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
