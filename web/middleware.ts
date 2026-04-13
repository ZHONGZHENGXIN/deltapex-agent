import createMiddleware from 'next-intl/middleware'
import { NextRequest } from 'next/server'

import { routing } from '@/i18n/routing'

export default function middleware(request: NextRequest) {
  // Handle internationalization first
  const response = createMiddleware(routing)(request);
  
  // Note: We can't check localStorage from server-side middleware
  // So we'll rely on client-side protection in the admin page component
  // The middleware mainly handles internationalization routing
  
  return response;
}

export const config = {
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)'
};