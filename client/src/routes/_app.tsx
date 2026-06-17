
import Header from '@/components/features/Header'
import { UserTabbar } from '@/components/layout/tabbar'
import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_app')({
  component: App,
})

function App() {
  return (
    <div className="min-h-screen">
      <Header />
      <Outlet />
      <UserTabbar />
    </div>
  )
}
