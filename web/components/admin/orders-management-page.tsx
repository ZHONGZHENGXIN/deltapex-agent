'use client'

import { useEffect, useState, useCallback } from 'react'
import { useTranslations } from 'next-intl'

import { 
  Package,
  Calendar, 
  CreditCard, 
  Eye, 
  Loader2,
  Search,
  Copy
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { fetcher } from '@/util/fetcher'
import { formatCurrency as formatCurrencyUtil } from '@/util/currency'
import OrderDetailDialog from '@/components/admin/order-detail-dialog'


interface OrderListItem {
  id: number
  order_number: string
  user_id: number
  user_email?: string  // 鐢ㄦ埛閭瀛楁
  username?: string
  membership_plan_id: number
  status: 'pending' | 'processing' | 'completed' | 'cancelled' | 'failed' | 'refunded'
  payment_method: 'stripe'
  final_price: number
  currency: string
  created_at: string
  paid_at?: string
}

// 璁㈠崟鎼滅储鍙傛暟鎺ュ彛
interface OrderSearchParams {
  limit?: number
  offset?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  status?: string
  user_id?: string
  user_email?: string
  username?: string
  order_number?: string
  start_date?: string
  end_date?: string
}

// 璁㈠崟鍒楄〃鍝嶅簲鎺ュ彛
interface OrderListResponse {
  orders: OrderListItem[]
  total: number
  total_pages: number
  current_page: number
  has_next: boolean
  has_prev: boolean
}

/**
 * 璁㈠崟绠＄悊缁勪欢锛堢鐞嗗憳锛? * 
 * 鍔熻兘:
 * - 绠＄悊鎵€鏈夌敤鎴疯鍗? * - 绛涢€夊拰鎼滅储璁㈠崟
 * - 鏌ョ湅璁㈠崟璇︽儏
 */
export default function OrdersManagementPage() {
  const t = useTranslations()
  
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [paginationInfo, setPaginationInfo] = useState({
    total: 0,
    total_pages: 0,
    current_page: 1,
    has_next: false,
    has_prev: false,
  })
  const [searchParams, setSearchParams] = useState<OrderSearchParams>({
    limit: 10,
    offset: 0,
    sort_by: 'created_at',
    sort_order: 'desc',
  })
  
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)


  // 鑾峰彇璁㈠崟鍒楄〃
  const fetchOrders = useCallback(async () => {
    try {
      setIsLoading(true)
      const params = new URLSearchParams()
      
      if (searchParams.status && searchParams.status !== 'all') params.append('status', searchParams.status)
      if (searchParams.user_id) params.append('user_id', searchParams.user_id)
      if (searchParams.user_email) params.append('user_email', searchParams.user_email)
      if (searchParams.username) params.append('username', searchParams.username)
      if (searchParams.order_number) params.append('order_number', searchParams.order_number)
      if (searchParams.start_date) params.append('start_date', searchParams.start_date)
      if (searchParams.end_date) params.append('end_date', searchParams.end_date)
      
      params.append('limit', (searchParams.limit || 10).toString())
      params.append('offset', (searchParams.offset || 0).toString())
      if (searchParams.sort_by) params.append('sort_by', searchParams.sort_by)
      if (searchParams.sort_order) params.append('sort_order', searchParams.sort_order)
      
      
      const url = `/orders/admin/all${params.toString() ? '?' + params.toString() : ''}`
      const response = await fetcher(url, {
        method: 'GET',
        auth: true,
      })
      
      const orderResponse = response as OrderListResponse
      setOrders(orderResponse.orders)
      setPaginationInfo({
        total: orderResponse.total,
        total_pages: orderResponse.total_pages,
        current_page: orderResponse.current_page,
        has_next: orderResponse.has_next,
        has_prev: orderResponse.has_prev,
      })
    } catch (error) {
      console.error('Fetch order list failed:', error)
      toast.error(t('order.messages.fetchFailed'))
    } finally {
      setIsLoading(false)
    }
  }, [searchParams, t])

  useEffect(() => {
    fetchOrders()
  }, [fetchOrders])

  // 澶勭悊鎼滅储鎻愪氦
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchParams({ ...searchParams, offset: 0 })
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      pending: { 
        variant: 'secondary' as const, 
        className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
        text: t('order.status.pending')
      },
      processing: { 
        variant: 'secondary' as const,
        className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        text: t('order.status.processing')
      },
      completed: { 
        variant: 'secondary' as const,
        className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        text: t('order.status.completed')
      },
      cancelled: { 
        variant: 'secondary' as const,
        className: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
        text: t('order.status.cancelled')
      },
      failed: { 
        variant: 'destructive' as const,
        className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        text: t('order.status.failed')
      },
      refunded: { 
        variant: 'secondary' as const,
        className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        text: t('order.status.refunded')
      }
    }

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending
    return (
      <Badge variant={config.variant} className={config.className}>
        {config.text}
      </Badge>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  // 鏍煎紡鍖栭噾棰?- 浣跨敤璁㈠崟涓殑璐у竵淇℃伅
  const formatCurrency = (amount: number, currency: string = 'CNY') => {
    return formatCurrencyUtil(amount, currency)
  }

  // 澶勭悊鏌ョ湅璁㈠崟璇︽儏
  const handleViewOrderDetail = (orderId: number) => {
    setSelectedOrderId(orderId)
    setIsDetailDialogOpen(true)
  }

  const handleCopyOrderNumber = async (orderNumber: string) => {
    try {
      await navigator.clipboard.writeText(orderNumber)
      toast.success(t('admin.orders.messages.orderNumberCopied'))
    } catch (error) {
      console.error('Copy order number failed:', error)
      toast.error(t('admin.orders.messages.copyFailed'))
    }
  }

  return (
    <div className="p-6 max-w-full mx-auto overflow-x-hidden">
      {/* 鎼滅储鍜岀瓫閫?*/}
      <div className="bg-card rounded-lg p-6 shadow-sm border border-border mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {/* 璁㈠崟鍙锋悳绱?*/}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('order.table.orderNumber')}
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  placeholder={t('admin.orders.search.orderNumberPlaceholder')}
                  value={searchParams.order_number || ''}
                  onChange={(e) => setSearchParams({ ...searchParams, order_number: e.target.value })}
                  className="pl-10"
                />
              </div>
            </div>

            {/* 鐢ㄦ埛鍚嶆悳绱?*/}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.search.username')}
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  placeholder={t('admin.orders.search.usernamePlaceholder')}
                  value={searchParams.username || ''}
                  onChange={(e) => setSearchParams({ ...searchParams, username: e.target.value })}
                  className="pl-10"
                />
              </div>
            </div>

            {/* 鐢ㄦ埛閭鎼滅储 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.search.userEmail')}
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  placeholder={t('admin.orders.search.userEmailPlaceholder')}
                  value={searchParams.user_email || ''}
                  onChange={(e) => setSearchParams({ ...searchParams, user_email: e.target.value })}
                  className="pl-10"
                />
              </div>
            </div>

            {/* 鐢ㄦ埛ID鎼滅储 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.filter.userId')}
              </label>
              <Input
                placeholder={t('admin.orders.filter.userIdPlaceholder')}
                value={searchParams.user_id || ''}
                onChange={(e) => setSearchParams({ ...searchParams, user_id: e.target.value })}
              />
            </div>

            {/* 璁㈠崟鐘舵€佺瓫閫?*/}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('order.filter.status')}
              </label>
              <select
                value={searchParams.status || 'all'}
                onChange={(e) => setSearchParams({ ...searchParams, status: e.target.value })}
                className="w-full border border-border rounded-md px-3 py-2 bg-background text-foreground"
              >
                <option value="all">{t('order.filter.all')}</option>
                <option value="pending">{t('order.status.pending')}</option>
                <option value="processing">{t('order.status.processing')}</option>
                <option value="completed">{t('order.status.completed')}</option>
                <option value="cancelled">{t('order.status.cancelled')}</option>
                <option value="failed">{t('order.status.failed')}</option>
                <option value="refunded">{t('order.status.refunded')}</option>
              </select>
            </div>

            {/* 鎺掑簭瀛楁 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.sort.sortBy')}
              </label>
              <select
                value={searchParams.sort_by || 'created_at'}
                onChange={(e) => setSearchParams({ ...searchParams, sort_by: e.target.value })}
                className="w-full border border-border rounded-md px-3 py-2 bg-background text-foreground"
              >
                <option value="created_at">{t('admin.orders.sort.fields.created_at')}</option>
                <option value="final_price">{t('admin.orders.sort.fields.final_price')}</option>
                <option value="status">{t('admin.orders.sort.fields.status')}</option>
                <option value="user_id">{t('admin.orders.sort.fields.user_id')}</option>
              </select>
            </div>

            {/* 鎺掑簭鏂瑰悜 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.sort.sortOrder')}
              </label>
              <select
                value={searchParams.sort_order || 'desc'}
                onChange={(e) => setSearchParams({ ...searchParams, sort_order: e.target.value as 'asc' | 'desc' })}
                className="w-full border border-border rounded-md px-3 py-2 bg-background text-foreground"
              >
                <option value="desc">{t('admin.orders.sort.directions.desc')}</option>
                <option value="asc">{t('admin.orders.sort.directions.asc')}</option>
              </select>
            </div>

            {/* 寮€濮嬫棩鏈?*/}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.filter.startDate')}
              </label>
              <Input
                type="date"
                value={searchParams.start_date || ''}
                onChange={(e) => setSearchParams({ ...searchParams, start_date: e.target.value })}
              />
            </div>

            {/* 缁撴潫鏃ユ湡 */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                {t('admin.orders.filter.endDate')}
              </label>
              <Input
                type="date"
                value={searchParams.end_date || ''}
                onChange={(e) => setSearchParams({ ...searchParams, end_date: e.target.value })}
              />
            </div>

            {/* 鎼滅储鎸夐挳 */}
            <div className="flex items-end">
              <Button type="submit" className="w-full">{t('ui.search')}</Button>
            </div>
          </div>
        </form>
      </div>

      {/* 璁㈠崟鍒楄〃 */}
      <div className="border border-border rounded-lg overflow-hidden bg-card shadow-sm">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 px-6">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
            <span className="text-muted-foreground">{t('common.actions.loading')}</span>
            <span className="text-sm text-muted-foreground mt-1">{t('admin.orders.loading.description')}</span>
          </div>
        ) : orders.length === 0 ? (
          <div className="text-center py-12 px-6">
            <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium text-muted-foreground mb-2">
              {t('order.list.empty')}
            </h3>
            <p className="text-muted-foreground">
              {t('admin.orders.list.emptyDescription')}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-b border-red-200/60 bg-gradient-to-r from-red-500/10 via-red-500/5 to-transparent backdrop-blur-sm dark:border-red-900/40">
                  <TableHead className="min-w-[200px] font-semibold text-red-700 dark:text-red-300">
                    {t('order.table.orderNumber')}
                  </TableHead>
                  <TableHead className="min-w-[80px] font-semibold text-red-700 dark:text-red-300">
                    {t('admin.orders.table.userId')}
                  </TableHead>
                  <TableHead className="min-w-[120px] font-semibold text-red-700 dark:text-red-300">
                    {t('admin.orders.table.username')}
                  </TableHead>
                  <TableHead className="min-w-[180px] font-semibold text-red-700 dark:text-red-300">
                    {t('admin.orders.table.userEmail')}
                  </TableHead>
                  <TableHead className="min-w-[80px] font-semibold text-red-700 dark:text-red-300">
                    {t('order.table.status')}
                  </TableHead>
                  <TableHead className="min-w-[120px] font-semibold text-red-700 dark:text-red-300">
                    {t('order.table.amount')}
                  </TableHead>
                  <TableHead className="min-w-[100px] font-semibold text-red-700 dark:text-red-300">
                    {t('order.table.paymentMethod')}
                  </TableHead>
                  <TableHead className="min-w-[160px] font-semibold text-red-700 dark:text-red-300">
                    {t('order.table.createTime')}
                  </TableHead>
                  <TableHead className="min-w-[80px] font-semibold text-red-700 dark:text-red-300">
                    {t('order.table.actions')}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.id} className="hover:bg-muted/50 transition-colors">
                    <TableCell className="font-mono text-sm">
                      <div className="flex items-center gap-2">
                        <span className="select-all">
                          {order.order_number}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 hover:bg-muted"
                          onClick={() => handleCopyOrderNumber(order.order_number)}
                          title={t('admin.orders.actions.copyOrderNumber')}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {order.user_id}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="truncate max-w-32" title={order.username || t('common.values.notSet')}>
                        {order.username || t('common.values.notSet')}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="truncate max-w-48" title={order.user_email || t('common.values.notSet')}>
                        {order.user_email || t('common.values.notSet')}
                      </div>
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(order.status)}
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold">
                        {formatCurrency(order.final_price, order.currency)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <CreditCard className="h-4 w-4" />
                        Stripe
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm">
                        <Calendar className="h-4 w-4" />
                        {formatDate(order.created_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleViewOrderDetail(order.id)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        
        {/* 鍒嗛〉 */}
        {!isLoading && orders.length > 0 && (
          <div className="bg-card px-4 py-3 flex items-center justify-between border-t border-border">
            <div className="flex-1 flex justify-between sm:hidden">
              <Button
                variant="outline"
                onClick={() => setSearchParams({ 
                  ...searchParams, 
                  offset: Math.max(0, (searchParams.offset || 0) - (searchParams.limit || 10)) 
                })}
                disabled={!paginationInfo.has_prev}
              >
                {t('pagination.previousPage')}
              </Button>
              <div className="text-sm text-muted-foreground flex items-center">
                {t('common.pagination.pageInfo', { 
                  current: paginationInfo.current_page, 
                  total: paginationInfo.total_pages 
                })}
              </div>
              <Button
                variant="outline"
                onClick={() => setSearchParams({ 
                  ...searchParams, 
                  offset: (searchParams.offset || 0) + (searchParams.limit || 10) 
                })}
                disabled={!paginationInfo.has_next}
              >
                {t('pagination.nextPage')}
              </Button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-muted-foreground">
                  {t('common.pagination.showRecordsWithTotal', {
                    start: (searchParams.offset || 0) + 1,
                    end: (searchParams.offset || 0) + orders.length,
                    total: paginationInfo.total
                  })}
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">
                  {t('common.pagination.pageInfo', { 
                    current: paginationInfo.current_page, 
                    total: paginationInfo.total_pages 
                  })}
                </span>
                <nav className="relative z-0 inline-flex rounded-md space-x-2">
                  <Button
                    className="shadow-sm"
                    variant="outline"
                    size="sm"
                    onClick={() => setSearchParams({ 
                      ...searchParams, 
                      offset: Math.max(0, (searchParams.offset || 0) - (searchParams.limit || 10)) 
                    })}
                    disabled={!paginationInfo.has_prev}
                  >
                    {t('pagination.previousPage')}
                  </Button>
                  <Button
                    className="shadow-sm"
                    variant="outline"
                    size="sm"
                    onClick={() => setSearchParams({ 
                      ...searchParams, 
                      offset: (searchParams.offset || 0) + (searchParams.limit || 10) 
                    })}
                    disabled={!paginationInfo.has_next}
                  >
                    {t('pagination.nextPage')}
                  </Button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 璁㈠崟璇︽儏寮规 */}
      <OrderDetailDialog
        orderId={selectedOrderId}
        open={isDetailDialogOpen}
        onOpenChange={setIsDetailDialogOpen}
      />
    </div>
  )
}

