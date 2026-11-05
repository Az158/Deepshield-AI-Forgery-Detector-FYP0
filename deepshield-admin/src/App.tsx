import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clipboard,
  FileText,
  Gauge,
  LayoutDashboard,
  Lock,
  LogOut,
  Search,
  Settings,
  ShieldCheck,
  X,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import clsx from 'clsx'
import logoUrl from './assets/logo.png'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Page = 'overview' | 'logs' | 'settings'

type AdminUser = {
  user_id: string
  email: string
  role: 'admin' | 'investigator' | 'viewer'
  display_name?: string
}

type Metrics = {
  total_analyses: number
  fake_rate: number
  average_confidence: number
  blockchain_confirmed_rate: number
  trend: Array<{ date: string; count: number }>
  media_breakdown: Record<string, number>
  prediction_breakdown: Record<string, number>
  alerts: Array<{ type: string; message: string; severity: string }>
}

type Analysis = {
  id: string
  user_id?: string
  filename?: string
  media_type?: string
  prediction?: string
  confidence?: number
  band?: string
  ucf_prob?: number
  ai_prob?: number
  heatmap_url?: string
  pdf_url?: string
  created_at?: string
  block_number?: number
  blockchain_tx_hash?: string
  polygon_url?: string
  blockchain_status?: string
  reviewed_status?: string
}

type Detail = {
  analysis: Analysis
  blockchain_anchors: Array<Record<string, unknown>>
  pdf_reports: Array<Record<string, unknown>>
  review_notes: Array<Record<string, unknown>>
  dedup_references: Array<Record<string, unknown>>
}

type AdminProfile = {
  id: string
  display_name?: string
  role: string
  status: string
  created_at?: string
  last_active_at?: string
}

type BlockchainStatus = {
  chain: string
  chain_id: number
  status: string
  confirmed_last_7_days: number
  failed_last_7_days: number
  latest_block?: number
}

type AuditLog = {
  id: string
  action: string
  target_type?: string
  target_id?: string
  details?: Record<string, unknown>
  created_at?: string
}

type SettingRow = {
  key: string
  value: Record<string, unknown>
  updated_at?: string
}

function shortHash(value?: string) {
  if (!value) return '-'
  return value.length > 22 ? `${value.slice(0, 12)}...${value.slice(-8)}` : value
}

function formatDate(value?: string) {
  if (!value) return '-'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function percent(value?: number) {
  if (value === undefined || Number.isNaN(value)) return '-'
  return `${value.toFixed(1)}%`
}

async function request<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail ?? `Request failed: ${response.status}`)
  }

  return response.json() as Promise<T>
}

