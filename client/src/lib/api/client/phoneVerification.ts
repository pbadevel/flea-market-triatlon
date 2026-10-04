// src/lib/api/client/phoneVerification.ts
import { serverApi } from '../server-proxy'

export const sendPhoneCode = (token: string, phone: string) =>
  serverApi({
    data: { path: '/phone-verification/send-code', method: 'POST', token, body: { phone } },
  })

export const verifyPhoneCode = (token: string, phone: string, code: string) =>
  serverApi({
    data: { path: '/phone-verification/verify-code', method: 'POST', token, body: { phone, code } },
  })

export const fetchPhoneStatus = (token: string) =>
  serverApi({ data: { path: '/phone-verification/status', token } })