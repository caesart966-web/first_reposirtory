import { Check, CheckSquare, Plus, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Header } from '../components/Header'
import { useAppData } from '../hooks/useData'
import { createTask, deleteTask, updateTask } from '../db/repo'
import {
  PRIORITIES,
  PRIORITY_LABEL,
  PRIORITY_TONE,
  TASK_STATUSES,
  TASK_STATUS_LABEL,
  TASK_STATUS_TONE,
  type Priority,
  type Task,
  type TaskStatus,
} from '../db/types'
import { addDays, cn, formatDeadline, plural, today } from '../lib/utils'
import { Button } from '../ui/Button'
import { Choice } from '../ui/Choice'
import { Field, Input, Textarea } from '../ui/Field'
import { EmptyState, SkeletonList } from '../ui/Feedback'
import { Pill } from '../ui/Pill'
import { ConfirmSheet, Sheet } from '../ui/Sheet'
import { useToast } from '../ui/Toast'

type Group = 'overdue' | 'today' | 'week' | 'later' | 'done'

const GROUP_LABEL: Record<Group, string> = {
  overdue: 'Просрочено',
  today: 'Сегодня',
  week: 'На неделе',
  later: 'Потом',
  done: 'Готово',
}

const GROUP_ORDER: Group[] = ['overdue', 'today', 'week', 'later', 'done']

function groupOf(t: Task): Group {
  if (t.status === 'done') return 'done'
  if (!t.deadline) return 'later'
  const day = today()
  if (t.deadline < day) return 'overdue'
  if (t.deadline === day) return 'today'
  if (t.deadline <= addDays(day, 7)) return 'week'
  return 'later'
}

