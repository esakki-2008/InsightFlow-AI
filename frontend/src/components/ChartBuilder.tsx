import { useMemo, useState } from 'react'
import { BarChart3, Loader2, Sparkles } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'
type ChartPoint = { label: string; value: number; x?: number }
type ChartResult = { chart_type: string; x_column: string; y_column: string; aggregation: string; points: ChartPoint[]; total_records: number; filtered_records?: number; filter_column?: string; filter_value?: string; filter_min?: string; filter_max?: string; note?: string }

export default function ChartBuilder({ file, columns, filterColumn, filterValue, filterMin, filterMax, onChartGenerated }: { file: File; columns: { name: string; dtype: string }[]; filterColumn: string; filterValue: string; filterMin: string; filterMax: string; onChartGenerated?: (chart: ChartResult) => void }) {
  const numericColumns = useMemo(() => columns.filter(column => /int|float|double|decimal/i.test(column.dtype)).map(column => column.name), [columns])
  const [xColumn, setXColumn] = useState(columns[0]?.name ?? '')
  const [yColumn, setYColumn] = useState(numericColumns[0] ?? '')
  const [chartType, setChartType] = useState('bar')
  const [aggregation, setAggregation] = useState('sum')
  const [result, setResult] = useState<ChartResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [historyStatus, setHistoryStatus] = useState('')

  const createChart = async () => {
    if (!xColumn) return
    setBusy(true); setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('x_column', xColumn)
      form.append('y_column', chartType === 'scatter' ? yColumn : yColumn)
      form.append('chart_type', chartType)
      form.append('aggregation', aggregation)
      form.append('filter_column', filterColumn)
      form.append('filter_value', filterValue)
      form.append('filter_min', filterMin)
      form.append('filter_max', filterMax)
      const response = await fetch(`${API_URL}/api/v1/datasets/chart`, { method: 'POST', body: form })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Could not generate chart.')
      const chartResult = payload.chart as ChartResult
      setResult(chartResult)
      onChartGenerated?.(chartResult)
      setHistoryStatus('')

      // Save chart configuration and aggregate metadata only, never raw rows.
      try {
        const historyResponse = await fetch(`${API_URL}/api/v1/history`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            analysis_type: 'chart_analysis',
            row_count: chartResult.total_records,
            column_count: columns.length,
            summary: {
              chart_type: chartResult.chart_type,
              x_column: chartResult.x_column,
              y_column: chartResult.y_column,
              aggregation: chartResult.aggregation,
              points_generated: chartResult.points.length,
              filtered_records: chartResult.filtered_records ?? chartResult.total_records,
              filter_column: chartResult.filter_column || null,
              filter_value: chartResult.filter_value || null,
              filter_min: chartResult.filter_min || null,
              filter_max: chartResult.filter_max || null,
              chart_preview: chartResult.points.slice(0, 20),
            },
            notes: 'Chart configuration and aggregate preview saved automatically. Original dataset rows were not stored.',
          }),
        })
        if (!historyResponse.ok) throw new Error('History save request failed')
        setHistoryStatus('Chart generated and saved to Analysis History.')
      } catch {
        setHistoryStatus('Chart generated, but Analysis History could not be saved.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate chart.')
    } finally { setBusy(false) }
  }

  const maxValue = Math.max(...(result?.points.map(point => Math.abs(point.value)) ?? [1]), 1)
  const chartPoints = result?.points ?? []
  const coordinates = chartPoints.map((point, index) => ({
    x: chartPoints.length <= 1 ? 400 : 38 + index * (724 / (chartPoints.length - 1)),
    y: 250 - (Math.max(0, point.value) / maxValue) * 210,
  }))
  const pieTotal = chartPoints.reduce((sum, point) => sum + Math.max(0, point.value), 0)
  const pieStops = chartPoints.reduce<{ stops: string[]; current: number }>((acc, point, index) => {
    const next = acc.current + (pieTotal ? Math.max(0, point.value) / pieTotal * 100 : 0)
    acc.stops.push(`hsl(${(index * 47 + 260) % 360} 78% 60%) ${acc.current}% ${next}%`)
    acc.current = next
    return acc
  }, { stops: [], current: 0 }).stops.join(', ')

  return <div className="mt-5 rounded-xl border border-violet-400/20 bg-violet-500/[0.035] p-5 sm:p-6">
    <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
      <div><div className="flex items-center gap-2 text-violet-300"><BarChart3 size={17}/><h4 className="font-semibold text-white">Interactive chart builder</h4></div><p className="mt-1 text-xs text-zinc-500">Choose fields and generate a visualization from the full dataset.</p></div>
      <span className="text-[10px] tracking-wider text-violet-300">POWER BI-STYLE CHARTS · V1</span>
    </div>
    <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <label className="text-xs text-zinc-400">Chart type<select value={chartType} onChange={event => setChartType(event.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-[#171722] px-3 py-2.5 text-sm text-white"><option value="bar">Bar</option><option value="line">Line</option><option value="pie">Pie</option><option value="donut">Donut</option><option value="histogram">Histogram</option><option value="scatter">Scatter</option></select></label>
      <label className="text-xs text-zinc-400">X-axis / category<select value={xColumn} onChange={event => setXColumn(event.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-[#171722] px-3 py-2.5 text-sm text-white">{columns.map(column => <option key={column.name} value={column.name}>{column.name}</option>)}</select></label>
      <label className="text-xs text-zinc-400">Y-axis / value<select value={yColumn} onChange={event => setYColumn(event.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-[#171722] px-3 py-2.5 text-sm text-white"><option value="">Count records</option>{numericColumns.map(column => <option key={column} value={column}>{column}</option>)}</select></label>
      <label className="text-xs text-zinc-400">Aggregation<select value={aggregation} onChange={event => setAggregation(event.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-[#171722] px-3 py-2.5 text-sm text-white"><option value="sum">Sum</option><option value="mean">Average</option><option value="median">Median</option><option value="count">Count</option></select></label>
      <div className="sm:col-span-2 xl:col-span-3 rounded-lg border border-emerald-500/15 bg-emerald-500/[0.04] px-3 py-3 text-xs text-emerald-300">Using dashboard-wide filter: {filterColumn ? filterColumn : 'None'}{filterValue ? ` · ${filterValue}` : ''}{filterMin ? ` · min ${filterMin}` : ''}{filterMax ? ` · max ${filterMax}` : ''}</div>
    </div>
    <button onClick={createChart} disabled={busy || !xColumn} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-xs font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{busy ? <Loader2 size={15} className="animate-spin"/> : <Sparkles size={15}/>}Generate chart</button>
    {error && <p role="alert" className="mt-3 text-xs text-red-300">{error}</p>}
    {historyStatus && <p role="status" className={`mt-3 text-xs ${historyStatus.includes('could not') ? 'text-amber-300' : 'text-emerald-300'}`}>{historyStatus}</p>}
    {result && <div className="mt-5 rounded-xl border border-white/[0.06] bg-[#101019] p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><h5 className="text-sm font-semibold text-white">{result.aggregation === 'count' ? 'Record count' : result.y_column} by {result.x_column}</h5><p className="mt-1 text-[11px] text-zinc-500">{result.chart_type.toUpperCase()} · {result.aggregation} · {(result.filtered_records ?? result.total_records).toLocaleString()} records</p></div><span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[10px] text-emerald-300">{result.filter_column && (result.filter_value || result.filter_min || result.filter_max) ? "FILTERED DATA" : "FULL DATASET"}</span></div>
      {result.chart_type === 'pie' || result.chart_type === 'donut' ? <div className="flex flex-col items-center gap-5 py-6 sm:flex-row sm:justify-center"><div className="relative h-52 w-52 shrink-0 rounded-full" style={{background: `conic-gradient(${pieStops})`}}>{result.chart_type === 'donut' && <div className="absolute inset-9 flex items-center justify-center rounded-full bg-[#101019] text-center"><div><p className="text-xl font-bold text-white">{pieTotal.toLocaleString(undefined,{maximumFractionDigits:1})}</p><p className="text-[10px] text-zinc-500">Total</p></div></div>}</div><div className="grid gap-2 text-xs">{chartPoints.map((point,index)=><div key={point.label} className="flex items-center gap-2 text-zinc-300"><span className="h-2.5 w-2.5 rounded-sm" style={{background:`hsl(${(index*47+260)%360} 78% 60%)`}}/><span className="max-w-48 truncate">{point.label}</span><span className="text-zinc-500">{point.value.toLocaleString(undefined,{maximumFractionDigits:2})}</span></div>)}</div></div> : <div className="mt-4 overflow-x-auto"><svg viewBox="0 0 800 300" role="img" aria-label={`${result.chart_type} chart for ${result.x_column}`} className="h-auto min-w-[620px] w-full"><line x1="30" y1="250" x2="770" y2="250" stroke="#3f3f50"/><line x1="30" y1="35" x2="30" y2="250" stroke="#3f3f50"/>{result.chart_type === 'line' ? <><polyline points={coordinates.map(point=>`${point.x},${point.y}`).join(' ')} fill="none" stroke="#a78bfa" strokeWidth="3"/>{coordinates.map((point,index)=><circle key={index} cx={point.x} cy={point.y} r="4" fill="#c4b5fd"/>)}</> : result.chart_type === 'scatter' ? chartPoints.map((point,index)=><circle key={index} cx={38+(index/Math.max(chartPoints.length-1,1))*724} cy={250-(point.value/maxValue)*210} r="3.5" fill="#38bdf8" opacity=".75"/>) : chartPoints.map((point,index)=>{const width=Math.max(8,Math.min(30,680/Math.max(chartPoints.length,1)-5));const x=38+index*(724/Math.max(chartPoints.length,1));const height=Math.max(1,Math.abs(point.value)/maxValue*210);return <rect key={point.label} x={x} y={250-height} width={width} height={height} rx="3" fill="#8b5cf6"/>})}{chartPoints.map((point,index)=>{const x=result.chart_type==='line'?coordinates[index].x:38+index*(724/Math.max(chartPoints.length,1));return <text key={point.label} x={x} y="272" fill="#a1a1aa" fontSize="9" textAnchor="middle">{point.label.slice(0,12)}</text>})}</svg></div>}
      {result.note && <p className="mt-2 text-[10px] text-zinc-500">{result.note}</p>}
    </div>}
  </div>
}
