import { ArrowLeft, Bot, KeyRound, ShieldCheck, UserRound, Workflow } from 'lucide-react'
import type { AuthUser } from '../config/api'

interface SettingsWorkbenchProps {
  user: AuthUser
  onBack: () => void
}

const sections = [
  {
    title: 'AI Providers',
    description: 'Connect AI services, manage provider credentials and choose models for Dataset Q&A.',
    icon: Bot,
    status: 'Coming in Phase 2',
  },
  {
    title: 'API Credentials',
    description: 'Provider keys will be encrypted on the server and isolated to your account.',
    icon: KeyRound,
    status: 'Secure setup next',
  },
  {
    title: 'Privacy & Security',
    description: 'Your account and workspace data remain separated from other users.',
    icon: ShieldCheck,
    status: 'Authentication enabled',
  },
  {
    title: 'Model Preferences',
    description: 'Select a connected provider and model for AI-powered dataset questions.',
    icon: Workflow,
    status: 'Coming in Phase 3',
  },
]

export default function SettingsWorkbench({ user, onBack }: SettingsWorkbenchProps) {
  return (
    <main className="min-h-screen bg-[#09090f] px-5 py-8 text-zinc-100 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-5xl">
        <button
          type="button"
          onClick={onBack}
          className="mb-8 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-zinc-400 transition hover:border-violet-500/40 hover:text-white"
        >
          <ArrowLeft size={16} /> Back to dashboard
        </button>

        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-400">Workspace configuration</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Settings</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
            Manage your account, AI connections and workspace preferences from one place.
          </p>
        </div>

        <section className="mb-6 rounded-2xl border border-white/[0.08] bg-[#11111b] p-5 sm:p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet-500/10 text-violet-300">
              <UserRound size={22} />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="font-semibold text-white">Account</h2>
              <p className="mt-1 text-xs text-zinc-500">Signed in account</p>
              <p className="mt-2 break-all text-sm text-zinc-200">{user.email}</p>
              <p className="mt-2 text-xs text-zinc-600">Your settings and connected providers will belong only to this account.</p>
            </div>
            <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-medium text-emerald-300">Authenticated</span>
          </div>
        </section>

        <div className="grid gap-4 md:grid-cols-2">
          {sections.map((section) => {
            const Icon = section.icon
            return (
              <section key={section.title} className="rounded-2xl border border-white/[0.08] bg-[#11111b] p-5 transition hover:border-violet-500/25">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04] text-violet-300">
                    <Icon size={19} />
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] text-zinc-400">{section.status}</span>
                </div>
                <h3 className="mt-5 font-semibold text-zinc-100">{section.title}</h3>
                <p className="mt-2 text-sm leading-6 text-zinc-500">{section.description}</p>
              </section>
            )
          })}
        </div>

        <div className="mt-6 rounded-xl border border-sky-500/15 bg-sky-500/[0.04] p-4 text-sm leading-6 text-sky-200/80">
          AI provider management is being added next. No API key is requested or stored on this page yet.
        </div>
      </div>
    </main>
  )
}