export function Tasks() {
  const { tasks, clients, clientById, loading } = useAppData()
  const toast = useToast()
  const [quick, setQuick] = useState('')
  const [editing, setEditing] = useState<Task | null>(null)
  const [creating, setCreating] = useState(false)

  const grouped = useMemo(() => {
    const map = new Map<Group, Task[]>()
    for (const t of tasks ?? []) {
      const g = groupOf(t)
      const arr = map.get(g) ?? []
      arr.push(t)
      map.set(g, arr)
    }
    for (const arr of map.values()) {
      arr.sort((a, b) => (a.deadline ?? '9999').localeCompare(b.deadline ?? '9999'))
    }
    return map
  }, [tasks])

  const openCount = (tasks ?? []).filter((t) => t.status !== 'done').length

  const addQuick = async () => {
    const title = quick.trim()
    if (!title) return
    await createTask({ title })
    setQuick('')
    toast('Задача добавлена')
  }

  const toggleDone = async (t: Task) => {
    await updateTask(t.id, { status: t.status === 'done' ? 'new' : 'done' })
  }

  return (
    <div>
      <Header
        title="Задачи"
        subtitle={openCount ? `${plural(openCount, 'открытая', 'открытые', 'открытых')} задача` : undefined}
      />

      {/* Быстрое добавление одной строкой */}
      <div className="flex gap-2 px-4">
        <Input
          value={quick}
          onChange={(e) => setQuick(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addQuick()}
          placeholder="Что нужно сделать"
        />
        <Button onClick={addQuick} className="shrink-0 px-4" aria-label="Добавить задачу">
          <Plus size={20} />
        </Button>
      </div>

      <div className="mt-5 space-y-6 px-4">
        {loading ? (
          <SkeletonList count={3} />
        ) : (tasks ?? []).length === 0 ? (
          <EmptyState
            icon={<CheckSquare size={26} />}
            title="Задач нет"
            text="Впиши строкой сверху всё, что не должно забыться: позвонить, выставить счёт, продлить домен."
          />
        ) : (
          GROUP_ORDER.map((g) => {
            const items = grouped.get(g) ?? []
            if (!items.length) return null
            return (
              <section key={g}>
                <div className="mb-2.5 flex items-center gap-2 px-1">
                  <h2 className="text-body-lg font-semibold tracking-tight">{GROUP_LABEL[g]}</h2>
                  <span
                    className={cn(
                      'tnum text-caption font-medium',
                      g === 'overdue' ? 'text-danger' : 'text-muted',
                    )}
                  >
                    {items.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-center gap-3 rounded-card border border-line bg-surface p-3 shadow-soft"
                    >
                      <button
                        onClick={() => toggleDone(t)}
                        aria-label={t.status === 'done' ? 'Вернуть в работу' : 'Отметить готовой'}
                        className={cn(
                          'tap flex h-11 w-11 shrink-0 items-center justify-center rounded-btn border transition-colors duration-150 ease-out',
                          t.status === 'done'
                            ? 'border-money/30 bg-money/10 text-money'
                            : 'border-line text-muted hover:border-accent/40 hover:text-accent',
                        )}
                      >
                        <Check size={18} strokeWidth={t.status === 'done' ? 2.6 : 2} />
                      </button>

                      <button onClick={() => setEditing(t)} className="min-w-0 flex-1 text-left">
                        <div
                          className={cn(
                            'truncate text-body',
                            t.status === 'done' && 'text-muted line-through',
                          )}
                        >
                          {t.title}
                        </div>
                        <div className="mt-0.5 flex items-center gap-2 text-caption text-muted">
                          <span className={cn(g === 'overdue' && 'text-danger')}>
                            {formatDeadline(t.deadline)}
                          </span>
                          {t.clientId && clientById.get(t.clientId) && (
                            <span className="truncate">· {clientById.get(t.clientId)!.name}</span>
                          )}
                        </div>
                      </button>

                      {t.status !== 'done' && t.status !== 'new' && (
                        <Pill tone={TASK_STATUS_TONE[t.status]} size="sm">
                          {TASK_STATUS_LABEL[t.status]}
                        </Pill>
                      )}
                      {t.priority === 'high' && t.status !== 'done' && (
                        <Pill tone={PRIORITY_TONE.high} size="sm">
                          !
                        </Pill>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )
          })
        )}
      </div>

      <button
        onClick={() => setCreating(true)}
        aria-label="Новая задача"
        className="fixed bottom-[calc(78px+env(safe-area-inset-bottom,0px))] right-4 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-accent text-white shadow-lift transition-transform duration-150 ease-out active:scale-95"
      >
        <Plus size={26} />
      </button>

      <TaskSheet
        open={creating || !!editing}
        task={editing}
        clients={clients ?? []}
        onClose={() => {
          setCreating(false)
          setEditing(null)
        }}
      />
    </div>
  )
}

function TaskSheet({
  open,
  task,
  clients,
  onClose,
}: {
  open: boolean
  task: Task | null
  clients: Array<{ id: string; name: string }>
  onClose: () => void
}) {
  const toast = useToast()
  const [title, setTitle] = useState('')
  const [clientId, setClientId] = useState<string | null>(null)
  const [deadline, setDeadline] = useState<string | null>(null)
  const [status, setStatus] = useState<TaskStatus>('new')
  const [priority, setPriority] = useState<Priority>('medium')
  const [notes, setNotes] = useState('')
  const [confirm, setConfirm] = useState(false)

  useEffect(() => {
    if (!open) return
    setTitle(task?.title ?? '')
    setClientId(task?.clientId ?? null)
    setDeadline(task?.deadline ?? null)
    setStatus(task?.status ?? 'new')
    setPriority(task?.priority ?? 'medium')
    setNotes(task?.notes ?? '')
  }, [open, task])

  const save = async () => {
    if (!title.trim()) return toast('Впиши, что нужно сделать', 'error')
    const payload = { title: title.trim(), clientId, deadline, status, priority, notes }
    if (task) {
      await updateTask(task.id, payload)
      toast('Задача обновлена')
    } else {
      await createTask(payload)
      toast('Задача добавлена')
    }
    onClose()
  }

  const remove = async () => {
    if (!task) return
    await deleteTask(task.id)
    toast('Задача удалена')
    onClose()
  }

  const quickDeadlines: Array<[string, string | null]> = [
    ['Сегодня', today()],
    ['Завтра', addDays(today(), 1)],
    ['+3 дня', addDays(today(), 3)],
    ['+неделя', addDays(today(), 7)],
    ['Без срока', null],
  ]

  return (
    <>
      <Sheet
        open={open}
        onClose={onClose}
        title={task ? 'Задача' : 'Новая задача'}
        footer={
          <div className="flex gap-3">
            {task && (
              <Button variant="danger" size="lg" onClick={() => setConfirm(true)} aria-label="Удалить">
                <Trash2 size={18} />
              </Button>
            )}
            <Button full size="lg" onClick={save}>
              Сохранить
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Field label="Что сделать">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Коротко и понятно" />
          </Field>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Срок</span>
            <div className="flex flex-wrap gap-2">
              {quickDeadlines.map(([label, value]) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => setDeadline(value)}
                  className={cn(
                    'tap rounded-btn border px-3.5 py-2.5 text-body font-medium transition-colors duration-150 ease-out',
                    deadline === value
                      ? 'border-accent bg-accent/10 text-accent dark:bg-accent/15'
                      : 'border-line bg-surface text-muted hover:text-ink',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <Input
              type="date"
              value={deadline ?? ''}
              onChange={(e) => setDeadline(e.target.value || null)}
              className="mt-2"
            />
          </div>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Статус</span>
            <Choice
              options={TASK_STATUSES.map((s) => ({ value: s, label: TASK_STATUS_LABEL[s] }))}
              value={status}
              onChange={setStatus}
            />
          </div>

          <div>
            <span className="mb-1.5 block text-caption font-medium text-muted">Приоритет</span>
            <Choice
              options={PRIORITIES.map((p) => ({ value: p, label: PRIORITY_LABEL[p] }))}
              value={priority}
              onChange={setPriority}
            />
          </div>

          {clients.length > 0 && (
            <div>
              <span className="mb-1.5 block text-caption font-medium text-muted">Клиент</span>
              <Choice
                options={clients.map((c) => ({ value: c.id, label: c.name }))}
                value={clientId}
                onChange={(id) => setClientId(id === clientId ? null : id)}
              />
            </div>
          )}

          <Field label="Заметки">
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Детали" />
          </Field>
        </div>
      </Sheet>

      <ConfirmSheet
        open={confirm}
        onClose={() => setConfirm(false)}
        onConfirm={remove}
        title="Удалить задачу?"
      />
    </>
  )
}
