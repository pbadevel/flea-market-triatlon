import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Plus, Edit, Trash2, Layers, X, ChevronDown, ChevronRight } from 'lucide-react'
import { verifySession } from '@/lib/session'
import { fetchCategories, createCategory, updateCategory, deleteCategory, createSubcategory, updateSubcategory, deleteSubcategory } from '@/lib/api/admin/categories'
import type { Category, CategoryCreate, SubcategoryCreate } from '@/types/admin'

export const Route = createFileRoute('/_admin/admin/categories/')({
  component: CategoriesPage,
  loader: async () => {
    const session = await verifySession()
    return { token: session?.token, isAdmin: session?.isAdmin ?? false }
  },
})

type SubForm = { name: string; key: string; display_order: number; requires_size: boolean; group_key: string }

function CategoriesPage() {
  const { token } = Route.useLoaderData()
  const qc = useQueryClient()
  const [editing, setEditing] = useState<string | null>(null)
  const [newCat, setNewCat] = useState(false)
  const [form, setForm] = useState({ name: '', key: '', icon: '', display_order: 0 })
  const [errors, setErrors] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [editSub, setEditSub] = useState<string | null>(null)
  const [subForm, setSubForm] = useState<SubForm>({ name: '', key: '', display_order: 0, requires_size: false, group_key: '' })
  const [newSub, setNewSub] = useState<string | null>(null)

  const { data: cats, isLoading } = useQuery({
    queryKey: ['admin-categories'],
    queryFn: () => fetchCategories(token!),
    enabled: !!token,
  })

  const createMut = useMutation({
    mutationFn: (d: CategoryCreate) => createCategory(token!, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-categories'] }); setNewCat(false); resetForm() },
    onError: (e: Error) => setErrors(e.message),
  })

  const updateMut = useMutation({
    mutationFn: (d: { key: string; data: Partial<CategoryCreate> }) => updateCategory(token!, d.key, d.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-categories'] }); setEditing(null) },
    onError: (e: Error) => setErrors(e.message),
  })

  const deleteMut = useMutation({
    mutationFn: (key: string) => deleteCategory(token!, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-categories'] }),
  })

  const createSubMut = useMutation({
    mutationFn: (d: SubcategoryCreate) => createSubcategory(token!, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-categories'] }); setNewSub(null) },
  })

  const updateSubMut = useMutation({
    mutationFn: (d: { key: string; data: Partial<SubcategoryCreate> }) => updateSubcategory(token!, d.key, d.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-categories'] }); setEditSub(null) },
  })

  const deleteSubMut = useMutation({
    mutationFn: (key: string) => deleteSubcategory(token!, key),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-categories'] }),
  })

  const resetForm = () => setForm({ name: '', key: '', icon: '', display_order: 0 })
  const resetSubForm = () => setSubForm({ name: '', key: '', display_order: 0, requires_size: false, group_key: '' })
  const toggleExpanded = (key: string) => {
    const next = new Set(expanded)
    expanded.has(key) ? next.delete(key) : next.add(key)
    setExpanded(next)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold flex items-center gap-2"><Layers className="size-5" />Категории</h1>
        <button onClick={() => setNewCat(true)} className="flex items-center gap-1 rounded-lg bg-(--palm) px-3 py-2 text-sm text-white"><Plus className="size-4" />Добавить</button>
      </div>

      {errors && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{errors}<button onClick={() => setErrors(null)} className="float-right"><X className="size-4" /></button></div>}

      {newCat && (
        <div className="mb-4 rounded-lg border p-4 bg-white space-y-2">
          <input placeholder="key (eng)" value={form.key} onChange={e => setForm({ ...form, key: e.target.value })} className="w-full rounded border px-3 py-1.5 text-sm" />
          <input placeholder="Название" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full rounded border px-3 py-1.5 text-sm" />
          <input placeholder="Порядок" type="number" value={form.display_order} onChange={e => setForm({ ...form, display_order: +e.target.value })} className="w-full rounded border px-3 py-1.5 text-sm" />
          <div className="flex gap-2">
            <button onClick={() => createMut.mutate(form)} disabled={!form.key || !form.name} className="rounded bg-green-500 px-3 py-1.5 text-sm text-white disabled:opacity-50">Создать</button>
            <button onClick={() => { setNewCat(false); resetForm() }} className="rounded border px-3 py-1.5 text-sm">Отмена</button>
          </div>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-500">Загрузка...</p> : !cats?.length ? <p className="text-sm text-gray-500">Нет категорий</p> : (
        <div className="space-y-3">
          {cats.map(cat => (
            <div key={cat.key} className="rounded-lg border bg-white">
              {/* Category header */}
              <div className="p-4 border-b border-gray-100">
                {editing === cat.key ? (
                  <div className="space-y-2">
                    <input defaultValue={cat.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full rounded border px-3 py-1.5 text-sm" />
                    <input defaultValue={cat.display_order} type="number" onChange={e => setForm({ ...form, display_order: +e.target.value })} className="w-full rounded border px-3 py-1.5 text-sm" />
                    <div className="flex gap-2">
                      <button onClick={() => updateMut.mutate({ key: cat.key, data: form })} className="rounded bg-(--palm) px-3 py-1.5 text-sm text-white">Сохранить</button>
                      <button onClick={() => setEditing(null)} className="rounded border px-3 py-1.5 text-sm">Отмена</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button onClick={() => toggleExpanded(cat.key)} className="rounded p-0.5 hover:bg-gray-100">
                        {expanded.has(cat.key) ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                      </button>
                      <span className="font-medium">{cat.name}</span>
                      <span className="text-xs text-gray-400">({cat.key}) order:{cat.display_order}</span>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => { setEditing(cat.key); setForm({ name: cat.name, key: cat.key, icon: '', display_order: cat.display_order }) }} className="rounded p-1.5 hover:bg-gray-100"><Edit className="size-4" /></button>
                      <button onClick={() => { if (confirm(`Удалить ${cat.name}?`)) deleteMut.mutate(cat.key) }} className="rounded p-1.5 hover:bg-red-50 text-red-500"><Trash2 className="size-4" /></button>
                    </div>
                  </div>
                )}
              </div>

              {/* Subcategories */}
              {expanded.has(cat.key) && (
                <div className="px-6 py-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-500">Подкатегории ({cat.subcategories.length})</h3>
                    <button onClick={() => { setNewSub(cat.key); resetSubForm(); setSubForm(f => ({ ...f, category_key: cat.key })) }}
                      className="flex items-center gap-1 text-xs text-(--palm) hover:underline"><Plus className="size-3" />Добавить</button>
                  </div>

                  {newSub === cat.key && (
                    <div className="rounded border p-3 bg-gray-50 space-y-1.5">
                      <input placeholder="key" value={subForm.key} onChange={e => setSubForm(f => ({ ...f, key: e.target.value }))} className="w-full rounded border px-2 py-1 text-xs" />
                      <input placeholder="Название" value={subForm.name} onChange={e => setSubForm(f => ({ ...f, name: e.target.value }))} className="w-full rounded border px-2 py-1 text-xs" />
                      <div className="flex items-center gap-3">
                        <input placeholder="Порядок" type="number" value={subForm.display_order} onChange={e => setSubForm(f => ({ ...f, display_order: +e.target.value }))} className="w-20 rounded border px-2 py-1 text-xs" />
                        <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={subForm.requires_size} onChange={e => setSubForm(f => ({ ...f, requires_size: e.target.checked }))} /> Размер</label>
                      </div>
                      <div className="flex gap-1.5">
                        <button onClick={() => createSubMut.mutate({ key: subForm.key, name: subForm.name, category_key: cat.key, display_order: subForm.display_order, requires_size: subForm.requires_size })}
                          disabled={!subForm.key || !subForm.name}
                          className="rounded bg-green-500 px-2 py-1 text-xs text-white disabled:opacity-50">Создать</button>
                        <button onClick={() => setNewSub(null)} className="rounded border px-2 py-1 text-xs">Отмена</button>
                      </div>
                    </div>
                  )}

                  {cat.subcategories.map((sub, i) => (
                    <div key={sub.key} className="flex items-center justify-between rounded border bg-white px-3 py-2">
                      {editSub === sub.key ? (
                        <div className="flex-1 flex items-center gap-2">
                          <input defaultValue={sub.name} onChange={e => setSubForm(f => ({ ...f, name: e.target.value }))} className="w-40 rounded border px-2 py-1 text-xs" />
                          <input defaultValue={sub.display_order} type="number" onChange={e => setSubForm(f => ({ ...f, display_order: +e.target.value }))} className="w-16 rounded border px-2 py-1 text-xs" />
                          <label className="flex items-center gap-1 text-xs"><input type="checkbox" defaultChecked={sub.requires_size} onChange={e => setSubForm(f => ({ ...f, requires_size: e.target.checked }))} /> Размер</label>
                          <button onClick={() => updateSubMut.mutate({ key: sub.key, data: { name: subForm.name, display_order: subForm.display_order, requires_size: subForm.requires_size } })} className="rounded bg-(--palm) px-2 py-1 text-xs text-white">Ок</button>
                          <button onClick={() => setEditSub(null)} className="rounded border px-2 py-1 text-xs">✕</button>
                        </div>
                      ) : (
                        <>
                          <span className="text-sm">{sub.name} <span className="text-xs text-gray-400">({sub.key}) order:{sub.display_order}{sub.requires_size ? ' 📏' : ''}</span></span>
                          <div className="flex gap-1">
                            <button onClick={() => { setEditSub(sub.key); setSubForm({ name: sub.name, key: sub.key, display_order: sub.display_order, requires_size: sub.requires_size, group_key: sub.group_key || '' }) }}
                              className="rounded p-1 hover:bg-gray-100"><Edit className="size-3.5" /></button>
                            <button onClick={() => { if (confirm(`Удалить ${sub.name}?`)) deleteSubMut.mutate(sub.key) }} className="rounded p-1 hover:bg-red-50 text-red-500"><Trash2 className="size-3.5" /></button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                  {cat.subcategories.length === 0 && <p className="text-xs text-gray-400 italic">Нет подкатегорий</p>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Link to="/admin" className="mt-4 inline-block text-sm text-(--palm) hover:underline">← Назад в админку</Link>
    </div>
  )
}
