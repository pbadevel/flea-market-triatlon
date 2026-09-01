import { Bestsellers } from '@/components/features/home'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_app/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div className='w-full max-w-full overflow-x-hidden'>
      <Bestsellers />
  </div>
}
