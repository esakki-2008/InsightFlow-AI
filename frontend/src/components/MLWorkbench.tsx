import { useMemo, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Play,
  ShieldCheck,
  Sparkles,
  Upload,
} from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000'

type ModelResult = {
  model: string
  accuracy: number
  precision_macro: number
  recall_macro: number
  f1_macro: number
  confusion_matrix: number[][]
  class_labels: string[]
  training_time_seconds: number
  prediction_time_seconds: number
}

type TrainingResponse = {
  message: string
  filename: string
  preparation: {
    total_rows?: number
    usable_rows?: number
    feature_count?: number
    train_rows?: number
    test_rows?: number
    target_column?: string
    target_classes?: string[]
  }
  training: {
    task: string
    model_id: string
    saved_models: string[]
    models_trained: number
    test_rows: number
    feature_count: number
    class_labels: string[]
    evaluation_metric: string
    results: ModelResult[]
    random_forest_feature_importance: { feature: string; importance: number }[]
  }
}

type PredictionRow = {
  row: number
  predicted_label: string
  confidence: number | null
  class_probabilities: Record<string, number> | null
}

type PredictionResponse = {
  message: string
  filename: string
  prediction: {
    model_id: string
    model_name: string
    target_column: string
    rows_predicted: number
    feature_count: number
    missing_feature_values_filled: number
    prediction_distribution: Record<string, number>
    predictions: PredictionRow[]
  }
}

const panelClass = 'rounded-2xl border border-white/[0.07] bg-[#11111b] p-5 sm:p-6'
const inputClass = 'mt-2 w-full rounded-xl border border-white/10 bg-[#0b0b13] px-3 py-2.5 text-sm text-zinc-200 outline-none transition focus:border-violet-500'

function percent(value: number) {
  return `${(value * 100).toFixed(2)}%`
}

