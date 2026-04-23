'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'

import { CreditCard, Loader2, Wallet, Zap } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useGlobalUserData } from '@/hooks/use-global-user-data'
import { createCreemCheckout } from '@/util/user-api'
import { formatCurrency } from '@/util/currency'
import { formatTokenCount } from '@/util/user-utils'

interface RechargeDialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

function getLocaleFromPath(pathname: string) {
  const locale = pathname.split('/').filter(Boolean)[0]
  return locale === 'en' ? 'en' : 'zh'
}

export default function RechargeDialog({ open: externalOpen, onOpenChange }: RechargeDialogProps = {}) {
  const t = useTranslations()
  const pathname = usePathname()
  const locale = getLocaleFromPath(pathname)
  const {
    membershipStatus,
    tokenWallet,
    tokenWalletLoading,
    tokenPackages,
    tokenPackagesLoading,
    tokenTopupOrders,
    tokenTopupOrdersLoading,
    refreshTokenWallet,
    refreshTokenPackages,
    refreshTokenTopupOrders,
  } = useGlobalUserData()

  const [isSubmitting, setIsSubmitting] = useState<number | null>(null)
  const [internalOpen, setInternalOpen] = useState(false)
  const open = externalOpen !== undefined ? externalOpen : internalOpen
  const setOpen = onOpenChange || setInternalOpen

  useEffect(() => {
    const handleOpenRechargeDialog = () => {
      setOpen(true)
    }

    window.addEventListener('open-recharge-dialog', handleOpenRechargeDialog)
    return () => {
      window.removeEventListener('open-recharge-dialog', handleOpenRechargeDialog)
    }
  }, [setOpen])

  useEffect(() => {
    if (!open) {
      return
    }

    void refreshTokenWallet()
    void refreshTokenPackages()
    void refreshTokenTopupOrders()
  }, [open, refreshTokenPackages, refreshTokenTopupOrders, refreshTokenWallet])

  const isLoading = tokenWalletLoading || tokenPackagesLoading
  const recentOrders = useMemo(() => tokenTopupOrders.slice(0, 5), [tokenTopupOrders])

  const handleCheckout = async (packageId: number) => {
    try {
      setIsSubmitting(packageId)
      const baseOrigin = window.location.origin
      const successUrl = `${baseOrigin}/${locale}/payment/success`
      const cancelUrl = `${baseOrigin}/${locale}/payment/cancel`
      const response = await createCreemCheckout({
        package_id: packageId,
        success_url: successUrl,
        cancel_url: cancelUrl,
      })

      localStorage.setItem('pending_topup_request_id', response.request_id)
      localStorage.setItem('pending_topup_checkout_id', response.checkout_id)
      window.location.href = response.checkout_url
    } catch (error) {
      console.error('Create Creem checkout failed:', error)
      toast.error(t('billing.messages.checkoutFailed'))
    } finally {
      setIsSubmitting(null)
    }
  }

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'paid':
        return <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">{t('billing.orderStatus.paid')}</Badge>
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">{t('billing.orderStatus.pending')}</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const content = (
    <DialogContent className="max-w-5xl w-[95vw] max-h-[92vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-2xl">
          <Wallet className="h-6 w-6 text-primary" />
          {t('billing.title')}
        </DialogTitle>
      </DialogHeader>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('billing.balanceTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Wallet className="h-4 w-4" />
              {t('billing.paidBalance')}
            </div>
            <div className="text-3xl font-semibold">{formatTokenCount(tokenWallet?.paid_token_balance || 0)}</div>
            <div className="text-sm text-muted-foreground">
              {t('billing.totalRecharged')}: {formatTokenCount(tokenWallet?.total_recharged_tokens || 0)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('billing.freeQuotaTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Zap className="h-4 w-4" />
              {t('billing.freeRemaining')}
            </div>
            <div className="text-3xl font-semibold">{formatTokenCount(membershipStatus?.daily_token_remaining || 0)}</div>
            <div className="text-sm text-muted-foreground">
              {t('billing.freeUsedToday')}: {formatTokenCount(membershipStatus?.daily_token_count || 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {tokenPackages.map((pkg) => (
            <Card key={pkg.id} className="border-border/70">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-lg">
                  <span>{pkg.name}</span>
                  <CreditCard className="h-5 w-5 text-primary" />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-3xl font-semibold">{formatCurrency(pkg.price, pkg.currency)}</div>
                <div className="text-sm text-muted-foreground">
                  {t('billing.packageTokens')}: {formatTokenCount(pkg.token_amount)}
                </div>
                <Button className="w-full" onClick={() => handleCheckout(pkg.id)} disabled={isSubmitting === pkg.id}>
                  {isSubmitting === pkg.id ? <Loader2 className="h-4 w-4 animate-spin" /> : t('billing.buyNow')}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">{t('billing.recentOrders')}</CardTitle>
          <Button variant="outline" size="sm" onClick={() => void refreshTokenTopupOrders()} disabled={tokenTopupOrdersLoading}>
            {tokenTopupOrdersLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : t('common.actions.refresh')}
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {recentOrders.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('billing.noOrders')}</p>
          ) : (
            recentOrders.map((order) => (
              <div key={order.id} className="flex items-center justify-between rounded-lg border p-3">
                <div className="space-y-1">
                  <div className="font-mono text-sm">{order.order_number}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatCurrency(order.amount, order.currency)} · {formatTokenCount(order.token_amount)}
                  </div>
                </div>
                {renderStatusBadge(order.status)}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </DialogContent>
  )

  if (externalOpen !== undefined) {
    return <Dialog open={open} onOpenChange={setOpen}>{content}</Dialog>
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Wallet className="h-4 w-4" />
          {t('billing.buttonText')}
        </Button>
      </DialogTrigger>
      {content}
    </Dialog>
  )
}
