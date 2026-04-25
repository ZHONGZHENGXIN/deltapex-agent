'use client'

import { Suspense, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'

import { CheckCircle, Loader2, Wallet } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { GlobalUserDataProvider, useGlobalUserData } from '@/hooks/use-global-user-data'
import type { TokenTopupOrder } from '@/util/user-api'
import { getTokenTopupOrders } from '@/util/user-api'
import { formatCurrency } from '@/util/currency'
import { formatTokenCount } from '@/util/user-utils'

function PaymentSuccessContent() {
  const t = useTranslations()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { tokenWallet, refreshTokenWallet, refreshTokenTopupOrders } = useGlobalUserData()

  const [isLoading, setIsLoading] = useState(true)
  const [order, setOrder] = useState<TokenTopupOrder | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)
  const [checkoutId, setCheckoutId] = useState<string | null>(null)
  const [orderNumber, setOrderNumber] = useState<string | null>(null)
  const [referenceResolved, setReferenceResolved] = useState(false)
  const localePrefix = pathname.split('/').filter(Boolean)[0] === 'en' ? '/en' : '/zh'
  const hasCreemRedirectSignal = useMemo(
    () =>
      ['order_id', 'customer_id', 'product_id', 'signature'].some((key) => Boolean(searchParams.get(key))),
    [searchParams]
  )

  const findRecentOrder = (items: TokenTopupOrder[]) => {
    const now = Date.now()
    return (
      items.find((item) => {
        const createdAt = new Date(item.created_at).getTime()
        return Number.isFinite(createdAt) && now - createdAt < 30 * 60 * 1000
      }) || null
    )
  }

  useEffect(() => {
    const nextRequestId =
      searchParams.get('request_id') ||
      searchParams.get('topup_request_id') ||
      localStorage.getItem('pending_topup_request_id')
    const nextCheckoutId =
      searchParams.get('checkout_id') ||
      localStorage.getItem('pending_topup_checkout_id')
    const nextOrderNumber =
      searchParams.get('topup_order_number') ||
      searchParams.get('order_number') ||
      localStorage.getItem('pending_topup_order_number')

    if (nextRequestId) {
      localStorage.setItem('pending_topup_request_id', nextRequestId)
    }
    if (nextCheckoutId) {
      localStorage.setItem('pending_topup_checkout_id', nextCheckoutId)
    }
    if (nextOrderNumber) {
      localStorage.setItem('pending_topup_order_number', nextOrderNumber)
    }

    setRequestId(nextRequestId)
    setCheckoutId(nextCheckoutId)
    setOrderNumber(nextOrderNumber)
    setReferenceResolved(true)
  }, [searchParams])

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null
    let cancelled = false
    let attempts = 0

    const pollOrder = async () => {
      if (!referenceResolved) {
        return
      }

      try {
        let response
        if (requestId || checkoutId || orderNumber) {
          response = await getTokenTopupOrders({
            request_id: requestId || undefined,
            checkout_id: checkoutId || undefined,
            order_number: orderNumber || undefined,
            limit: 1,
          })
        } else {
          response = await getTokenTopupOrders({ limit: 5 })
        }

        let currentOrder: TokenTopupOrder | null = response.items[0] ?? null
        if (!currentOrder) {
          const recentFallback = await getTokenTopupOrders({ limit: 5 })
          currentOrder = findRecentOrder(recentFallback.items)
        }

        if (!currentOrder && !requestId && !checkoutId && !orderNumber && !hasCreemRedirectSignal) {
          setError(t('billing.messages.missingOrderReference'))
          setIsLoading(false)
          return
        }

        if (!cancelled) {
          setError(null)
          setOrder(currentOrder)
          await refreshTokenTopupOrders({
            request_id: requestId || undefined,
            checkout_id: checkoutId || undefined,
            order_number: orderNumber || undefined,
          })
          await refreshTokenWallet()
          setIsLoading(false)
        }

        if (!cancelled && currentOrder?.status === 'pending' && attempts < 20) {
          attempts += 1
          timer = setTimeout(() => {
            void pollOrder()
          }, 3000)
          return
        }

        if (currentOrder?.status === 'paid') {
          localStorage.removeItem('pending_topup_request_id')
          localStorage.removeItem('pending_topup_checkout_id')
          localStorage.removeItem('pending_topup_order_number')
        }
      } catch (fetchError) {
        console.error('Fetch topup order failed:', fetchError)
        if (!cancelled) {
          setError(t('billing.messages.fetchOrderFailed'))
          setIsLoading(false)
        }
      }
    }

    void pollOrder()

    return () => {
      cancelled = true
      if (timer) {
        clearTimeout(timer)
      }
    }
  }, [checkoutId, hasCreemRedirectSignal, orderNumber, referenceResolved, refreshTokenTopupOrders, refreshTokenWallet, requestId, t])

  const renderStatus = () => {
    if (!order || order.status === 'pending') {
      return <Badge className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">{t('billing.status.processing')}</Badge>
    }
    if (order.status === 'paid') {
      return <Badge className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">{t('billing.orderStatus.paid')}</Badge>
    }
    return <Badge variant="secondary">{order.status}</Badge>
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">{t('billing.status.processing')}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="max-w-md w-full">
          <CardHeader className="text-center">
            <CardTitle className="text-red-600">{t('payment.error.title')}</CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-muted-foreground">{error}</p>
            <div className="flex gap-2 justify-center">
              <Button variant="outline" onClick={() => router.back()}>{t('common.actions.back')}</Button>
              <Button asChild><Link href={localePrefix}>{t('common.actions.home')}</Link></Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-2xl w-full space-y-6">
        <Card className="shadow-xl">
          <CardHeader className="text-center pb-4">
            <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-4">
              {order?.status === 'paid' ? (
                <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
              ) : (
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
              )}
            </div>
            <CardTitle className="text-2xl font-bold">
              {order?.status === 'paid' ? t('billing.successTitle') : t('billing.processingTitle')}
            </CardTitle>
            <p className="text-muted-foreground">{t('billing.successDescription')}</p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="rounded-lg border p-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{t('billing.orderReference')}</span>
                {renderStatus()}
              </div>
              {order && (
                <>
                  <div className="text-sm font-mono">{order.order_number}</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">{t('billing.packageAmount')}:</span>
                      <span className="ml-2">{formatTokenCount(order.token_amount)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('order.detail.finalPrice')}:</span>
                      <span className="ml-2">{formatCurrency(order.amount, order.currency)}</span>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="bg-muted/40 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Wallet className="h-5 w-5 text-primary" />
                <h3 className="font-semibold">{t('billing.walletUpdated')}</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                {t('billing.paidBalance')}: {formatTokenCount(tokenWallet?.paid_token_balance || 0)}
              </p>
            </div>

            <Button asChild size="lg" className="w-full h-12">
              <Link href={localePrefix}>{t('billing.backToChat')}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function PaymentSuccessPage() {
  return (
    <GlobalUserDataProvider>
      <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
        <PaymentSuccessContent />
      </Suspense>
    </GlobalUserDataProvider>
  )
}
