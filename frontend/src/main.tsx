import { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Activity, Bot, CheckCircle2, ChevronRight, Clock3, Globe2, Plus, Radio, Sparkles, X } from 'lucide-react'
import './styles.css'

type Status = 'queued' | 'planning' | 'running' | 'recovering' | 'completed' | 'failed' | 'cancelled'
type Event = { id: string; at: string; kind: string; message: string; data: Record<string, unknown> }
type Task = { id: string; objective: string; start_url?: string; status: Status; created_at: string; plan: string[]; events: Event[]; result?: string }
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const sample: Task = {
  id: 'preview', objective: 'Research the latest browser automation patterns', start_url: 'https://playwright.dev', status: 'running', created_at: new Date().toISOString(),
  plan: ['Parse task intent and scope', 'Visit documentation and inspect sections', 'Return sourced findings'],
  events: [
    { id: '1', at: new Date().toISOString(), kind: 'system', message: 'Task accepted by runtime', data: {} },
    { id: '2', at: new Date().toISOString(), kind: 'plan', message: 'Execution plan created', data: {} },
    { id: '3', at: new Date().toISOString(), kind: 'action', message: 'Browser session allocated', data: {} },
  ]
}

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedId, setSelectedId] = useState<string>('preview')
  const [objective, setObjective] = useState('')
  const [url, setUrl] = useState('')
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState('')
  const selected = useMemo(() => tasks.find(t => t.id === selectedId) || (selectedId === 'preview' ? sample : tasks[0]), [tasks, selectedId])

  async function load() {
    try { const response = await fetch(`${API}/api/tasks`); if (response.ok) setTasks(await response.json()) } catch { /* API can be started after UI */ }
  }
  useEffect(() => { load(); const timer = setInterval(load, 3000); return () => clearInterval(timer) }, [])
  useEffect(() => {
    if (selectedId === 'preview') return
    const stream = new EventSource(`${API}/api/tasks/${selectedId}/events`)
    stream.onmessage = ({ data }) => {
      const event: Event = JSON.parse(data)
      setTasks(current => current.map(task => task.id === selectedId && !task.events.some(existing => existing.id === event.id)
        ? { ...task, events: [...task.events, event] }
        : task))
      load()
    }
    return () => stream.close()
  }, [selectedId])

  async function createTask(event: React.FormEvent) {
    event.preventDefault()
    if (objective.trim().length < 5) {
      setFormError('Describe the mission in at least 5 characters.')
      return
    }
    setCreating(true)
    setFormError('')
    try {
      const response = await fetch(`${API}/api/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ objective, start_url: url || undefined }) })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail?.[0]?.msg || 'Could not create task')
      }
      const task: Task = await response.json(); setTasks(current => [task, ...current]); setSelectedId(task.id); setObjective(''); setUrl('')
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not create task')
    } finally { setCreating(false) }
  }
  async function cancelTask() {
    if (!selected || selected.id === 'preview') return
    const response = await fetch(`${API}/api/tasks/${selected.id}/cancel`, { method: 'POST' })
    if (response.ok) {
      const task: Task = await response.json()
      setTasks(current => current.map(item => item.id === task.id ? task : item))
    }
  }
  const active = tasks.filter(t => ['queued', 'planning', 'running', 'recovering'].includes(t.status)).length

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark"><Bot size={19}/></span><span>webagent<span>runtime</span></span></div>
      <div className="nav-label">WORKSPACE</div>
      <button className="nav-item active"><Activity size={17}/> Mission control</button>
      <button className="nav-item"><Clock3 size={17}/> Task history <b>{tasks.length}</b></button>
      <div className="nav-label lower">SYSTEM</div>
      <button className="nav-item"><Globe2 size={17}/> Browser fleet</button>
      <button className="nav-item"><Sparkles size={17}/> Model routing</button>
      <div className="sidebar-foot"><span className="live-dot"/> Runtime online</div>
    </aside>
    <section className="workspace">
      <header><div><p className="eyebrow">OPERATOR CONSOLE</p><h1>Mission control</h1><p className="subtle">Give an objective. Watch the agent reason, browse, and recover.</p></div><div className="health"><Radio size={15}/><span>All systems nominal</span></div></header>
      <form className="composer" onSubmit={createTask}>
        <div className="composer-icon"><Sparkles size={18}/></div><div className="fields"><input value={objective} onChange={e => setObjective(e.target.value)} placeholder="What should the browser agent accomplish?" /><input className="url" value={url} onChange={e => setUrl(e.target.value)} placeholder="Starting URL (optional)" /></div>
        <button type="submit" disabled={creating || objective.trim().length < 5}>{creating ? 'Launching…' : <><Plus size={17}/> Launch task</>}</button>
      </form>
      {formError && <p style={{ color: '#eea4a9', fontSize: 12, margin: '8px 4px 0' }}>{formError}</p>}
      <div className="metrics"><Metric label="Active missions" value={String(active)} tint="violet"/><Metric label="Tasks completed" value={String(tasks.filter(t => t.status === 'completed').length)} tint="green"/><Metric label="Browser sessions" value={active ? String(active) : '0'} tint="blue"/></div>
      <div className="content-grid">
        <section className="panel queue"><div className="panel-head"><div><p className="eyebrow">TASK QUEUE</p><h2>Agent missions</h2></div><span className="count">{tasks.length || 1}</span></div>
          <div className="task-list">{(tasks.length ? tasks : [sample]).map(task => <button className={`task ${selected?.id === task.id ? 'selected' : ''}`} key={task.id} onClick={() => setSelectedId(task.id)}><div className="task-top"><StatusBadge status={task.status}/><time>{new Date(task.created_at).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}</time></div><strong>{task.objective}</strong>{task.start_url && <span className="task-url"><Globe2 size={12}/>{task.start_url.replace(/^https?:\/\//, '')}</span>}<ChevronRight className="arrow" size={16}/></button>)}</div>
        </section>
        <section className="panel detail"><div className="panel-head"><div><p className="eyebrow">LIVE TRACE</p><h2>{selected?.objective || 'Select a mission'}</h2></div><div className="trace-actions">{selected && ['queued', 'planning', 'running', 'recovering'].includes(selected.status) && selected.id !== 'preview' && <button className="cancel" onClick={cancelTask}><X size={13}/> Cancel</button>}{selected && <StatusBadge status={selected.status}/>}</div></div>
          {selected && <><div className="plan"><p>EXECUTION PLAN</p>{selected.plan.map((step, index) => <div className="plan-step" key={step}><span>{index + 1}</span>{step}</div>)}</div><div className="timeline">{selected.events.map((event, index) => <div className="event" key={event.id}><div className={`event-dot ${event.kind}`}>{event.kind === 'system' ? <CheckCircle2 size={13}/> : <Activity size={13}/>}</div>{index < selected.events.length - 1 && <i/>}<div><span className="event-kind">{event.kind}</span><p>{event.message}</p>{Object.keys(event.data).length > 0 && <code>{JSON.stringify(event.data)}</code>}</div></div>)}</div>{selected.result && <div className="result"><Sparkles size={16}/><span>{selected.result}</span></div>}</>}
        </section>
      </div>
    </section>
  </main>
}

function Metric({ label, value, tint }: { label: string; value: string; tint: string }) { return <div className="metric"><div className={`metric-icon ${tint}`}><Activity size={17}/></div><div><span>{label}</span><strong>{value}</strong></div></div> }
function StatusBadge({ status }: { status: Status }) { return <span className={`status ${status}`}><span/>{status}</span> }
export default App

createRoot(document.getElementById('root')!).render(<App />)
