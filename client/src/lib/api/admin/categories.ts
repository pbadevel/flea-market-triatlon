import { serverApi } from '../server-proxy'

export const fetchCategories = (token: string) =>
  serverApi({ data: { path: '/admin/categories', token } })

export const createCategory = (token: string, data: { name: string; key: string; icon?: string }) =>
  serverApi({ data: { path: '/admin/categories', method: 'POST', token, body: data } })

export const updateCategory = (token: string, key: string, data: { name?: string; icon?: string }) =>
  serverApi({ data: { path: `/admin/categories/${key}`, method: 'PUT', token, body: data } })

export const deleteCategory = (token: string, key: string) =>
  serverApi({ data: { path: `/admin/categories/${key}`, method: 'DELETE', token } })

export const createSubcategory = (token: string, data: { category_key: string; name: string; key: string }) =>
  serverApi({ data: { path: '/admin/categories/subcategories', method: 'POST', token, body: data } })

export const updateSubcategory = (token: string, key: string, data: { name?: string }) =>
  serverApi({ data: { path: `/admin/categories/subcategories/${key}`, method: 'PUT', token, body: data } })

export const deleteSubcategory = (token: string, key: string) =>
  serverApi({ data: { path: `/admin/categories/subcategories/${key}`, method: 'DELETE', token } })
