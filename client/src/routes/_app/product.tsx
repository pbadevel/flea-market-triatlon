import { createFileRoute, Outlet } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/product')({
  component: ProductSection,
})

function ProductSection() {
  return (
    <div className="min-h-screen">
      <Outlet />
    </div>
  )
}
