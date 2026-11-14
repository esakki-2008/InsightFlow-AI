import { useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  FileSpreadsheet,
  Lightbulb,
  Loader2,
  Sparkles,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

type Evidence = Record<string, string | number | boolean | null>
type Insight = {
  category: string
  severity: 'positive' | 'warning' | 'info'
  title: string
  description: string
  evidence: Evidence[]
}
type InsightsResponse = {
  message: string
  filename: string
  insights: {
    summary: {
      rows: number
      columns: number
      numeric_columns: number
      categorical_columns: number
      missing_values: number
      duplicate_rows: number
      insights_generated: number
    }
    insights: Insight[]
    method: string
  }
}

type Props = { onBack: () => void }

const summaryCards = [
  { key: 'rows', label: 'Rows analyzed' },
  { key: 'columns', label: 'Columns' },
  { key: 'missing_values', label: 'Missing values' },
  { key: 'insights_generated', label: 'Insights generated' },
] as const

const severityStyles = {
  positive: 'border-emerald-500/20 bg-emerald-500/[0.05] text-emerald-300',
  warning: 'border-amber-500/20 bg-amber-500/[0.05] text-amber-300',
  info: 'border-sky-500/20 bg-sky-500/[0.05] text-sky-300',
}

function formatEvidence(evidence: Evidence) {
  return Object.entries(evidence)
    .map(([key, value]) => `${key.replaceAll('_', ' ')}: ${typeof value === 'number' ? value.toLocaleString() : String(value)}`)
    .join(' · ')
}

export default function InsightsWorkbench({ onBack }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<InsightsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const generateInsights = async () => {
    if (!file) {
      setError('Select a CSV or Excel dataset first.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)
    try {
      const body = new FormData()
      body.append('file', file)
      const response = await fetch(`${API_URL}/api/v1/datasets/insights`, {
        method: 'POST',
        body,
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || 'Unable to generate dataset insights.')
      }
      setResult(payload as InsightsResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong while generating insights.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#09090f] text-zinc-100">
      <header className="flex h-20 items-center justify-between border-b border-white/5 px-6 lg:px-10">
        <div>
          <p className="text-xs text-zinc-500">Workspace / AI Insights</p>
          <h1 className="mt-1 text-lg font-semibold">Dataset Insights</h1>
        </div>
        <button onClick={onBack} className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-sm text-zinc-300 hover:bg-white/5">
          <ArrowLeft size={16} /> Back to overview
        </button>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-6 lg:p-10">
        <section className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/[0.10] to-[#11111b] p-6 sm:p-8">
          <div className="flex items-center gap-2 text-sm font-medium tracking-wide text-violet-300">
            <Sparkles size={17} /> INTELLIGENT DATA ANALYST
          </div>
          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Turn dataset statistics into clear insights.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">
            Upload a CSV or Excel file to identify data-quality issues, potential outliers,
            skewed distributions, dominant categories, and strong numeric relationships.
          </p>
          <div className="mt-6 grid gap-3 sm:grid-cols-[1fr_auto]">
            <label className="flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-violet-400/30 bg-black/20 px-4 py-3">
              <FileSpreadsheet className="shrink-0 text-violet-300" size={20} />
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-zinc-200">{file?.name ?? 'Choose a dataset file'}</span>
                <span className="mt-1 block text-xs text-zinc-500">CSV, XLSX or XLS · Maximum 10 MB</span>
              </span>
              <input className="sr-only" type="file" accept=".csv,.xlsx,.xls" disabled={loading} onChange={event => { setFile(event.target.files?.[0] ?? null); setResult(null); setError('') }} />
            </label>
            <button onClick={generateInsights} disabled={!file || loading} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40">
              {loading ? <><Loader2 size={17} className="animate-spin" /> Analyzing...</> : <><Lightbulb size={17} /> Generate insights</>}
            </button>
          </div>
          {error && <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><AlertCircle size={17} className="mt-0.5 shrink-0" />{error}</div>}
        </section>

        {result && (
          <>
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
              <div>
                <div className="flex items-center gap-2 text-emerald-300"><CheckCircle2 size={18} /><span className="text-sm font-semibold">Analysis completed</span></div>
                <p className="mt-1 break-all text-xs text-zinc-500">{result.filename}</p>
              </div>
              <p className="text-xs text-zinc-500">{result.insights.summary.numeric_columns} numeric · {result.insights.summary.categorical_columns} categorical columns</p>
            </div>

            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {summaryCards.map(card => (
                <div key={card.key} className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5">
                  <p className="text-xs text-zinc-500">{card.label}</p>
                  <p className="mt-3 text-3xl font-bold tabular-nums">{result.insights.summary[card.key].toLocaleString()}</p>
                </div>
              ))}
            </section>

            <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
              <div className="mb-5 flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-semibold">AI-generated dataset insights</h3>
                  <p className="mt-1 text-xs text-zinc-500">Evidence-backed observations from statistical profiling</p>
                </div>
                <span className="rounded-lg bg-violet-500/10 px-3 py-1.5 text-xs text-violet-300">{result.insights.insights.length} findings</span>
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                {result.insights.insights.map((insight, index) => (
                  <article key={`${insight.category}-${index}`} className={`rounded-xl border p-5 ${severityStyles[insight.severity]}`}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-[1.5px] opacity-80">{insight.category.replaceAll('_', ' ')}</span>
                      <span className="rounded-full border border-current/20 px-2.5 py-1 text-[10px] font-semibold uppercase">{insight.severity}</span>
                    </div>
                    <h4 className="mt-3 text-base font-semibold text-zinc-100">{insight.title}</h4>
                    <p className="mt-2 text-sm leading-6 text-zinc-300">{insight.description}</p>
                    {insight.evidence.length > 0 && (
                      <div className="mt-4 space-y-2 border-t border-white/10 pt-3">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Supporting evidence</p>
                        {insight.evidence.map((item, itemIndex) => <p key={itemIndex} className="rounded-lg bg-black/20 px-3 py-2 text-xs leading-5 text-zinc-300">{formatEvidence(item)}</p>)}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-sky-500/15 bg-sky-500/[0.04] p-4">
              <div className="flex items-start gap-3">
                <Lightbulb className="mt-0.5 shrink-0 text-sky-300" size={18} />
                <div>
                  <h3 className="text-sm font-semibold text-sky-200">How these insights are generated</h3>
                  <p className="mt-1 text-xs leading-5 text-zinc-400">{result.insights.method}</p>
                  <p className="mt-2 text-xs text-zinc-500">These are descriptive statistical observations, not causal conclusions or a substitute for domain review.</p>
                </div>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}
