import { useState } from 'react'
import { Plus, Trash2, LayoutDashboard } from 'lucide-react'
import ChartBuilder from './ChartBuilder'

type Column = { name: string; dtype: string }

type Props = {
  file: File
  columns: Column[]
  filterColumn: string
  filterValue: string
  filterMin: string
  filterMax: string
}

type ChartPanel = { id: number }
type ChartConfig = { panel_id: number; chart_type: string; x_column: string; y_column: string; aggregation: string; records: number; points_generated: number }

export default function ChartWorkspace({ file, columns, filterColumn, filterValue, filterMin, filterMax }: Props) {
  const [panels, setPanels] = useState<ChartPanel[]>([{ id: 1 }])
  const [nextId, setNextId] = useState(2)
  const [savedCharts, setSavedCharts] = useState<ChartConfig[]>([])
  const [workspaceStatus, setWorkspaceStatus] = useState('')

  const addChart = () => {
    setPanels(current => [...current, { id: nextId }])
    setNextId(current => current + 1)
  }

  const removeChart = (id: number) => {
    setPanels(current => current.length > 1 ? current.filter(panel => panel.id !== id) : current)
    setSavedCharts(current => current.filter(chart => chart.panel_id !== id))
  }

  const saveWorkspace = async (panelId: number, chart: { chart_type: string; x_column: string; y_column: string; aggregation: string; total_records: number; points: { label: string; value: number }[] }) => {
    const nextCharts = [...savedCharts.filter(item => item.panel_id !== panelId), {
      panel_id: panelId,
      chart_type: chart.chart_type,
      x_column: chart.x_column,
      y_column: chart.y_column,
      aggregation: chart.aggregation,
      records: chart.total_records,
      points_generated: chart.points.length,
    }]
    setSavedCharts(nextCharts)
    setWorkspaceStatus('')
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          analysis_type: 'chart_workspace',
          row_count: chart.total_records,
          column_count: columns.length,
          summary: {
            panel_count: panels.length,
            shared_filter: { column: filterColumn || null, value: filterValue || null, min: filterMin || null, max: filterMax || null },
            charts: nextCharts,
          },
          notes: 'Dashboard chart workspace configuration saved automatically. Raw dataset rows were not stored.',
        }),
      })
      if (!response.ok) throw new Error('History save request failed')
      setWorkspaceStatus('Dashboard chart workspace saved to Analysis History.')
    } catch {
      setWorkspaceStatus('Chart generated, but dashboard workspace history could not be saved.')
    }
  }

  return <section className="mt-6 rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6">
    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div>
        <div className="flex items-center gap-2 text-violet-300"><LayoutDashboard size={18}/><h3 className="font-semibold text-white">Dashboard canvas</h3></div>
        <p className="mt-1 text-xs text-zinc-500">Add multiple chart panels. Every panel receives the current dashboard-wide filter settings.</p>
      </div>
      <button onClick={addChart} className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-violet-500">
        <Plus size={15}/> Add chart
      </button>
    </div>
    <div className="mt-2 flex items-center justify-between text-[11px] text-zinc-500">
      <span>{panels.length} chart {panels.length === 1 ? 'panel' : 'panels'}</span>
      <span>{filterColumn ? `Shared filter: ${filterColumn}` : 'No shared filter active'}</span>
    </div>
    {workspaceStatus && <p role="status" className={`mt-2 text-xs ${workspaceStatus.includes('could not') ? 'text-amber-300' : 'text-emerald-300'}`}>{workspaceStatus}</p>}
    <div className="mt-2 grid gap-4">
      {panels.map((panel, index) => <div key={panel.id} className="relative">
        {panels.length > 1 && <div className="flex items-center justify-between rounded-t-xl border border-b-0 border-white/[0.06] bg-white/[0.025] px-4 py-2">
          <span className="text-[11px] font-medium text-zinc-400">Chart panel {index + 1}</span>
          <button onClick={() => removeChart(panel.id)} aria-label={`Remove chart panel ${index + 1}`} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-zinc-500 transition hover:bg-red-500/10 hover:text-red-300"><Trash2 size={12}/> Remove</button>
        </div>}
        <div className={panels.length > 1 ? '[&>div]:mt-0 [&>div]:rounded-t-none' : ''}>
          <ChartBuilder file={file} columns={columns} filterColumn={filterColumn} filterValue={filterValue} filterMin={filterMin} filterMax={filterMax} onChartGenerated={(chart) => void saveWorkspace(panel.id, chart)}/>
        </div>
      </div>)}
    </div>
  </section>
}