async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })

  if (!response.ok) {
    throw new Error('Invalid email or password')
  }

  return response.json() as Promise<{ access_token: string; email: string }>
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('ds_admin_token') ?? '')
  const [admin, setAdmin] = useState<AdminUser | null>(null)
  const [page, setPage] = useState<Page>('overview')
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [users, setUsers] = useState<AdminProfile[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [settings, setSettings] = useState<SettingRow[]>([])
  const [blockchain, setBlockchain] = useState<BlockchainStatus | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<Detail | null>(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [refreshNonce, setRefreshNonce] = useState(0)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  useEffect(() => {
    if (!token) return
    localStorage.setItem('ds_admin_token', token)
    request<AdminUser>('/admin/me', token)
      .then(setAdmin)
      .catch((err) => {
        setError(err.message)
        setToken('')
        localStorage.removeItem('ds_admin_token')
      })
  }, [token])

  useEffect(() => {
    if (!token || !admin) return
    async function loadDashboard() {
      setLoading(true)
      try {
        const [metricsData, analysisData, userData, blockchainData, auditData, settingsData] = await Promise.all([
          request<Metrics>('/admin/metrics', token),
          request<{ analyses: Analysis[] }>('/admin/analyses?limit=200', token),
          request<{ users: AdminProfile[] }>('/admin/users', token),
          request<BlockchainStatus>('/admin/blockchain/status', token),
          request<{ logs: AuditLog[] }>('/admin/audit-logs?limit=20', token),
          request<{ settings: SettingRow[] }>('/admin/settings', token),
        ])
        setMetrics(metricsData)
        setAnalyses(analysisData.analyses)
        setUsers(userData.users)
        setBlockchain(blockchainData)
        setAuditLogs(auditData.logs)
        setSettings(settingsData.settings)
        setLastUpdated(new Date())
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load dashboard')
      } finally {
        setLoading(false)
      }
    }
    void loadDashboard()
  }, [token, admin, refreshNonce])

  useEffect(() => {
    if (!token || !admin) return
    const id = window.setInterval(() => setRefreshNonce((value) => value + 1), 12000)
    return () => window.clearInterval(id)
  }, [token, admin])

  useEffect(() => {
    if (!selectedId || !token) return
    request<Detail>(`/admin/analyses/${selectedId}`, token)
      .then(setDetail)
      .catch((err) => setError(err.message))
  }, [selectedId, token])

  const filteredAnalyses = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return analyses.filter((item) => {
      const matchesQuery =
        !needle ||
        [item.filename, item.prediction, item.band, item.id]
          .join(' ')
          .toLowerCase()
          .includes(needle)
      const matchesStatus = !statusFilter || item.blockchain_status === statusFilter
      return matchesQuery && matchesStatus
    })
  }, [analyses, query, statusFilter])

  function openAnalysis(id: string) {
    setDetail(null)
    setSelectedId(id)
  }

  if (!token || !admin) {
    return <LoginScreen onLogin={setToken} error={error} setError={setError} />
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img src={logoUrl} className="brand-logo" alt="DeepShield logo" />
          <div>
            <strong>DeepShield</strong>
            <span>Investigator Dashboard</span>
          </div>
        </div>
        <nav>
          <NavButton icon={<LayoutDashboard size={17} />} active={page === 'overview'} onClick={() => setPage('overview')}>
            Overview
          </NavButton>
          <NavButton icon={<FileText size={17} />} active={page === 'logs'} onClick={() => setPage('logs')}>
            Logs & Reports
          </NavButton>
          <NavButton icon={<Settings size={17} />} active={page === 'settings'} onClick={() => setPage('settings')}>
            Settings/Admin
          </NavButton>
        </nav>
        <div className="sidebar-footer">
          <span>{admin.email}</span>
          <button
            type="button"
            onClick={() => {
              setToken('')
              setAdmin(null)
              localStorage.removeItem('ds_admin_token')
            }}
          >
            <LogOut size={15} />
            Logout
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <span className="eyebrow">DeepShield v2.1</span>
            <h1>{page === 'overview' ? 'Overview Dashboard' : page === 'logs' ? 'Logs & Reports' : 'Settings & Administration'}</h1>
          </div>
          <div className="topbar-actions">
            <span className="last-updated">
              {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Sync pending'}
            </span>
            <button type="button" className="refresh-button" onClick={() => setRefreshNonce((value) => value + 1)}>
              Refresh
            </button>
            <div className="operator">
              <span>{admin.role}</span>
              <div>{admin.display_name?.slice(0, 1) || admin.email.slice(0, 1).toUpperCase()}</div>
            </div>
          </div>
        </header>

        {error && (
          <div className="banner">
            <AlertTriangle size={16} />
            {error}
            <button type="button" onClick={() => setError('')}>
              <X size={14} />
            </button>
          </div>
        )}

        {loading && <div className="loading-bar" />}

        {page === 'overview' && <Overview metrics={metrics} analyses={analyses} blockchain={blockchain} auditLogs={auditLogs} />}
        {page === 'logs' && (
          <Logs
            analyses={filteredAnalyses}
            query={query}
            setQuery={setQuery}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            onSelect={openAnalysis}
          />
        )}
        {page === 'settings' && (
          <AdminSettings
            users={users}
            blockchain={blockchain}
            metrics={metrics}
            auditLogs={auditLogs}
            settings={settings}
            token={token}
            adminRole={admin.role}
            refresh={() => setRefreshNonce((value) => value + 1)}
          />
        )}
      </main>

      {selectedId && (
        <DetailDrawer
          detail={detail}
          onClose={() => {
            setSelectedId(null)
            setDetail(null)
          }}
          token={token}
          refresh={() => {
            request<Detail>(`/admin/analyses/${selectedId}`, token).then(setDetail)
          }}
        />
      )}
    </div>
  )
}