function downloadPredictions(rows: PredictionRow[], filename: string) {
  const headers = ['row', 'predicted_label', 'confidence']
  const csv = [
    headers.join(','),
    ...rows.map((row) => [
      row.row,
      JSON.stringify(row.predicted_label),
      row.confidence ?? '',
    ].join(',')),
  ].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename.replace(/\.[^.]+$/, '') + '_predictions.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function MLWorkbench({ onBack }: { onBack: () => void }) {
  const [trainingFile, setTrainingFile] = useState<File | null>(null)
  const [targetColumn, setTargetColumn] = useState('Label')
  const [testSize, setTestSize] = useState('0.2')
  const [randomState, setRandomState] = useState('42')
  const [isTraining, setIsTraining] = useState(false)
  const [trainingError, setTrainingError] = useState('')
  const [trainingResult, setTrainingResult] = useState<TrainingResponse | null>(null)

  const [predictionFile, setPredictionFile] = useState<File | null>(null)
  const [selectedModel, setSelectedModel] = useState('Random Forest')
  const [isPredicting, setIsPredicting] = useState(false)
  const [predictionError, setPredictionError] = useState('')
  const [predictionResult, setPredictionResult] = useState<PredictionResponse | null>(null)

  const bestModel = useMemo(
    () => trainingResult?.training.results[0] ?? null,
    [trainingResult],
  )

  const trainModels = async () => {
    if (!trainingFile) {
      setTrainingError('Choose a CSV or Excel dataset first.')
      return
    }
    if (!targetColumn.trim()) {
      setTrainingError('Enter the name of the target column.')
      return
    }

    setIsTraining(true)
    setTrainingError('')
    setTrainingResult(null)
    setPredictionResult(null)
    setPredictionError('')

    try {
      const body = new FormData()
      body.append('file', trainingFile)
      body.append('target_column', targetColumn.trim())
      body.append('test_size', testSize)
      body.append('random_state', randomState)
      const response = await fetch(`${API_URL}/api/v1/ml/train`, { method: 'POST', body })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Model training failed.')
      setTrainingResult(result as TrainingResponse)
    } catch (error) {
      setTrainingError(error instanceof Error ? error.message : 'Unable to train models.')
    } finally {
      setIsTraining(false)
    }
  }

  const runPrediction = async () => {
    if (!trainingResult) {
      setPredictionError('Train models first to create a saved model.')
      return
    }
    if (!predictionFile) {
      setPredictionError('Choose a dataset for prediction.')
      return
    }

    setIsPredicting(true)
    setPredictionError('')
    setPredictionResult(null)
    try {
      const body = new FormData()
      body.append('file', predictionFile)
      body.append('model_id', trainingResult.training.model_id)
      body.append('model_name', selectedModel)
      const response = await fetch(`${API_URL}/api/v1/ml/predict`, { method: 'POST', body })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Prediction failed.')
      setPredictionResult(result as PredictionResponse)
    } catch (error) {
      setPredictionError(error instanceof Error ? error.message : 'Unable to generate predictions.')
    } finally {
      setIsPredicting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#09090f] text-zinc-100">
      <header className="sticky top-0 z-10 border-b border-white/5 bg-[#0d0d16]/95 px-5 py-4 backdrop-blur sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={onBack} className="rounded-xl border border-white/10 p-2 text-zinc-400 transition hover:bg-white/5 hover:text-white" aria-label="Back to overview">
              <ArrowLeft size={18} />
            </button>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600/20 text-violet-300">
              <BrainCircuit size={21} />
            </div>
            <div>
              <p className="font-semibold">Machine Learning Studio</p>
              <p className="text-xs text-zinc-500">Train, evaluate and run saved models</p>
            </div>
          </div>
          <span className="hidden rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-xs text-emerald-300 sm:inline-flex">
            <span className="mr-2 mt-1 h-1.5 w-1.5 rounded-full bg-emerald-400" /> API workflow
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 p-5 sm:p-8">
        <section className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 via-[#11111b] to-[#11111b] p-6 sm:p-8">
          <p className="flex items-center gap-2 text-xs font-semibold tracking-[2px] text-violet-300">
            <Sparkles size={15} /> INTELLIGENT MODEL WORKSPACE
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Build models from your data.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">
            Train three baseline classifiers, compare holdout metrics, save the trained bundle, and predict labels for another dataset.
          </p>
        </section>

        <section className={panelClass}>
          <div className="mb-5 flex items-start gap-3">
            <div className="rounded-xl bg-violet-500/10 p-3 text-violet-300"><Upload size={20} /></div>
            <div>
              <h2 className="font-semibold">1. Train classification models</h2>
              <p className="mt-1 text-xs text-zinc-500">Upload a labeled dataset and identify the column to predict.</p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm text-zinc-300">
              Training dataset
              <input className={inputClass} type="file" accept=".csv,.xlsx,.xls" onChange={(event) => setTrainingFile(event.target.files?.[0] ?? null)} />
              {trainingFile && <span className="mt-1 block text-xs text-violet-300">{trainingFile.name}</span>}
            </label>
            <label className="block text-sm text-zinc-300">
              Target column
              <input className={inputClass} value={targetColumn} onChange={(event) => setTargetColumn(event.target.value)} placeholder="e.g. Label" />
            </label>
            <label className="block text-sm text-zinc-300">
              Test data proportion
              <select className={inputClass} value={testSize} onChange={(event) => setTestSize(event.target.value)}>
                <option value="0.1">10% test · 90% train</option>
                <option value="0.2">20% test · 80% train</option>
                <option value="0.25">25% test · 75% train</option>
                <option value="0.3">30% test · 70% train</option>
                <option value="0.4">40% test · 60% train</option>
              </select>
            </label>
            <label className="block text-sm text-zinc-300">
              Random state
              <input className={inputClass} type="number" value={randomState} onChange={(event) => setRandomState(event.target.value)} />
            </label>
          </div>

          <button onClick={trainModels} disabled={isTraining || !trainingFile} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto">
            {isTraining ? <><Loader2 size={17} className="animate-spin" /> Training models...</> : <><Play size={17} /> Train 3 models</>}
          </button>
          {trainingError && <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><AlertCircle size={17} className="mt-0.5 shrink-0" />{trainingError}</div>}
        </section>

        {trainingResult && (
          <>
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'Models trained', value: trainingResult.training.models_trained },
                { label: 'Features used', value: trainingResult.training.feature_count },
                { label: 'Test rows', value: trainingResult.training.test_rows.toLocaleString() },
                { label: 'Target classes', value: trainingResult.training.class_labels.join(' / ') },
              ].map((item) => (
                <div key={item.label} className="rounded-2xl border border-white/[0.07] bg-[#11111b] p-4">
                  <p className="text-xs text-zinc-500">{item.label}</p>
                  <p className="mt-2 break-words text-xl font-bold text-white">{item.value}</p>
                </div>
              ))}
            </section>

            <section className={panelClass}>
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                <div>
                  <h2 className="font-semibold">2. Model evaluation</h2>
                  <p className="mt-1 text-xs text-zinc-500">Metrics calculated on the held-out test split · higher is better</p>
                </div>
                {bestModel && <span className="w-fit rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-xs text-emerald-300">Top macro F1: {bestModel.model}</span>}
              </div>
              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead className="text-xs text-zinc-500">
                    <tr className="border-b border-white/10">
                      {['Model', 'Accuracy', 'Precision', 'Recall', 'Macro F1', 'Train time'].map((heading) => <th key={heading} className="px-3 py-3 font-medium">{heading}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {trainingResult.training.results.map((model) => (
                      <tr key={model.model} className="border-b border-white/5 text-zinc-300">
                        <td className="px-3 py-3 font-medium text-white">{model.model}</td>
                        <td className="px-3 py-3 tabular-nums">{percent(model.accuracy)}</td>
                        <td className="px-3 py-3 tabular-nums">{percent(model.precision_macro)}</td>
                        <td className="px-3 py-3 tabular-nums">{percent(model.recall_macro)}</td>
                        <td className="px-3 py-3 tabular-nums text-violet-300">{percent(model.f1_macro)}</td>
                        <td className="px-3 py-3 tabular-nums">{model.training_time_seconds.toFixed(3)}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs text-zinc-500">{trainingResult.training.evaluation_metric}. Accuracy and macro metrics are shown as reported by the backend.</p>
            </section>

            <section className="grid gap-6 xl:grid-cols-2">
              <div className={panelClass}>
                <h2 className="font-semibold">Confusion matrix</h2>
                <p className="mt-1 text-xs text-zinc-500">Select a model to inspect actual vs predicted counts.</p>
                <div className="mt-4 space-y-3">
                  {trainingResult.training.results.map((model) => (
                    <details key={model.model} className="rounded-xl border border-white/5 bg-white/[0.02] p-3" open={model.model === trainingResult.training.results[0]?.model}>
                      <summary className="cursor-pointer text-sm font-medium text-zinc-200">{model.model}</summary>
                      <div className="mt-3 overflow-x-auto">
                        <table className="min-w-[260px] border-collapse text-center text-xs">
                          <thead><tr><th className="p-2 text-zinc-500">Actual ↓ / Predicted →</th>{model.class_labels.map((label) => <th key={label} className="p-2 text-zinc-400">{label}</th>)}</tr></thead>
                          <tbody>{model.confusion_matrix.map((row, index) => <tr key={model.class_labels[index]}><th className="p-2 text-left text-zinc-400">{model.class_labels[index]}</th>{row.map((value, cell) => <td key={cell} className="rounded-lg bg-violet-500/10 p-3 font-semibold text-violet-200">{value}</td>)}</tr>)}</tbody>
                        </table>
                      </div>
                    </details>
                  ))}
                </div>
              </div>

              <div className={panelClass}>
                <h2 className="font-semibold">Random Forest feature importance</h2>
                <p className="mt-1 text-xs text-zinc-500">Top features ranked by the trained Random Forest model.</p>
                <div className="mt-4 space-y-3">
                  {trainingResult.training.random_forest_feature_importance.map((item) => (
                    <div key={item.feature}>
                      <div className="mb-1 flex justify-between gap-3 text-xs">
                        <span className="truncate text-zinc-300" title={item.feature}>{item.feature}</span>
                        <span className="shrink-0 tabular-nums text-violet-300">{percent(item.importance)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/5"><div className="h-full rounded-full bg-violet-500" style={{ width: `${Math.max(0, Math.min(100, item.importance * 100))}%` }} /></div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-5 sm:p-6">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-0.5 shrink-0 text-emerald-300" size={22} />
                <div className="min-w-0 flex-1">
                  <h2 className="font-semibold text-emerald-200">Saved model bundle</h2>
                  <p className="mt-1 text-xs text-zinc-400">All three fitted estimators were saved together on the backend.</p>
                  <code className="mt-3 block break-all rounded-lg bg-black/20 p-3 text-xs text-emerald-200">{trainingResult.training.model_id}</code>
                  <p className="mt-2 text-xs text-zinc-500">Saved models: {trainingResult.training.saved_models.join(', ')}</p>
                </div>
                <CheckCircle2 className="shrink-0 text-emerald-300" size={20} />
              </div>
            </section>

            <section className={panelClass}>
              <div className="mb-5 flex items-start gap-3">
                <div className="rounded-xl bg-sky-500/10 p-3 text-sky-300"><FileSpreadsheet size={20} /></div>
                <div>
                  <h2 className="font-semibold">3. Predict with a saved model</h2>
                  <p className="mt-1 text-xs text-zinc-500">Upload data containing the same feature columns used during training.</p>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm text-zinc-300">
                  Prediction dataset
                  <input className={inputClass} type="file" accept=".csv,.xlsx,.xls" onChange={(event) => { setPredictionFile(event.target.files?.[0] ?? null); setPredictionResult(null); setPredictionError('') }} />
                  {predictionFile && <span className="mt-1 block text-xs text-sky-300">{predictionFile.name}</span>}
                </label>
                <label className="block text-sm text-zinc-300">
                  Model
                  <select className={inputClass} value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
                    {trainingResult.training.saved_models.map((model) => <option key={model} value={model}>{model}</option>)}
                  </select>
                </label>
              </div>
              <button onClick={runPrediction} disabled={isPredicting || !predictionFile} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-sky-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto">
                {isPredicting ? <><Loader2 size={17} className="animate-spin" /> Predicting...</> : <><Play size={17} /> Run predictions</>}
              </button>
              {predictionError && <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300"><AlertCircle size={17} className="mt-0.5 shrink-0" />{predictionError}</div>}
            </section>
          </>
        )}

        {predictionResult && (
          <section className={panelClass}>
            <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div>
                <div className="flex items-center gap-2 text-emerald-300"><CheckCircle2 size={18} /><h2 className="font-semibold">Prediction completed</h2></div>
                <p className="mt-1 text-xs text-zinc-500">{predictionResult.filename} · {predictionResult.prediction.model_name}</p>
              </div>
              <button onClick={() => downloadPredictions(predictionResult.prediction.predictions, predictionResult.filename)} className="flex items-center justify-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 text-sm font-medium text-emerald-200 transition hover:bg-emerald-500/20">
                <Download size={16} /> Export predictions CSV
              </button>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {[
                { label: 'Rows predicted', value: predictionResult.prediction.rows_predicted.toLocaleString() },
                { label: 'Features used', value: predictionResult.prediction.feature_count },
                { label: 'Missing values filled', value: predictionResult.prediction.missing_feature_values_filled.toLocaleString() },
              ].map((item) => <div key={item.label} className="rounded-xl border border-white/5 bg-white/[0.02] p-4"><p className="text-xs text-zinc-500">{item.label}</p><p className="mt-2 text-2xl font-bold">{item.value}</p></div>)}
            </div>
            <h3 className="mt-6 text-sm font-semibold">Prediction distribution</h3>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {Object.entries(predictionResult.prediction.prediction_distribution).map(([label, count]) => (
                <div key={label} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
                  <div className="flex justify-between text-sm"><span className="text-zinc-300">{label}</span><strong>{count.toLocaleString()}</strong></div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/5"><div className="h-full rounded-full bg-sky-500" style={{ width: `${predictionResult.prediction.rows_predicted ? (count / predictionResult.prediction.rows_predicted) * 100 : 0}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="mt-6 overflow-x-auto rounded-xl border border-white/5">
              <table className="w-full min-w-[520px] text-left text-xs">
                <thead className="bg-white/[0.03] text-zinc-500"><tr>{['Row', 'Predicted label', 'Confidence'].map((heading) => <th key={heading} className="px-3 py-3 font-medium">{heading}</th>)}</tr></thead>
                <tbody>{predictionResult.prediction.predictions.slice(0, 100).map((row) => <tr key={row.row} className="border-t border-white/5 text-zinc-300"><td className="px-3 py-2.5">{row.row}</td><td className="px-3 py-2.5 font-medium">{row.predicted_label}</td><td className="px-3 py-2.5">{row.confidence === null ? '—' : percent(row.confidence)}</td></tr>)}</tbody>
              </table>
              {predictionResult.prediction.predictions.length > 100 && <p className="border-t border-white/5 px-3 py-3 text-xs text-zinc-500">Showing the first 100 rows here. Export the CSV for the complete prediction set.</p>}
            </div>
          </section>
        )}

        <p className="text-xs leading-5 text-zinc-600">
          Model scores are evaluation results for the selected holdout split, not a guarantee of real-world performance. Use representative, properly labeled data and check for leakage before relying on predictions.
        </p>
      </main>
    </div>
  )
}
