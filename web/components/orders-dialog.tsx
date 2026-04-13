'use client'

import { useEffect, useState, useCallback } from 'react'
import { useTranslations } from 'next-intl'

import { 
  Package, 
  Calendar, 
  CreditCard, 
  Eye, 
  X, 
  Loader2,
  Filter,
  RefreshCw,
  Copy,
  ArrowLeft,
  Play
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Separator } from '@/components/ui/separator'
import { getOrderDetail, cancelOrder, continueOrderPayment } from '@/util/user-api'
import { useGlobalUserData } from '@/hooks/use-global-user-data'
import type { OrderResponse } from '@/util/user-api'
import { formatCurrency } from '@/util/currency'

interface OrdersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/**
 * 璁㈠崟绠＄悊寮规缁勪欢
 * 
 * 鍔熻兘:
 * - 鏄剧ず鐢ㄦ埛璁㈠崟鍒楄〃
 * - 绛涢€夎鍗曠姸鎬? * - 鏌ョ湅璁㈠崟璇︽儏
 * - 鍙栨秷寰呮敮浠樿鍗? */
export default function OrdersDialog({ open, onOpenChange }: OrdersDialogProps) {
  const t = useTranslations()
  const { userOrders, userOrdersLoading, refreshUserOrders } = useGlobalUserData()
  
  const [selectedOrder, setSelectedOrder] = useState<OrderResponse | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [cancellingOrderId, setCancellingOrderId] = useState<number | null>(null)
  const [continuingPaymentOrderId, setContinuingPaymentOrderId] = useState<number | null>(null)
  const [view, setView] = useState<'list' | 'detail'>('list')
  // const [isLoading, setIsLoading] = useState(false)

  const filteredOrders = statusFilter === 'all' 
    ? userOrders 
    : userOrders.filter(order => order.status === statusFilter)

  const fetchOrders = useCallback(async (status?: string) => {
    try {
      await refreshUserOrders(status)
    } catch {
      toast.error(t('order.messages.fetchFailed'))
    }
  }, [refreshUserOrders, t])

  useEffect(() => {
    if (open) {
      if (userOrders.length === 0 || statusFilter !== 'all') {
        fetchOrders(statusFilter)
      }
    }
  }, [open, statusFilter, fetchOrders, userOrders.length])

  // 澶勭悊璁㈠崟鍙栨秷
  const handleCancelOrder = async (orderId: number) => {
    if (!confirm(t('order.actions.confirmCancel'))) {
      return
    }

    try {
      setCancellingOrderId(orderId)
      await cancelOrder(orderId, t('order.cancelReason.userRequested'))
      toast.success(t('order.messages.cancelSuccess'))
      
      // 鍒锋柊璁㈠崟鍒楄〃
      fetchOrders(statusFilter)
    } catch (error) {
      let errorMessage = t('order.messages.cancelFailed');
      
      if (error instanceof Error) {
        errorMessage = error.message || errorMessage;
      }
      
      toast.error(errorMessage);
    } finally {
      setCancellingOrderId(null)
    }
  }

  // 澶勭悊缁х画鏀粯
  const handleContinuePayment = async (orderId: number) => {
    try {
      setContinuingPaymentOrderId(orderId)
      
      // 鏋勫缓鏀粯鎴愬姛鍜屽彇娑堢殑鍥炶皟URL
      const baseUrl = window.location.origin
      const successUrl = `${baseUrl}/payment/success`
      const cancelUrl = `${baseUrl}/payment/cancel`
      
      // 璋冪敤缁х画鏀粯API
      const checkoutResponse = await continueOrderPayment(orderId, successUrl, cancelUrl)
      
      // 璺宠浆鍒癝tripe鏀粯椤甸潰
      window.location.href = checkoutResponse.checkout_url
      
    } catch (error) {
      let errorMessage = t('order.messages.continuePaymentFailed');
      
      if (error instanceof Error) {
        errorMessage = error.message || errorMessage;
      }
      
      toast.error(errorMessage);
    } finally {
      setContinuingPaymentOrderId(null)
    }
  }

  // 鏌ョ湅璁㈠崟璇︽儏
  const handleViewDetail = async (orderId: number) => {
    try {
      // setIsLoading(true)
      const orderDetail = await getOrderDetail(orderId)
      setSelectedOrder(orderDetail)
      setView('detail')
    } catch (error) {
      let errorMessage = t('order.messages.fetchDetailFailed');
      
      if (error instanceof Error) {
        errorMessage = error.message || errorMessage;
      }
      
      toast.error(errorMessage);
    } finally {
      // setIsLoading(false)
    }
  }

  // 杩斿洖璁㈠崟鍒楄〃
  const handleBackToList = () => {
    setView('list')
    setSelectedOrder(null)
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { 
        className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        text: t('order.status.pending')
      },
      processing: { 
        className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        text: t('order.status.processing')
      },
      completed: { 
        className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        text: t('order.status.completed')
      },
      cancelled: { 
        className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
        text: t('order.status.cancelled')
      },
      failed: { 
        className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        text: t('order.status.failed')
      },
      refunded: { 
        className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        text: t('order.status.refunded')
      }
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending
    return (
      <Badge className={config.className}>
        {config.text}
      </Badge>
    )
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return t('common.status.notAvailable')
    return new Date(dateString).toLocaleString()
  }

  // 澶嶅埗鏂囨湰鍒板壀璐存澘
  const copyToClipboard = (text: string, message: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast.success(message)
    }).catch(() => {
      toast.error(t('common.messages.copyFailed'))
    })
  }

  // 娓叉煋璁㈠崟鍒楄〃
  const renderOrderList = () => (
    <>
      {/* 绛涢€夊櫒 */}
      <div className="mb-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            <label className="text-sm font-medium">{t('order.filter.status')}:</label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('order.filter.all')}</SelectItem>
                <SelectItem value="pending">{t('order.status.pending')}</SelectItem>
                <SelectItem value="processing">{t('order.status.processing')}</SelectItem>
                <SelectItem value="completed">{t('order.status.completed')}</SelectItem>
                <SelectItem value="cancelled">{t('order.status.cancelled')}</SelectItem>
                <SelectItem value="failed">{t('order.status.failed')}</SelectItem>
                <SelectItem value="refunded">{t('order.status.refunded')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => fetchOrders(statusFilter)}
            disabled={userOrdersLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${userOrdersLoading ? 'animate-spin' : ''}`} />
            {t('common.actions.refresh')}
          </Button>
        </div>
      </div>

      {/* 璁㈠崟鍒楄〃 */}
      {userOrdersLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-2 text-muted-foreground">{t('common.actions.loading')}</span>
        </div>
      ) : filteredOrders.length === 0 ? (
        <div className="text-center py-12">
          <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium text-muted-foreground mb-2">
            {t('order.list.empty')}
          </h3>
          <p className="text-muted-foreground">
            {t('order.list.emptyDescription')}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[200px]">{t('order.table.orderNumber')}</TableHead>
                <TableHead className="min-w-[80px]">{t('order.table.status')}</TableHead>
                <TableHead className="min-w-[120px]">{t('order.table.amount')}</TableHead>
                <TableHead className="min-w-[160px]">{t('order.table.createTime')}</TableHead>
                <TableHead className="min-w-[100px]">{t('order.table.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredOrders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-mono text-sm">
                    {order.order_number}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(order.status)}
                  </TableCell>
                  <TableCell className="font-semibold">
                    {formatCurrency(order.final_price, order.currency)}
                    {order.discount_amount > 0 && (
                      <span className="text-sm text-muted-foreground ml-1">
                        ({t('order.detail.originalPrice')} {formatCurrency(order.original_price, order.currency)})
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm">
                      <Calendar className="h-4 w-4" />
                      {formatDate(order.created_at)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {/* 鏌ョ湅璇︽儏 */}
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleViewDetail(order.id)}
                        title={t('common.actions.view')}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      
                      {/* 缁х画鏀粯 */}
                      {order.status === 'pending' && (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleContinuePayment(order.id)}
                          disabled={continuingPaymentOrderId === order.id}
                          title={t('order.actions.continuePayment')}
                        >
                          {continuingPaymentOrderId === order.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                      
                      {/* 鍙栨秷璁㈠崟 */}
                      {order.status === 'pending' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelOrder(order.id)}
                          disabled={cancellingOrderId === order.id}
                          title={t('order.actions.cancel')}
                        >
                          {cancellingOrderId === order.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <X className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </>
  )

  // 娓叉煋璁㈠崟璇︽儏
  const renderOrderDetail = () => {
    if (!selectedOrder) return null

    return (
      <>
        {/* 杩斿洖鎸夐挳 */}
        <div className="mb-4">
          <Button variant="outline" size="sm" onClick={handleBackToList}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common.actions.back')}
          </Button>
        </div>

        <div className="space-y-6">
          {/* 璁㈠崟鍩烘湰淇℃伅 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{t('order.detail.orderInfo')}</span>
                {getStatusBadge(selectedOrder.status)}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('order.detail.orderNumber')}
                  </label>
                  <div className="flex items-center gap-2 mt-1">
                    <code className="bg-muted px-2 py-1 rounded text-sm font-mono">
                      {selectedOrder.order_number}
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(selectedOrder.order_number, t('order.messages.orderNumberCopied'))}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    {t('order.detail.createTime')}
                  </label>
                  <div className="flex items-center gap-2 mt-1">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{formatDate(selectedOrder.created_at)}</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* 浠锋牸淇℃伅 */}
              <div>
                <h4 className="font-medium mb-3">{t('order.detail.priceInfo')}</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t('order.detail.originalPrice')}</span>
                    <span>{formatCurrency(selectedOrder.original_price, selectedOrder.currency)}</span>
                  </div>
                  {selectedOrder.discount_amount > 0 && (
                    <div className="flex justify-between text-green-600">
                      <span>{t('order.detail.discount')}</span>
                      <span>-{formatCurrency(selectedOrder.discount_amount, selectedOrder.currency)}</span>
                    </div>
                  )}
                  <Separator />
                  <div className="flex justify-between font-semibold text-lg">
                    <span>{t('order.detail.finalPrice')}</span>
                    <span>{formatCurrency(selectedOrder.final_price, selectedOrder.currency)}</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* 鏀粯淇℃伅 */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <CreditCard className="h-4 w-4" />
                  {t('order.detail.paymentInfo')}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">{t('order.detail.paymentMethod')}: </span>
                    <span>Stripe</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('order.detail.currency')}: </span>
                    <span>{selectedOrder.currency}</span>
                  </div>
                  {selectedOrder.paid_at && (
                    <div>
                      <span className="text-muted-foreground">{t('order.detail.paymentTime')}: </span>
                      <span>{formatDate(selectedOrder.paid_at)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* 澶囨敞淇℃伅 */}
              {(selectedOrder.notes || selectedOrder.failure_reason || selectedOrder.refund_reason) && (
                <>
                  <Separator />
                  <div>
                    <h4 className="font-medium mb-3">{t('order.detail.additionalInfo')}</h4>
                    <div className="space-y-2 text-sm">
                      {selectedOrder.notes && (
                        <div>
                          <span className="text-muted-foreground">{t('order.detail.notes')}: </span>
                          <span>{selectedOrder.notes}</span>
                        </div>
                      )}
                      {selectedOrder.failure_reason && (
                        <div className="text-red-600">
                          <span className="text-muted-foreground">{t('order.detail.failureReason')}: </span>
                          <span>{selectedOrder.failure_reason}</span>
                        </div>
                      )}
                      {selectedOrder.refund_reason && (
                        <div className="text-red-600">
                          <span className="text-muted-foreground">{t('order.detail.refundReason')}: </span>
                          <span>{selectedOrder.refund_reason}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            {view === 'list' ? t('order.title') : t('order.detail.title')}
          </DialogTitle>
        </DialogHeader>
        
        <div className="mt-4">
          {view === 'list' ? renderOrderList() : renderOrderDetail()}
        </div>
      </DialogContent>
    </Dialog>
  )
}

