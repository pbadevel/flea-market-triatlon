
import Header from '@/components/features/Header'
import { UserTabbar } from '@/components/layout/tabbar'
import { createFileRoute, Outlet } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { verifySession } from '@/lib/session'
import { fetchMyProfile } from '@/lib/api/client/profile'
import { BannedScreen } from '@/components/ui/banned-screen'

export const Route = createFileRoute('/_app')({
  component: App,
})

function App() {
  const { data: session } = useQuery({
    queryKey: ['session'],
    queryFn: verifySession,
    staleTime: 0,
  })

  const { data: profile, error: profileError } = useQuery({
    queryKey: ['profile'],
    queryFn: () => fetchMyProfile(session!.token!),
    enabled: !!session?.token,
    retry: false,
    staleTime: 30_000,
  })

  const isBanned = profileError?.message?.includes('заблокирован') ||
    (profileError as any)?.info?.code === 'BANNED'

  if (isBanned) {
    return <BannedScreen />
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="pb-24 lg:pb-0">
        <Outlet />
      </main>
      <UserTabbar />
    </div>
  )
}
