import type { Metadata } from 'next'
import './globals.css'
import Providers from '@/components/Providers'
import { ToastContainer } from '@/components/Toast'
import { MockProvider } from '@/mocks/MockProvider'

export const metadata: Metadata = {
  title: 'NewsOps — Developer Intelligence',
  description: 'AI-powered developer intelligence dashboard with human-in-the-loop publishing',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <Providers>
          <MockProvider>
            {children}
          </MockProvider>
          <ToastContainer />
        </Providers>
      </body>
    </html>
  )
}
