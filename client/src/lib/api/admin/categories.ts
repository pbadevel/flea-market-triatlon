import { apiRequest } from '../api-request';
import { ADMIN_CATEGORIES_ENDPOINT, ADMIN_CATEGORIES_SUBCATEGORIES_ENDPOINT } from '../endpoints';
import type { Category, CategoryCreate, Subcategory, SubcategoryCreate } from '@/types/admin';

export const fetchCategories = async (token: string): Promise<Category[]> =>
  apiRequest<Category[]>(ADMIN_CATEGORIES_ENDPOINT, { method: 'GET', token });

export const createCategory = async (token: string, data: CategoryCreate): Promise<Category> =>
  apiRequest<Category>(ADMIN_CATEGORIES_ENDPOINT, { method: 'POST', token, body: data });

export const updateCategory = async (token: string, key: string, data: Partial<CategoryCreate>): Promise<Category> =>
  apiRequest<Category>(`${ADMIN_CATEGORIES_ENDPOINT}/${key}`, { method: 'PUT', token, body: data });

export const deleteCategory = async (token: string, key: string): Promise<void> =>
  apiRequest<void>(`${ADMIN_CATEGORIES_ENDPOINT}/${key}`, { method: 'DELETE', token });

export const createSubcategory = async (token: string, data: SubcategoryCreate): Promise<Subcategory> =>
  apiRequest<Subcategory>(ADMIN_CATEGORIES_SUBCATEGORIES_ENDPOINT, { method: 'POST', token, body: data });

export const updateSubcategory = async (token: string, key: string, data: Partial<SubcategoryCreate>): Promise<Subcategory> =>
  apiRequest<Subcategory>(`${ADMIN_CATEGORIES_SUBCATEGORIES_ENDPOINT}/${key}`, { method: 'PUT', token, body: data });

export const deleteSubcategory = async (token: string, key: string): Promise<void> =>
  apiRequest<void>(`${ADMIN_CATEGORIES_SUBCATEGORIES_ENDPOINT}/${key}`, { method: 'DELETE', token });
