// src/routes/admin.tsx
import { verifySession } from '@/lib/session'
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { fetchMyProfile } from '@/lib/api/client/profile'
import { BannedScreen } from '@/components/ui/banned-screen'


export const Route = createFileRoute('/_admin')({
  loader: async () => {
    const session = await verifySession()
    
    if (!session || !(session.isAdmin || session.isModerator)) {
      throw redirect({ to: '/' })
    }

    return {
      token: session?.token,
      isAdmin: session?.isAdmin ?? false,
      isModerator: session?.isModerator ?? false,
    }
  },
  component: AdminLayout,
})


function AdminLayout() {
  const { token } = Route.useLoaderData()

  const { error: profileError } = useQuery({
    queryKey: ['profile'],
    queryFn: () => fetchMyProfile(token!),
    enabled: !!token,
    retry: false,
    staleTime: 30_000,
  })

  const isBanned = profileError?.message?.includes('заблокирован') ||
    profileError?.message?.includes('блокирован')

  if (isBanned) {
    return <BannedScreen />
  }

  return (
    <div className="admin-container">
        <Outlet /> 
    </div>
  )
}
