import { serverApi } from '../server-proxy'

export const fetchFilterConfig = () =>
  serverApi({ data: { path: '/filters' } })
