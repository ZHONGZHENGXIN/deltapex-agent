'use client'

import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { useTranslations } from 'next-intl'
import {
  Activity,
  AlertTriangle,
  CircleDollarSign,
  Crown,
  DollarSign,
  Gauge,
  Link as LinkIcon,
  MessageSquare,
  MessageSquarePlus,
  ShieldAlert,
  ShoppingBasket,
  ShoppingCart,
  Timer,
  UserCheck,
  UserCog,
  UserPlus,
  UserX,
  Users,
  Zap,
} from 'lucide-react'
import { toast } from 'sonner'

import type { DashboardStats, MonitoringDashboard } from '@/app/[locale]/admin/types'
import { fetcher } from '@/util/fetcher'

interface StatCardProps {
  title: string
  value: number
  icon: ReactNode
  color: string
  isCurrency?: boolean
}

interface MetricCardProps {
  title: string
  value: string
  icon: ReactNode
  color: string
}

interface PanelProps {
  title: string
  icon: ReactNode
  children: ReactNode
  action?: ReactNode
}

function formatNumber(value: number): string {
  return value.toLocaleString()
}

function formatCurrency(value: number): string {
  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function StatCard({ title, value, icon, color, isCurrency = false }: StatCardProps) {
  return (
    <div className="bg-card rounded-lg p-6 shadow-sm border border-border">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold text-foreground">
            {isCurrency ? formatCurrency(value) : formatNumber(value)}
          </p>
        </div>
        <div className={`shrink-0 p-3 rounded-full ${color}`}>{icon}</div>
      </div>
    </div>
  )
}

function MetricCard({ title, value, icon, color }: MetricCardProps) {
  return (
    <div className="bg-card rounded-lg p-6 shadow-sm border border-border">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold text-foreground">{value}</p>
        </div>
        <div className={`shrink-0 p-3 rounded-full ${color}`}>{icon}</div>
      </div>
    </div>
  )
}

function Panel({ title, icon, children, action }: PanelProps) {
  return (
    <section className="bg-card rounded-lg p-6 shadow-sm border border-border">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <div className="text-muted-foreground">{icon}</div>
          <h2 className="text-base font-semibold text-foreground truncate">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted-foreground py-4">{children}</p>
}

function LoadingSkeleton() {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="animate-pulse space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, index) => (
            <div key={`top-${index}`} className="bg-card rounded-lg p-6 shadow-sm border border-border">
              <div className="h-4 bg-muted rounded w-24 mb-3" />
              <div className="h-8 bg-muted rounded w-20" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(9)].map((_, index) => (
            <div key={`body-${index}`} className="bg-card rounded-lg p-6 shadow-sm border border-border">
              <div className="h-4 bg-muted rounded w-28 mb-3" />
              <div className="h-8 bg-muted rounded w-24" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const t = useTranslations()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [monitoring, setMonitoring] = useState<MonitoringDashboard | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchDashboardStats = useCallback(async (): Promise<void> => {
    try {
      setLoading(true)
      const [dashboardData, monitoringData] = await Promise.all([
        fetcher('/admin/dashboard', {
          method: 'GET',
          auth: true,
        }),
        fetcher('/admin/monitoring', {
          method: 'GET',
          auth: true,
        }),
      ])
      setStats(dashboardData as DashboardStats)
      setMonitoring(monitoringData as MonitoringDashboard)
    } catch (error) {
      let errorMessage = t('admin.dashboard.messages.failedToLoadDashboard')
      if (error instanceof Error) {
        errorMessage = error.message || errorMessage
      }
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void fetchDashboardStats()
  }, [fetchDashboardStats])

  if (loading) {
    return <LoadingSkeleton />
  }

  if (!stats) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="text-center py-12">
          <p className="text-muted-foreground">{t('admin.dashboard.messages.failedToLoadDashboard')}</p>
        </div>
      </div>
    )
  }

  const maxLlmFailureRate = monitoring?.llm_channels.reduce(
    (max, channel) => Math.max(max, channel.failure_rate),
    0,
  ) ?? 0

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title={t('admin.dashboard.stats.todayRevenue')}
          value={stats.today_revenue}
          icon={<CircleDollarSign className="w-6 h-6 text-white" />}
          color="bg-orange-600"
          isCurrency
        />
        <StatCard
          title={t('admin.dashboard.stats.todayNewUsers')}
          value={stats.today_new_users}
          icon={<UserPlus className="w-6 h-6 text-white" />}
          color="bg-primary"
        />
        <StatCard
          title={t('admin.dashboard.stats.todayNewChats')}
          value={stats.today_new_chats}
          icon={<MessageSquarePlus className="w-6 h-6 text-white" />}
          color="bg-rose-600"
        />
        <StatCard
          title={t('admin.dashboard.stats.todayOrders')}
          value={stats.today_orders}
          icon={<ShoppingBasket className="w-6 h-6 text-white" />}
          color="bg-emerald-600"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title={t('admin.dashboard.stats.totalRevenue')}
          value={stats.total_revenue}
          icon={<DollarSign className="w-6 h-6 text-white" />}
          color="bg-orange-600"
          isCurrency
        />
        <StatCard
          title={t('admin.dashboard.stats.monthlyRevenue')}
          value={stats.monthly_revenue}
          icon={<DollarSign className="w-6 h-6 text-white" />}
          color="bg-orange-500"
          isCurrency
        />
        <StatCard
          title={t('admin.dashboard.stats.sevenDaysRevenue')}
          value={stats.seven_days_revenue}
          icon={<DollarSign className="w-6 h-6 text-white" />}
          color="bg-orange-400"
          isCurrency
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title={t('admin.dashboard.stats.totalUsers')}
          value={stats.total_users}
          icon={<Users className="w-6 h-6 text-white" />}
          color="bg-primary"
        />
        <StatCard
          title={t('admin.dashboard.stats.activeUsers')}
          value={stats.active_users}
          icon={<UserCheck className="w-6 h-6 text-white" />}
          color="bg-red-800"
        />
        <StatCard
          title={t('admin.dashboard.stats.adminUsers')}
          value={stats.admin_users}
          icon={<UserCog className="w-6 h-6 text-white" />}
          color="bg-red-700"
        />
        <StatCard
          title={t('admin.dashboard.stats.deletedUsers')}
          value={stats.deleted_users}
          icon={<UserX className="w-6 h-6 text-white" />}
          color="bg-gray-500"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title={t('admin.dashboard.stats.yearlyUsers')}
          value={stats.yearly_users}
          icon={<Crown className="w-6 h-6 text-white" />}
          color="bg-blue-600"
        />
        <StatCard
          title={t('admin.dashboard.stats.monthlyUsers')}
          value={stats.monthly_users}
          icon={<Crown className="w-6 h-6 text-white" />}
          color="bg-blue-500"
        />
        <StatCard
          title={t('admin.dashboard.stats.freeUsers')}
          value={stats.free_users}
          icon={<Crown className="w-6 h-6 text-white" />}
          color="bg-blue-400"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title={t('admin.dashboard.stats.totalChats')}
          value={stats.total_chats}
          icon={<MessageSquare className="w-6 h-6 text-white" />}
          color="bg-rose-600"
        />
        <StatCard
          title={t('admin.dashboard.stats.monthlyChats')}
          value={stats.monthly_chats}
          icon={<MessageSquare className="w-6 h-6 text-white" />}
          color="bg-rose-500"
        />
        <StatCard
          title={t('admin.dashboard.stats.sevenDaysChats')}
          value={stats.seven_days_chats}
          icon={<MessageSquare className="w-6 h-6 text-white" />}
          color="bg-rose-400"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title={t('admin.dashboard.stats.totalOrders')}
          value={stats.total_orders}
          icon={<ShoppingCart className="w-6 h-6 text-white" />}
          color="bg-emerald-600"
        />
        <StatCard
          title={t('admin.dashboard.stats.monthlyOrders')}
          value={stats.monthly_orders}
          icon={<ShoppingCart className="w-6 h-6 text-white" />}
          color="bg-emerald-500"
        />
        <StatCard
          title={t('admin.dashboard.stats.sevenDaysOrders')}
          value={stats.seven_days_orders}
          icon={<ShoppingCart className="w-6 h-6 text-white" />}
          color="bg-emerald-400"
        />
      </div>

      {monitoring && (
        <section className="space-y-6 pt-2">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-xl font-semibold text-foreground">{t('admin.monitoring.title')}</h1>
              <p className="text-sm text-muted-foreground">
                {t('admin.monitoring.generatedAt', {
                  time: new Date(monitoring.generated_at).toLocaleString(),
                })}
              </p>
            </div>
            {monitoring.external_links.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {monitoring.external_links.map((link) => (
                  <a
                    key={`${link.label}-${link.url}`}
                    href={link.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-foreground hover:bg-muted"
                  >
                    <LinkIcon className="h-4 w-4" />
                    {link.label}
                  </a>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard
              title={t('admin.monitoring.p99Latency')}
              value={`${monitoring.request_metrics.p99_latency_ms.toLocaleString()} ms`}
              icon={<Timer className="w-6 h-6 text-white" />}
              color="bg-indigo-600"
            />
            <MetricCard
              title={t('admin.monitoring.errorRate')}
              value={formatPercent(monitoring.request_metrics.error_rate)}
              icon={<ShieldAlert className="w-6 h-6 text-white" />}
              color="bg-red-700"
            />
            <MetricCard
              title={t('admin.monitoring.requestCount')}
              value={formatNumber(monitoring.request_metrics.request_count)}
              icon={<Activity className="w-6 h-6 text-white" />}
              color="bg-sky-700"
            />
            <MetricCard
              title={t('admin.monitoring.llmFailureRate')}
              value={formatPercent(maxLlmFailureRate)}
              icon={<Zap className="w-6 h-6 text-white" />}
              color="bg-amber-600"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Panel title={t('admin.monitoring.alerts')} icon={<AlertTriangle className="h-5 w-5" />}>
              {monitoring.alerts.length === 0 ? (
                <EmptyState>{t('admin.monitoring.noAlerts')}</EmptyState>
              ) : (
                <div className="divide-y divide-border">
                  {monitoring.alerts.map((alert, index) => (
                    <div key={`${alert.type}-${index}`} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-foreground">{alert.type}</p>
                        <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">
                          {alert.severity}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </Panel>

            <Panel title={t('admin.monitoring.llmChannels')} icon={<Gauge className="h-5 w-5" />}>
              {monitoring.llm_channels.length === 0 ? (
                <EmptyState>{t('admin.monitoring.noLlmData')}</EmptyState>
              ) : (
                <div className="divide-y divide-border">
                  {monitoring.llm_channels.map((channel) => (
                    <div key={`${channel.channel}-${channel.key_hash}`} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">{channel.channel}</p>
                          <p className="text-xs text-muted-foreground">{channel.key_hash}</p>
                        </div>
                        <span className="text-sm font-semibold text-foreground">
                          {formatPercent(channel.failure_rate)}
                        </span>
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-3 text-xs text-muted-foreground">
                        <span>
                          {t('admin.monitoring.requests')}: {formatNumber(channel.request_count)}
                        </span>
                        <span>
                          {t('admin.monitoring.errors')}: {formatNumber(channel.error_count)}
                        </span>
                        <span>
                          {t('admin.monitoring.tokens')}: {formatNumber(channel.total_tokens)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Panel title={t('admin.monitoring.tokenAlerts')} icon={<Zap className="h-5 w-5" />}>
              {monitoring.token_alerts.length === 0 ? (
                <EmptyState>{t('admin.monitoring.noTokenAlerts')}</EmptyState>
              ) : (
                <div className="divide-y divide-border">
                  {monitoring.token_alerts.map((alert) => (
                    <div key={alert.user_id} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">{alert.email}</p>
                          <p className="text-xs text-muted-foreground">
                            #{alert.user_id}
                            {alert.username ? ` - ${alert.username}` : ''}
                          </p>
                        </div>
                        <span className="text-sm font-semibold text-foreground">
                          {formatNumber(alert.daily_token_count)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        {t('admin.monitoring.threshold')}: {formatNumber(alert.threshold)} -{' '}
                        {t('admin.monitoring.requests')}: {formatNumber(alert.daily_message_count)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Panel>

            <Panel
              title={t('admin.monitoring.qualitySamples')}
              icon={<MessageSquare className="h-5 w-5" />}
              action={
                <span className="text-xs text-muted-foreground">
                  {monitoring.quality_samples.length}/{monitoring.sample_target}
                </span>
              }
            >
              {monitoring.quality_samples.length === 0 ? (
                <EmptyState>{t('admin.monitoring.noQualitySamples')}</EmptyState>
              ) : (
                <div className="divide-y divide-border">
                  {monitoring.quality_samples.map((sample) => (
                    <div key={sample.message_id} className="py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {sample.user_email}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            chat #{sample.chat_id} - message #{sample.message_id}
                          </p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {new Date(sample.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="mt-2 max-h-20 overflow-hidden text-sm text-muted-foreground">
                        {sample.content_preview}
                      </p>
                      {sample.token_usage && (
                        <p className="mt-2 truncate text-xs text-muted-foreground">
                          {JSON.stringify(sample.token_usage)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </section>
      )}
    </div>
  )
}
