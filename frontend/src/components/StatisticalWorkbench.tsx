import { useState } from 'react'
import { ArrowLeft, AlertCircle, FileSpreadsheet, Loader2, UploadCloud, Activity, Sigma } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'
type Statistics = {
  overview: { numeric_features_analyzed: number; correlation_pairs_analyzed: number; group_comparisons_analyzed: number }
  distributions: { column: string; count: number; mean: number; median: number; std_dev: number; min: number; q1: number; q3: number; max: number; skewness: number | null; kurtosis: number | null; normality_test: { test: string; statistic: number; p_value: number; interpretation: string } | null }[]
  correlations: { left: string; right: string; sample_size: number; pearson_r: number; pearson_p_value: number; spearman_rho: number; spearman_p_value: number; strength: string; significant_at_5_percent: boolean }[]
  group_comparisons: { category_column: string; numeric_column: string; groups: { name: string; count: number; mean: number }[]; test: string; f_statistic: number; p_value: number; significant_at_5_percent: boolean }[]
  methodology: Record<string, string>
}
const fmt = (value: number | null) => value === null ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: 4 })
const fmtP = (value: number) => value === 0 ? '< 1e-300' : value < 0.0001 ? value.toExponential(2) : value.toFixed(6).replace(/0+$/, '').replace(/\\.$/, '')
function Card({ title, value, note }: { title: string; value: string; note: string }) { return <div className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><p className="text-xs text-zinc-500">{title}</p><p className="mt-3 text-2xl font-bold text-white">{value}</p><p className="mt-2 text-xs text-zinc-600">{note}</p></div> }

