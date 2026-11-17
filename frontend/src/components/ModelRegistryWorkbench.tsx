import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, BrainCircuit, RefreshCw, Search, AlertCircle, CheckCircle2, Database, CalendarDays } from 'lucide-react'

import { API_URL, apiFetch } from '../config/api'

interface ModelMetric {
  model: string
  accuracy: number
  precision_macro: number
  recall_macro: number
  f1_macro: number
}

interface SavedModel {
  model_id: string
  created_at: string
  target_column: string
  feature_count: number
  class_labels: string[]
  model_names: string[]
  dataset_filename?: string
  test_rows?: number
  metrics?: ModelMetric[]
  registered_at?: string
}

interface RegistryResponse {
  total_models: number
  registered_models: number
  models: SavedModel[]
  storage_note?: string
}

interface Props {
  onBack: () => void
}

const percent = (value: number) => `${(value * 100).toFixed(1)}%`
const dateLabel = (value?: string) => {
  if (!value) return 'Not registered'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export default function ModelRegistryWorkbench({ onBack }: Props) {
  const [data, setData] = useState<RegistryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [showRegisteredOnly, setShowRegisteredOnly] = useState(false)

  const loadModels = useCallback(async () => {
    try {
      const response = await apiFetch(`${API_URL}/api/v1/ml/models`)
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Unable to load the model registry.')
      setError('')
      setData(result as RegistryResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to connect to the backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => { void loadModels() }, 0)
    return () => window.clearTimeout(timeoutId)
  }, [loadModels])

  const models = useMemo(() => {
    const items = data?.models ?? []
    return items.filter((model) => {
      const matchesQuery = [model.model_id, model.dataset_filename, model.target_column, ...(model.class_labels ?? [])]
        .filter(Boolean).join(' ').toLowerCase().includes(query.toLowerCase())
      return matchesQuery && (!showRegisteredOnly || Boolean(model.registered_at))
    })
  }, [data, query, showRegisteredOnly])

  return (
    <div className="min-h-screen bg-[#09090f] px-5 py-7 text-zinc-100 lg:px-10">
      <div className="mx-auto max-w-7xl space-y-7">
        <button onClick={onBack} className="inline-flex items-center gap-2 text-sm text-zinc-400 transition hover:text-white"><ArrowLeft size={17} /> Back to overview</button>
        <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="mb-2 flex items-center gap-2 text-sm font-medium text-violet-300"><BrainCircuit size={17} /> MODEL MANAGEMENT</p>
            <h1 className="text-3xl font-bold tracking-tight">ML Model Registry</h1>
            <p className="mt-2 max-w-2xl text-sm text-zinc-500">Browse trained model bundles, evaluation metrics and database registration metadata.</p>
          </div>
          <button onClick={() => { setLoading(true); setError(''); void loadModels() }} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-sm font-medium hover:bg-white/[0.08] disabled:opacity-50"><RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh registry</button>
        </header>

        {error && <div className="flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300"><AlertCircle size={18} className="mt-0.5 shrink-0" />{error}</div>}

        <section className="grid gap-4 sm:grid-cols-3">
          {[
            { label: 'Saved model bundles', value: data?.total_models ?? '—', icon: BrainCircuit },
            { label: 'Database registered', value: data?.registered_models ?? '—', icon: Database },
            { label: 'Not yet registered', value: data ? Math.max(0, data.total_models - data.registered_models) : '—', icon: CalendarDays },
          ].map((item) => {
            const Icon = item.icon
            return <div key={item.label} className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><div className="flex items-center justify-between text-sm text-zinc-500"><span>{item.label}</span><Icon size={18} className="text-violet-300" /></div><p className="mt-4 text-3xl font-bold tabular-nums">{item.value}</p></div>
          })}
        </section>

        <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <label className="relative block flex-1"><Search size={17} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search dataset, target, class or model ID..." className="w-full rounded-xl border border-white/10 bg-black/20 py-3 pl-10 pr-4 text-sm text-white outline-none focus:border-violet-500/50" /></label>
            <label className="flex items-center gap-2 text-sm text-zinc-400"><input type="checkbox" checked={showRegisteredOnly} onChange={(event) => setShowRegisteredOnly(event.target.checked)} className="accent-violet-500" /> Registered in database only</label>
          </div>
        </section>

        {loading && !data ? <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-10 text-center text-sm text-zinc-500">Loading saved models...</div> : models.length === 0 ? <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-10 text-center text-sm text-zinc-500">No models match this filter.</div> : (
          <div className="space-y-4">
            {models.map((model) => (
              <article key={model.model_id} className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
                <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{model.dataset_filename || 'Legacy model bundle'}</h2>{model.registered_at ? <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-300"><CheckCircle2 size={12} /> Database registered</span> : <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-200">Artifact only</span>}</div>
                    <p className="mt-2 break-all font-mono text-[11px] text-zinc-600">{model.model_id}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm sm:min-w-[260px]">
                    <div className="rounded-xl bg-white/[0.03] p-3"><p className="text-xs text-zinc-500">Target</p><p className="mt-1 font-medium">{model.target_column}</p></div>
                    <div className="rounded-xl bg-white/[0.03] p-3"><p className="text-xs text-zinc-500">Features</p><p className="mt-1 font-medium">{model.feature_count}</p></div>
                  </div>
                </div>
                <div className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                  <div><p className="text-xs text-zinc-500">Test rows</p><p className="mt-1 font-medium">{model.test_rows?.toLocaleString() ?? '—'}</p></div>
                  <div><p className="text-xs text-zinc-500">Classes</p><p className="mt-1 font-medium">{model.class_labels?.join(', ') || '—'}</p></div>
                  <div><p className="text-xs text-zinc-500">Trained</p><p className="mt-1 font-medium">{dateLabel(model.created_at)}</p></div>
                  <div><p className="text-xs text-zinc-500">Registered</p><p className="mt-1 font-medium">{dateLabel(model.registered_at)}</p></div>
                </div>
                <div className="mt-5 flex flex-wrap gap-2">{model.model_names.map((name) => <span key={name} className="rounded-lg border border-violet-500/15 bg-violet-500/[0.06] px-3 py-1.5 text-xs text-violet-200">{name}</span>)}</div>
                {model.metrics?.length ? <div className="mt-5 overflow-x-auto rounded-xl border border-white/[0.06]"><table className="w-full min-w-[600px] text-left text-xs"><thead className="bg-white/[0.03] text-zinc-500"><tr>{['Model', 'Accuracy', 'Precision (macro)', 'Recall (macro)', 'F1 (macro)'].map((heading) => <th key={heading} className="px-4 py-3 font-medium">{heading}</th>)}</tr></thead><tbody>{model.metrics.map((metric) => <tr key={metric.model} className="border-t border-white/[0.05] text-zinc-300"><td className="px-4 py-3 font-medium text-white">{metric.model}</td><td className="px-4 py-3 tabular-nums">{percent(metric.accuracy)}</td><td className="px-4 py-3 tabular-nums">{percent(metric.precision_macro)}</td><td className="px-4 py-3 tabular-nums">{percent(metric.recall_macro)}</td><td className="px-4 py-3 tabular-nums">{percent(metric.f1_macro)}</td></tr>)}</tbody></table></div> : <p className="mt-4 text-xs text-zinc-600">Detailed evaluation metrics were not recorded for this older model bundle.</p>}
              </article>
            ))}
          </div>
        )}
        {data?.storage_note && <p className="text-xs leading-5 text-zinc-600">{data.storage_note}</p>}
      </div>
    </div>
  )
}
