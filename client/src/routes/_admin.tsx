// src/routes/admin.tsx
import { verifySession } from '@/lib/session'
import { createFileRoute, Outlet, redirect } from '@tanstack/react-router'


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
  return (
    <div className="admin-container">
        <Outlet /> 
    </div>
  )
}
