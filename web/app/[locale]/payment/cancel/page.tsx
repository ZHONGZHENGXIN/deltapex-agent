'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import Link from 'next/link'

import { XCircle, RefreshCw, ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import RechargeDialog from '@/components/recharge-dialog'

/**
 * 鏀粯鍙栨秷椤甸潰鍐呭缁勪欢
 * 
 * 鍔熻兘:
 * - 鏄剧ず鏀粯鍙栨秷鐘舵€? * - 鎻愪緵閲嶆柊鏀粯閫夐」
 * - 寮曞鐢ㄦ埛杩斿洖鎴栭噸璇? */
function PaymentCancelContent() {
  const t = useTranslations()
  const searchParams = useSearchParams()
  
  const [showRechargeDialog, setShowRechargeDialog] = useState(false)

  useEffect(() => {
    const sessionId = searchParams.get('session_id')
    if (sessionId) {
      console.log('Payment cancelled - Session ID:', sessionId)
    }
  }, [searchParams])

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-red-50 to-pink-50 dark:from-orange-950 dark:via-red-950 dark:to-pink-950 flex items-center justify-center p-4">
      <div className="max-w-lg w-full">
        <Card className="border-orange-200 dark:border-orange-800 shadow-xl">
          <CardHeader className="text-center pb-4">
            <div className="mx-auto w-16 h-16 bg-orange-100 dark:bg-orange-900 rounded-full flex items-center justify-center mb-4">
              <XCircle className="h-8 w-8 text-orange-600 dark:text-orange-400" />
            </div>
            <CardTitle className="text-2xl font-bold text-orange-600 dark:text-orange-400">
              {t('payment.cancel.title')}
            </CardTitle>
            <p className="text-muted-foreground">
              {t('payment.cancel.description')}
            </p>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* 璇存槑淇℃伅 */}
            <div className="bg-orange-50 dark:bg-orange-950 rounded-lg p-4">
              <h3 className="font-semibold text-orange-800 dark:text-orange-200 mb-2">
                {t('payment.cancel.whatHappened')}
              </h3>
              <ul className="text-sm text-orange-700 dark:text-orange-300 space-y-1">
                <li>鈥?{t('payment.cancel.reasons.userCancelled')}</li>
                <li>鈥?{t('payment.cancel.reasons.paymentFailed')}</li>
                <li>鈥?{t('payment.cancel.reasons.sessionExpired')}</li>
              </ul>
            </div>

            {/* 涓嬩竴姝ユ搷浣?*/}
            <div className="space-y-3">
              <h3 className="font-semibold">{t('payment.cancel.nextSteps')}</h3>
              
              {/* 閲嶆柊鍗囩骇鎸夐挳 */}
              <Button 
                size="lg"
                onClick={() => setShowRechargeDialog(true)}
                className="w-full h-12 flex items-center justify-center gap-2 bg-gradient-to-r from-red-600 to-orange-500 hover:from-red-700 hover:to-pink-700"
              >
                <RefreshCw className="h-4 w-4" />
                {t('payment.cancel.retryPayment')}
              </Button>

              {/* 杩斿洖棣栭〉 */}
              <Button variant="outline" size="lg" asChild className="w-full h-12">
                <Link href="/" className="flex items-center justify-center gap-2">
                  <ArrowLeft className="h-4 w-4" />
                  {t('payment.cancel.backToHome')}
                </Link>
              </Button>
            </div>

            {/* 鍏嶈垂璁″垝鎻愰啋 */}
            <div className="text-center text-sm text-muted-foreground pt-4 border-t">
              <p>{t('payment.cancel.freeReminder')}</p>
            </div>

            {/* 甯姪淇℃伅 */}
            <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
                {t('payment.cancel.needHelp')}
              </h4>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {t('payment.cancel.contactSupport')}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 鍗囩骇瀵硅瘽妗?*/}
      <RechargeDialog 
        open={showRechargeDialog} 
        onOpenChange={setShowRechargeDialog}
      />
    </div>
  )
}

/**
 * 鏀粯鍙栨秷椤甸潰
 * 
 * 浣跨敤 Suspense 鍖呰浠ユ敮鎸?useSearchParams
 */
export default function PaymentCancelPage() {
  const t = useTranslations()
  
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-red-50 to-pink-50 dark:from-orange-950 dark:via-red-950 dark:to-pink-950 flex items-center justify-center p-4">
        <div className="max-w-lg w-full">
          <Card className="border-orange-200 dark:border-orange-800 shadow-xl">
            <CardContent className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-600 mx-auto"></div>
              <p className="mt-4 text-muted-foreground">{t('common.actions.loading')}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    }>
      <PaymentCancelContent />
    </Suspense>
  )
}

