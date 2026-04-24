'use client'

import React, {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { MembershipPlan, MembershipStatus } from '@/app/[locale]/admin/types'
import type { UserProfile } from '@/util/auth'
import { getUserProfile } from '@/util/auth'
import { getValidAccessToken } from '@/util/token'
import type { OrderResponse, TokenPackage, TokenTopupOrder, TokenWallet } from '@/util/user-api'
import {
  getMembershipPlans,
  getTokenPackages,
  getTokenTopupOrders,
  getTokenWallet,
  getUserMembershipStatus,
  getUserOrders,
} from '@/util/user-api'

interface GlobalUserData {
  userProfile: UserProfile | null
  userProfileLoading: boolean
  membershipStatus: MembershipStatus | null
  membershipStatusLoading: boolean
  membershipPlans: MembershipPlan[]
  membershipPlansLoading: boolean
  userOrders: OrderResponse[]
  userOrdersLoading: boolean
  pendingOrders: OrderResponse[]
  tokenWallet: TokenWallet | null
  tokenWalletLoading: boolean
  tokenPackages: TokenPackage[]
  tokenPackagesLoading: boolean
  tokenTopupOrders: TokenTopupOrder[]
  tokenTopupOrdersLoading: boolean
  refreshUserProfile: () => Promise<void>
  refreshMembershipStatus: () => Promise<void>
  refreshMembershipPlans: () => Promise<void>
  refreshUserOrders: (status?: string) => Promise<void>
  refreshTokenWallet: () => Promise<void>
  refreshTokenPackages: () => Promise<void>
  refreshTokenTopupOrders: (params?: { request_id?: string; checkout_id?: string; order_number?: string }) => Promise<void>
  refreshAllData: () => Promise<void>
}

const GlobalUserDataContext = createContext<GlobalUserData | undefined>(undefined)

const DEFAULT_MEMBERSHIP_STATUS: MembershipStatus = {
  has_membership: false,
  membership_type: 'free',
  plan_name: '免费会员',
  daily_message_limit: 100,
  daily_token_limit: 1_000_000,
  conversation_turn_limit: 10,
  daily_message_count: 0,
  daily_token_count: 0,
  daily_chat_count: 0,
  daily_message_remaining: 100,
  daily_token_remaining: 1_000_000,
  total_message_count: 0,
  total_token_count: 0,
  total_chat_count: 0,
}

export function GlobalUserDataProvider({ children }: { children: ReactNode }) {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [userProfileLoading, setUserProfileLoading] = useState(false)
  const [membershipStatus, setMembershipStatus] = useState<MembershipStatus | null>(null)
  const [membershipStatusLoading, setMembershipStatusLoading] = useState(false)
  const [membershipPlans, setMembershipPlans] = useState<MembershipPlan[]>([])
  const [membershipPlansLoading, setMembershipPlansLoading] = useState(false)
  const [userOrders, setUserOrders] = useState<OrderResponse[]>([])
  const [userOrdersLoading, setUserOrdersLoading] = useState(false)
  const [tokenWallet, setTokenWallet] = useState<TokenWallet | null>(null)
  const [tokenWalletLoading, setTokenWalletLoading] = useState(false)
  const [tokenPackages, setTokenPackages] = useState<TokenPackage[]>([])
  const [tokenPackagesLoading, setTokenPackagesLoading] = useState(false)
  const [tokenTopupOrders, setTokenTopupOrders] = useState<TokenTopupOrder[]>([])
  const [tokenTopupOrdersLoading, setTokenTopupOrdersLoading] = useState(false)

  const isFetchingUserProfile = useRef(false)
  const isFetchingMembershipStatus = useRef(false)
  const isFetchingMembershipPlans = useRef(false)
  const isFetchingUserOrders = useRef(false)
  const isFetchingTokenWallet = useRef(false)
  const isFetchingTokenPackages = useRef(false)
  const isFetchingTokenTopupOrders = useRef(false)

  const hasAuthenticatedSession = useCallback(async () => {
    const token = await getValidAccessToken()
    return Boolean(token)
  }, [])

  const refreshUserProfile = useCallback(async () => {
    if (isFetchingUserProfile.current) {
      return
    }

    isFetchingUserProfile.current = true
    setUserProfileLoading(true)

    try {
      const profile = await getUserProfile()
      setUserProfile(profile)

      if (profile) {
        localStorage.setItem('user_type', profile.user_type)
      } else {
        localStorage.removeItem('user_type')
      }

      window.dispatchEvent(new CustomEvent('user-type-changed'))
    } catch (error) {
      console.error('Refresh user profile failed:', error)
      setUserProfile(null)
      localStorage.removeItem('user_type')
      window.dispatchEvent(new CustomEvent('user-type-changed'))
    } finally {
      isFetchingUserProfile.current = false
      setUserProfileLoading(false)
    }
  }, [])

  const refreshMembershipStatus = useCallback(async () => {
    if (isFetchingMembershipStatus.current) {
      return
    }

    isFetchingMembershipStatus.current = true
    setMembershipStatusLoading(true)

    try {
      if (!(await hasAuthenticatedSession())) {
        setMembershipStatus(DEFAULT_MEMBERSHIP_STATUS)
        return
      }

      const status = await getUserMembershipStatus()
      setMembershipStatus(status)
    } catch (error) {
      console.error('Refresh membership status failed:', error)
      setMembershipStatus(DEFAULT_MEMBERSHIP_STATUS)
    } finally {
      isFetchingMembershipStatus.current = false
      setMembershipStatusLoading(false)
    }
  }, [hasAuthenticatedSession])

  const refreshMembershipPlans = useCallback(async () => {
    if (isFetchingMembershipPlans.current) {
      return
    }

    isFetchingMembershipPlans.current = true
    setMembershipPlansLoading(true)

    try {
      if (!(await hasAuthenticatedSession())) {
        setMembershipPlans([])
        return
      }

      const plans = await getMembershipPlans()
      setMembershipPlans(plans.items)
    } catch (error) {
      console.error('Refresh membership plans failed:', error)
      setMembershipPlans([])
    } finally {
      isFetchingMembershipPlans.current = false
      setMembershipPlansLoading(false)
    }
  }, [hasAuthenticatedSession])

  const refreshUserOrders = useCallback(async (status?: string) => {
    if (isFetchingUserOrders.current) {
      return
    }

    isFetchingUserOrders.current = true
    setUserOrdersLoading(true)

    try {
      if (!(await hasAuthenticatedSession())) {
        setUserOrders([])
        return
      }

      const params = status && status !== 'all' ? { status } : undefined
      const orders = await getUserOrders(params)
      setUserOrders(orders)
    } catch (error) {
      console.error('Refresh user orders failed:', error)
      setUserOrders([])
    } finally {
      isFetchingUserOrders.current = false
      setUserOrdersLoading(false)
    }
  }, [hasAuthenticatedSession])

  const refreshTokenWallet = useCallback(async () => {
    if (isFetchingTokenWallet.current) {
      return
    }

    isFetchingTokenWallet.current = true
    setTokenWalletLoading(true)

    try {
      if (!(await hasAuthenticatedSession())) {
        setTokenWallet(null)
        return
      }

      const wallet = await getTokenWallet()
      setTokenWallet(wallet)
    } catch (error) {
      console.error('Refresh token wallet failed:', error)
      setTokenWallet(null)
    } finally {
      isFetchingTokenWallet.current = false
      setTokenWalletLoading(false)
    }
  }, [hasAuthenticatedSession])

  const refreshTokenPackages = useCallback(async () => {
    if (isFetchingTokenPackages.current) {
      return
    }

    isFetchingTokenPackages.current = true
    setTokenPackagesLoading(true)

    try {
      if (!(await hasAuthenticatedSession())) {
        setTokenPackages([])
        return
      }

      const packages = await getTokenPackages()
      setTokenPackages(packages.items)
    } catch (error) {
      console.error('Refresh token packages failed:', error)
      setTokenPackages([])
    } finally {
      isFetchingTokenPackages.current = false
      setTokenPackagesLoading(false)
    }
  }, [hasAuthenticatedSession])

  const refreshTokenTopupOrders = useCallback(async (params?: { request_id?: string; checkout_id?: string; order_number?: string }) => {
    if (isFetchingTokenTopupOrders.current) {
      return
    }

    isFetchingTokenTopupOrders.current = true
    setTokenTopupOrdersLoading(true)

    try {
      if (!(await hasAuthenticatedSession())) {
        setTokenTopupOrders([])
        return
      }

      const orders = await getTokenTopupOrders(params)
      setTokenTopupOrders(orders.items)
    } catch (error) {
      console.error('Refresh token topup orders failed:', error)
      setTokenTopupOrders([])
    } finally {
      isFetchingTokenTopupOrders.current = false
      setTokenTopupOrdersLoading(false)
    }
  }, [hasAuthenticatedSession])

  const refreshAllData = useCallback(async () => {
    await refreshUserProfile()

    if (!(await hasAuthenticatedSession())) {
      setMembershipStatus(DEFAULT_MEMBERSHIP_STATUS)
      setMembershipPlans([])
      setUserOrders([])
      setTokenWallet(null)
      setTokenPackages([])
      setTokenTopupOrders([])
      return
    }

    await Promise.all([
      refreshMembershipStatus(),
      refreshMembershipPlans(),
      refreshUserOrders(),
      refreshTokenWallet(),
      refreshTokenPackages(),
      refreshTokenTopupOrders(),
    ])
  }, [
    hasAuthenticatedSession,
    refreshMembershipPlans,
    refreshMembershipStatus,
    refreshTokenPackages,
    refreshTokenTopupOrders,
    refreshTokenWallet,
    refreshUserOrders,
    refreshUserProfile,
  ])

  useEffect(() => {
    refreshAllData()
  }, [refreshAllData])

  useEffect(() => {
    const handleRefreshMembershipStatus = () => {
      void refreshMembershipStatus()
    }

    window.addEventListener('refresh-membership-status', handleRefreshMembershipStatus)
    return () => {
      window.removeEventListener('refresh-membership-status', handleRefreshMembershipStatus)
    }
  }, [refreshMembershipStatus])

  const value = useMemo<GlobalUserData>(
    () => ({
      userProfile,
      userProfileLoading,
      membershipStatus,
      membershipStatusLoading,
      membershipPlans,
      membershipPlansLoading,
      userOrders,
      userOrdersLoading,
      pendingOrders: userOrders.filter((order) => order.status === 'pending'),
      tokenWallet,
      tokenWalletLoading,
      tokenPackages,
      tokenPackagesLoading,
      tokenTopupOrders,
      tokenTopupOrdersLoading,
      refreshUserProfile,
      refreshMembershipStatus,
      refreshMembershipPlans,
      refreshUserOrders,
      refreshTokenWallet,
      refreshTokenPackages,
      refreshTokenTopupOrders,
      refreshAllData,
    }),
    [
      membershipPlans,
      membershipPlansLoading,
      membershipStatus,
      membershipStatusLoading,
      refreshAllData,
      refreshMembershipPlans,
      refreshMembershipStatus,
      refreshTokenPackages,
      refreshTokenTopupOrders,
      refreshTokenWallet,
      refreshUserOrders,
      refreshUserProfile,
      tokenPackages,
      tokenPackagesLoading,
      tokenTopupOrders,
      tokenTopupOrdersLoading,
      tokenWallet,
      tokenWalletLoading,
      userOrders,
      userOrdersLoading,
      userProfile,
      userProfileLoading,
    ]
  )

  return <GlobalUserDataContext.Provider value={value}>{children}</GlobalUserDataContext.Provider>
}

export function useGlobalUserData(): GlobalUserData {
  const context = useContext(GlobalUserDataContext)

  if (context === undefined) {
    throw new Error('useGlobalUserData must be used within a GlobalUserDataProvider')
  }

  return context
}

export function useMembershipStatus() {
  const { membershipStatus, membershipStatusLoading, refreshMembershipStatus } = useGlobalUserData()

  return {
    membershipStatus,
    isLoading: membershipStatusLoading,
    refresh: refreshMembershipStatus,
  }
}

export async function refreshMembershipStatusGlobally() {
  window.dispatchEvent(new CustomEvent('refresh-membership-status'))
}
