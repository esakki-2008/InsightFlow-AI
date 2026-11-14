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

export default function ChartWorkspace({ file, columns, filterColumn, filterValue, filterMin, filterMax }: Props) {
  const [panels, setPanels] = useState<ChartPanel[]>([{ id: 1 }])
  const [nextId, setNextId] = useState(2)

  const addChart = () => {
    setPanels(current => [...current, { id: nextId }])
    setNextId(current => current + 1)
  }

  const removeChart = (id: number) => {
    setPanels(current => current.length > 1 ? current.filter(panel => panel.id !== id) : current)
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
    <div className="mt-2 grid gap-4">
      {panels.map((panel, index) => <div key={panel.id} className="relative">
        {panels.length > 1 && <div className="flex items-center justify-between rounded-t-xl border border-b-0 border-white/[0.06] bg-white/[0.025] px-4 py-2">
          <span className="text-[11px] font-medium text-zinc-400">Chart panel {index + 1}</span>
          <button onClick={() => removeChart(panel.id)} aria-label={`Remove chart panel ${index + 1}`} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-zinc-500 transition hover:bg-red-500/10 hover:text-red-300"><Trash2 size={12}/> Remove</button>
        </div>}
        <div className={panels.length > 1 ? '[&>div]:mt-0 [&>div]:rounded-t-none' : ''}>
          <ChartBuilder file={file} columns={columns} filterColumn={filterColumn} filterValue={filterValue} filterMin={filterMin} filterMax={filterMax}/>
        </div>
      </div>)}
    </div>
  </section>
}