function LoginScreen({
  onLogin,
  error,
  setError,
}: {
  onLogin: (token: string) => void
  error: string
  setError: (value: string) => void
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await login(email, password)
      onLogin(result.access_token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="brand login-brand">
          <img src={logoUrl} className="brand-logo" alt="DeepShield logo" />
          <div>
            <strong>DeepShield Admin</strong>
            <span>Supabase authenticated access</span>
          </div>
        </div>
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
        </label>
        <label>
          Password
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" disabled={busy}>
          <Lock size={16} />
          {busy ? 'Checking access...' : 'Enter dashboard'}
        </button>
      </form>
    </div>
  )
}

function NavButton({
  active,
  icon,
  children,
  onClick,
}: {
  active: boolean
  icon: ReactNode
  children: ReactNode
  onClick: () => void
}) {
  return (
    <button type="button" className={clsx('nav-button', active && 'active')} onClick={onClick}>
      {icon}
      {children}
    </button>
  )
}

function Overview({
  metrics,
  analyses,
  blockchain,
  auditLogs,
}: {
  metrics: Metrics | null
  analyses: Analysis[]
  blockchain: BlockchainStatus | null
  auditLogs: AuditLog[]
}) {
  const pieData = metrics
    ? Object.entries(metrics.prediction_breakdown).map(([name, value]) => ({ name, value }))
    : []
  const mediaData = metrics
    ? Object.entries(metrics.media_breakdown).map(([name, count]) => ({ name, count }))
    : []
  const recent = analyses.slice(0, 5)

  return (
    <div className="dashboard-grid">
      <MetricCard icon={<Activity />} label="Total Analyses" value={metrics?.total_analyses.toLocaleString() ?? '-'} note="All submitted media" />
      <MetricCard icon={<AlertTriangle />} label="Fake Result %" value={percent(metrics?.fake_rate)} note="Manipulated or synthetic" tone="danger" />
      <MetricCard icon={<Gauge />} label="Average Confidence" value={percent(metrics?.average_confidence)} note="Mean detector confidence" />
      <MetricCard icon={<ShieldCheck />} label="Blockchain Confirmed" value={percent(metrics?.blockchain_confirmed_rate)} note="Anchored report hashes" tone="ok" />

      <section className="panel wide">
        <PanelHeader title="Monthly Trend" subtitle="Analyses over recent days" />
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={metrics?.trend ?? []}>
            <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#111827', border: '1px solid #263244' }} />
            <Area type="monotone" dataKey="count" stroke="#0ea5e9" fill="#0ea5e933" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </section>

      <section className="panel">
        <PanelHeader title="Result Distribution" subtitle="Prediction classes" />
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={82}>
              {pieData.map((_, index) => (
                <Cell key={index} fill={['#0ea5e9', '#ef4444', '#f59e0b', '#22c55e'][index % 4]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: '#111827', border: '1px solid #263244' }} />
          </PieChart>
        </ResponsiveContainer>
      </section>

      <section className="panel danger-panel">
        <PanelHeader title="Critical System Alerts" subtitle="Operational attention" />
        {(metrics?.alerts ?? []).map((alert, index) => (
          <div className="alert-row" key={`${alert.type}-${index}`}>
            <AlertTriangle size={16} />
            <span>{alert.message}</span>
          </div>
        ))}
        <div className="chain-status">
          <ShieldCheck size={16} />
          <span>
            {blockchain?.chain ?? 'DeepShield Private Chain'}: {blockchain?.status ?? 'unknown'}
          </span>
        </div>
      </section>

      <section className="panel wide">
        <PanelHeader title="Content Types Analyzed" subtitle="Image/video split" />
        <ResponsiveContainer width="100%" height={230}>
          <BarChart data={mediaData}>
            <XAxis dataKey="name" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip contentStyle={{ background: '#111827', border: '1px solid #263244' }} />
            <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section className="panel">
        <PanelHeader title="Recent System Activity" subtitle="Live audit stream" />
        <div className="activity-list">
          {auditLogs.length
            ? auditLogs.slice(0, 5).map((item) => (
                <div className="activity-item" key={item.id}>
                  <span>{formatDate(item.created_at)}</span>
                  <strong>{item.action.replaceAll('.', ' ')}</strong>
                  <small>{item.target_id ?? item.target_type ?? 'system'}</small>
                </div>
              ))
            : recent.map((item) => (
                <div className="activity-item" key={item.id}>
                  <span>{formatDate(item.created_at)}</span>
                  <strong>{item.prediction ?? 'Unknown'}</strong>
                  <small>{item.filename ?? item.id}</small>
                </div>
              ))}
        </div>
      </section>
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  note,
  tone,
}: {
  icon: ReactNode
  label: string
  value: string
  note: string
  tone?: 'danger' | 'ok'
}) {
  return (
    <section className={clsx('metric-card', tone)}>
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </section>
  )
}

function Logs({
  analyses,
  query,
  setQuery,
  statusFilter,
  setStatusFilter,
  onSelect,
}: {
  analyses: Analysis[]
  query: string
  setQuery: (value: string) => void
  statusFilter: string
  setStatusFilter: (value: string) => void
  onSelect: (id: string) => void
}) {
  return (
    <section className="panel full">
      <div className="toolbar">
        <div className="search">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search filename, verdict, hash..." />
        </div>
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="">All blockchain states</option>
          <option value="confirmed">Confirmed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date/Time</th>
              <th>Filename</th>
              <th>Type</th>
              <th>Outcome</th>
              <th>Confidence</th>
              <th>Blockchain</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((item) => (
              <tr key={item.id} onClick={() => onSelect(item.id)}>
                <td>{formatDate(item.created_at)}</td>
                <td>{item.filename ?? '-'}</td>
                <td>{item.media_type ?? '-'}</td>
                <td>
                  <span className={clsx('badge', _resultTone(item))}>{item.prediction ?? 'Unknown'}</span>
                </td>
                <td>{item.confidence !== undefined ? `${(item.confidence * 100).toFixed(1)}%` : '-'}</td>
                <td>
                  <span className={clsx('badge', item.blockchain_status)}>{item.blockchain_status ?? 'pending'}</span>
                </td>
                <td>{item.reviewed_status ?? 'unreviewed'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function _resultTone(item: Analysis) {
  const value = `${item.prediction ?? ''} ${item.band ?? ''}`.toLowerCase()
  if (value.includes('fake') || value.includes('manipulated')) return 'failed'
  if (value.includes('authentic') || value.includes('real')) return 'confirmed'
  return 'pending'
}

function DetailDrawer({
  detail,
  onClose,
  token,
  refresh,
}: {
  detail: Detail | null
  onClose: () => void
  token: string
  refresh: () => void
}) {
  const [note, setNote] = useState('')
  const analysis = detail?.analysis
  const anchor = detail?.blockchain_anchors?.[0]

  async function updateStatus(status: string) {
    if (!analysis) return
    await request(`/admin/analyses/${analysis.id}/review-status`, token, {
      method: 'PATCH',
      body: JSON.stringify({ reviewed_status: status }),
    })
    refresh()
  }

  async function submitNote() {
    if (!analysis || !note.trim()) return
    await request(`/admin/analyses/${analysis.id}/notes`, token, {
      method: 'POST',
      body: JSON.stringify({ note }),
    })
    setNote('')
    refresh()
  }

  return (
    <aside className="drawer">
      <button type="button" className="drawer-close" onClick={onClose}>
        <X size={18} />
      </button>
      {!analysis ? (
        <div className="drawer-loading">Loading analysis...</div>
      ) : (
        <>
          <span className="eyebrow">Analysis Log Details</span>
          <h2>{analysis.filename ?? analysis.id}</h2>
          <dl className="detail-grid">
            <dt>Date/Time</dt>
            <dd>{formatDate(analysis.created_at)}</dd>
            <dt>User</dt>
            <dd>{analysis.user_id ?? '-'}</dd>
            <dt>Outcome</dt>
            <dd>{analysis.prediction ?? '-'}</dd>
            <dt>Confidence</dt>
            <dd>{analysis.confidence !== undefined ? `${(analysis.confidence * 100).toFixed(2)}%` : '-'}</dd>
            <dt>Band</dt>
            <dd>{analysis.band ?? '-'}</dd>
            <dt>UCF Probability</dt>
            <dd>{analysis.ucf_prob !== undefined ? `${(analysis.ucf_prob * 100).toFixed(2)}%` : '-'}</dd>
            <dt>AI Probability</dt>
            <dd>{analysis.ai_prob !== undefined ? `${(analysis.ai_prob * 100).toFixed(2)}%` : '-'}</dd>
            <dt>Report Hash</dt>
            <dd className="mono">{String(anchor?.report_hash ?? '-')}</dd>
            <dt>Transaction</dt>
            <dd className="mono">{shortHash(String(anchor?.tx_hash ?? analysis.blockchain_tx_hash ?? ''))}</dd>
            <dt>Block</dt>
            <dd>{String(anchor?.block_number ?? analysis.block_number ?? '-')}</dd>
          </dl>

          <div className="drawer-actions">
            {analysis.pdf_url && (
              <a href={analysis.pdf_url} target="_blank" rel="noreferrer">
                Download PDF
              </a>
            )}
            {analysis.heatmap_url && (
              <a href={analysis.heatmap_url} target="_blank" rel="noreferrer">
                View Heatmap
              </a>
            )}
            <button type="button" onClick={() => navigator.clipboard.writeText(analysis.blockchain_tx_hash ?? '')}>
              <Clipboard size={14} />
              Copy TX
            </button>
          </div>

          <div className="review-row">
            {['reviewed', 'flagged', 'dismissed'].map((status) => (
              <button key={status} type="button" onClick={() => updateStatus(status)}>
                {status}
              </button>
            ))}
          </div>

          <label className="note-box">
            Review note
            <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add investigator note..." />
            <button type="button" onClick={submitNote}>
              Save note
            </button>
          </label>

          <div className="notes">
            {(detail?.review_notes ?? []).map((item) => (
              <div key={String(item.id)}>
                <span>{formatDate(String(item.created_at ?? ''))}</span>
                <p>{String(item.note ?? '')}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  )
}

function AdminSettings({
  users,
  blockchain,
  metrics,
  auditLogs,
  settings,
  token,
  adminRole,
  refresh,
}: {
  users: AdminProfile[]
  blockchain: BlockchainStatus | null
  metrics: Metrics | null
  auditLogs: AuditLog[]
  settings: SettingRow[]
  token: string
  adminRole: string
  refresh: () => void
}) {
  async function updateUser(userId: string, patch: Record<string, string>) {
    await request(`/admin/users/${userId}`, token, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    })
    refresh()
  }

  async function updateSetting(key: string, value: Record<string, unknown>) {
    await request(`/admin/settings/${key}`, token, {
      method: 'PATCH',
      body: JSON.stringify({ value }),
    })
    refresh()
  }

  return (
    <div className="settings-grid">
      <section className="panel wide">
        <PanelHeader title="User Management" subtitle="Admin profile roles and access status" />
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Last Active</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.display_name ?? user.id}</td>
                <td>
                  {adminRole === 'admin' ? (
                    <select value={user.role} onChange={(event) => updateUser(user.id, { role: event.target.value })}>
                      <option value="admin">admin</option>
                      <option value="investigator">investigator</option>
                      <option value="viewer">viewer</option>
                    </select>
                  ) : (
                    <span className="badge">{user.role}</span>
                  )}
                </td>
                <td>
                  {adminRole === 'admin' ? (
                    <select value={user.status} onChange={(event) => updateUser(user.id, { status: event.target.value })}>
                      <option value="active">active</option>
                      <option value="suspended">suspended</option>
                    </select>
                  ) : (
                    <span className={clsx('badge', user.status === 'active' ? 'confirmed' : 'failed')}>{user.status}</span>
                  )}
                </td>
                <td>{formatDate(user.last_active_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <PanelHeader title="AI Thresholds & Sensitivity" subtitle="Current operational posture" />
        <div className="slider-row">
          <span>Real threshold</span>
          <strong>{String(settings.find((item) => item.key === 'ai_thresholds')?.value?.real ?? 0.3)}</strong>
          <div style={{ width: `${Number(settings.find((item) => item.key === 'ai_thresholds')?.value?.real ?? 0.3) * 100}%` }} />
        </div>
        <div className="slider-row danger">
          <span>Fake threshold</span>
          <strong>{String(settings.find((item) => item.key === 'ai_thresholds')?.value?.fake ?? 0.7)}</strong>
          <div style={{ width: `${Number(settings.find((item) => item.key === 'ai_thresholds')?.value?.fake ?? 0.7) * 100}%` }} />
        </div>
        {adminRole === 'admin' && (
          <button
            type="button"
            className="secondary-action"
            onClick={() => updateSetting('ai_thresholds', { real: 0.3, fake: 0.7, ai_generated: 0.8 })}
          >
            Reset default thresholds
          </button>
        )}
      </section>

      <section className="panel">
        <PanelHeader title="System Configuration & Status" subtitle="Current private chain runtime" />
        <dl className="detail-grid">
          <dt>Chain</dt>
          <dd>{blockchain?.chain ?? 'DeepShield Private Chain'}</dd>
          <dt>Chain ID</dt>
          <dd>{blockchain?.chain_id ?? 31337}</dd>
          <dt>Status</dt>
          <dd>{blockchain?.status ?? 'unknown'}</dd>
          <dt>Latest Block</dt>
          <dd>{blockchain?.latest_block ?? '-'}</dd>
          <dt>Confirmed 7d</dt>
          <dd>{blockchain?.confirmed_last_7_days ?? 0}</dd>
        </dl>
      </section>

      <section className="panel">
        <PanelHeader title="Recent Admin Actions" subtitle="Audit stream summary" />
        <div className="activity-list">
          {auditLogs.slice(0, 6).map((item) => (
            <div className="activity-item" key={item.id}>
              <span>{formatDate(item.created_at)}</span>
              <strong>{item.action.replaceAll('.', ' ')}</strong>
              <small>{item.target_id ?? JSON.stringify(item.details ?? {})}</small>
            </div>
          ))}
          {!auditLogs.length && (
            <div className="activity-item">
              <span>System</span>
              <strong>{metrics?.total_analyses ?? 0} total analyses indexed</strong>
              <small>No audit events yet</small>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}

function PanelHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="panel-header">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <BarChart3 size={17} />
    </div>
  )
}

export default App