export default function StatisticalWorkbench({ onBack }: { onBack: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [data, setData] = useState<Statistics | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [historyStatus, setHistoryStatus] = useState('')
  const run = async () => {
    if (!file) { setError('Choose a CSV or Excel dataset first.'); return }
    setBusy(true); setError(''); setHistoryStatus(''); setData(null)
    try {
      const form = new FormData(); form.append('file', file)
      const response = await fetch(`${API_URL}/api/v1/datasets/statistics`, { method: 'POST', body: form })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Statistical analysis failed.')
      const statistics = result.statistics as Statistics
      setData(statistics)
      try {
        const historyResponse = await fetch(`${API_URL}/api/v1/history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            analysis_type: 'statistical_analysis',
            row_count: result.rows ?? null,
            column_count: result.columns ?? null,
            summary: {
              numeric_features_analyzed: statistics.overview.numeric_features_analyzed,
              correlation_pairs_analyzed: statistics.overview.correlation_pairs_analyzed,
              group_comparisons_analyzed: statistics.overview.group_comparisons_analyzed,
              significant_correlations: statistics.correlations.filter(item => item.significant_at_5_percent).length,
              significant_group_comparisons: statistics.group_comparisons.filter(item => item.significant_at_5_percent).length
            },
            notes: 'Automatically saved after successful statistical analysis.'
          })
        })
        if (!historyResponse.ok) throw new Error('History save failed')
        setHistoryStatus('This statistical analysis was automatically saved to Analysis History.')
      } catch {
        setHistoryStatus('Analysis completed, but it could not be saved to Analysis History. You can retry from the History page after checking the backend.')
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to analyze this dataset.') }
    finally { setBusy(false) }
  }
  return <div className="min-h-screen bg-[#09090f] text-zinc-100">
    <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[#0d0d16]/95 backdrop-blur"><div className="mx-auto flex h-18 max-w-[1500px] items-center gap-3 px-5 sm:px-8"><button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 hover:bg-white/5" aria-label="Back"><ArrowLeft size={18}/></button><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600"><Sigma size={21}/></div><div><p className="font-semibold">InsightFlow AI</p><p className="text-[10px] tracking-[1.8px] text-zinc-500">STATISTICAL ANALYTICS</p></div></div></header>
    <main className="mx-auto max-w-[1500px] space-y-7 px-5 py-8 sm:px-8 lg:py-10">
      <section><p className="mb-2 text-xs font-semibold tracking-[2px] text-violet-300">ADVANCED ANALYTICS</p><h1 className="text-3xl font-bold sm:text-4xl">Statistical analysis<span className="text-violet-400">.</span></h1><p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-500">Explore distribution shape, normality tests, Pearson and Spearman relationships, and differences between categorical groups.</p></section>
      <section className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-5"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div className="flex items-center gap-3"><div className="rounded-xl bg-violet-500/10 p-3 text-violet-300"><UploadCloud size={21}/></div><div><h2 className="font-semibold">Analyze a dataset</h2><p className="mt-1 text-xs text-zinc-500">CSV, XLSX or XLS · maximum 10 MB</p></div></div><div className="flex flex-col gap-3 sm:flex-row sm:items-center"><label className="flex min-w-0 cursor-pointer items-center gap-3 rounded-xl border border-dashed border-white/15 px-4 py-3 sm:min-w-[330px]"><FileSpreadsheet size={19} className="shrink-0 text-violet-300"/><span className="min-w-0 flex-1 truncate text-sm text-zinc-300">{file ? file.name : 'Choose a dataset file'}</span><input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={e => { setFile(e.target.files?.[0] ?? null); setData(null); setError('') }}/></label><button onClick={run} disabled={!file || busy} className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40">{busy ? <><Loader2 size={17} className="animate-spin"/>Analyzing…</> : <><Activity size={17}/>Run statistics</>}</button></div></div>{error && <p role="alert" className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300"><AlertCircle size={16}/>{error}</p>}</section>
      {historyStatus && <p role="status" className="rounded-xl border border-violet-500/20 bg-violet-500/5 px-4 py-3 text-sm text-violet-200">{historyStatus}</p>}
      {!data && <div className="rounded-2xl border border-dashed border-white/10 px-6 py-16 text-center"><Sigma className="mx-auto mb-3 text-zinc-600" size={30}/><p className="font-medium text-zinc-300">Statistical results will appear here</p><p className="mt-2 text-sm text-zinc-600">Upload a dataset to calculate statistical tests and relationships.</p></div>}
      {data && <>
        <section className="grid gap-3 sm:grid-cols-3"><Card title="Numeric features" value={String(data.overview.numeric_features_analyzed)} note="Distribution profiles"/><Card title="Correlation pairs" value={String(data.overview.correlation_pairs_analyzed)} note="Pearson and Spearman tests"/><Card title="Group comparisons" value={String(data.overview.group_comparisons_analyzed)} note="One-way ANOVA"/></section>
        <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#11111b]"><div className="border-b border-white/[0.06] p-5"><h2 className="font-semibold">Distribution & normality</h2><p className="mt-1 text-xs text-zinc-500">Quartiles, skewness, kurtosis and Shapiro-Wilk test where applicable.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-xs"><thead className="bg-white/[0.025] text-zinc-500"><tr>{['Feature','N','Mean','Median','Std dev','Min','Q1','Q3','Max','Skewness','Kurtosis','Normality p'].map(x=><th key={x} className="px-3 py-3 font-medium">{x}</th>)}</tr></thead><tbody>{data.distributions.map(row=><tr key={row.column} className="border-t border-white/[0.05]"><td className="px-3 py-3 font-medium text-zinc-200">{row.column}</td><td className="px-3 py-3">{row.count}</td>{[row.mean,row.median,row.std_dev,row.min,row.q1,row.q3,row.max,row.skewness,row.kurtosis,row.normality_test?.p_value ?? null].map((v,i)=><td key={i} className="px-3 py-3 text-zinc-400">{fmt(v)}</td>)}</tr>)}</tbody></table></div><div className="space-y-2 p-5">{data.distributions.filter(x=>x.normality_test).map(x=><p key={x.column} className="text-xs text-zinc-400"><span className="font-semibold text-zinc-200">{x.column}:</span> {x.normality_test?.interpretation} (p = {x.normality_test ? fmtP(x.normality_test.p_value) : '—'})</p>)}</div></section>
        <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#11111b]"><div className="border-b border-white/[0.06] p-5"><h2 className="font-semibold">Correlation significance</h2><p className="mt-1 text-xs text-zinc-500">Sorted by absolute Pearson correlation.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead className="bg-white/[0.025] text-zinc-500"><tr>{['Feature A','Feature B','Pearson r','Pearson p','Spearman ρ','Spearman p','N','Result'].map(x=><th key={x} className="px-4 py-3 font-medium">{x}</th>)}</tr></thead><tbody>{data.correlations.map((x,i)=><tr key={i} className="border-t border-white/[0.05]"><td className="px-4 py-3 text-zinc-200">{x.left}</td><td className="px-4 py-3 text-zinc-200">{x.right}</td><td className="px-4 py-3">{fmt(x.pearson_r)}</td><td className="px-4 py-3">{fmtP(x.pearson_p_value)}</td><td className="px-4 py-3">{fmt(x.spearman_rho)}</td><td className="px-4 py-3">{fmtP(x.spearman_p_value)}</td><td className="px-4 py-3">{x.sample_size}</td><td className={`px-4 py-3 ${x.significant_at_5_percent ? 'text-emerald-300' : 'text-zinc-500'}`}>{x.significant_at_5_percent ? 'Significant' : 'Not significant'} · {x.strength}</td></tr>)}</tbody></table>{data.correlations.length===0 && <p className="p-5 text-sm text-zinc-500">No valid numeric pairs were found.</p>}</div></section>
        <section className="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#11111b]"><div className="border-b border-white/[0.06] p-5"><h2 className="font-semibold">Group comparison (one-way ANOVA)</h2><p className="mt-1 text-xs text-zinc-500">Compares numeric means across categorical groups.</p></div><div className="space-y-3 p-5">{data.group_comparisons.map((x,i)=><div key={i} className="rounded-xl border border-white/[0.06] p-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-zinc-200">{x.numeric_column} by {x.category_column}</p><span className={`text-xs ${x.significant_at_5_percent ? 'text-emerald-300' : 'text-zinc-500'}`}>{x.significant_at_5_percent ? 'Significant difference' : 'No significant difference'} · p={fmtP(x.p_value)}</span></div><p className="mt-1 text-xs text-zinc-500">F = {x.f_statistic}</p><div className="mt-3 flex flex-wrap gap-2">{x.groups.map(g=><span key={g.name} className="rounded-lg bg-white/[0.04] px-3 py-2 text-xs text-zinc-300">{g.name}: mean {fmt(g.mean)} (n={g.count})</span>)}</div></div>)}{data.group_comparisons.length===0 && <p className="text-sm text-zinc-500">No eligible categorical group comparisons found.</p>}</div></section>
        <section className="rounded-2xl border border-amber-500/20 bg-[#11111b] p-5"><h2 className="font-semibold text-amber-200">Interpretation & limitations</h2><ul className="mt-3 list-disc space-y-2 pl-5 text-xs leading-5 text-zinc-400">{Object.values(data.methodology).map((x,i)=><li key={i}>{x}</li>)}</ul></section>
      </>}
    </main>
  </div>
}
