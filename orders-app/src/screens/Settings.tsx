import {
  Bell,
  Download,
  Moon,
  Palette,
  Pencil,
  Plus,
  Smartphone,
  Sun,
  Tags,
  Trash2,
  Upload,
  Monitor,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Header } from '../components/Header'
import { SourceEditorSheet } from '../components/SourceEditorSheet'
import { useAppData } from '../hooks/useData'
import { useInstallPrompt } from '../hooks/useInstallPrompt'
import { useTheme } from '../hooks/useTheme'
import { seedIfEmpty } from '../db/db'
import {
  DEFAULT_NOTIFICATIONS,
  SETTING_KEYS,
  countOrdersBySource,
  deleteSource,
  getSetting,
  setSetting,
  wipeAll,
} from '../db/repo'
import type { NotificationSettings, Source, ThemeMode } from '../db/types'
import { exportCsv, exportJson, importJson } from '../lib/backup'
import {
  notificationsSupported,
  permission,
  requestPermission,
  sendTestNotification,
} from '../lib/notifications'
import { cn, percent, plural } from '../lib/utils'
import { Button } from '../ui/Button'
import { Card, SectionTitle } from '../ui/Card'
import { Choice } from '../ui/Choice'
import { ConfirmSheet, Sheet } from '../ui/Sheet'
import { useToast } from '../ui/Toast'

export function Settings({ params }: { params: Record<string, string> }) {
  const toast = useToast()
  const { sources, orders } = useAppData()
  const { mode, setMode } = useTheme()
  const { canInstall, installed, install } = useInstallPrompt()

  const [editingSource, setEditingSource] = useState<Source | null>(null)
  const [creatingSource, setCreatingSource] = useState(false)
  const [deletingSource, setDeletingSource] = useState<Source | null>(null)
  const [confirmWipe, setConfirmWipe] = useState(false)
  const [notifications, setNotifications] = useState<NotificationSettings>(DEFAULT_NOTIFICATIONS)
  const fileRef = useRef<HTMLInputElement>(null)
  const sourcesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getSetting<NotificationSettings>(SETTING_KEYS.notifications, DEFAULT_NOTIFICATIONS).then(
      setNotifications,
    )
  }, [])

  // Переход с дашборда «Настроить источники» — сразу прокручиваем к ним
  useEffect(() => {
    if (params.section === 'sources') {
      sourcesRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [params.section])

  const usage = useMemo(() => {
    const m = new Map<string, number>()
    for (const o of orders ?? []) if (o.sourceId) m.set(o.sourceId, (m.get(o.sourceId) ?? 0) + 1)
    return m
  }, [orders])

  const saveNotifications = async (next: NotificationSettings) => {
    setNotifications(next)
    await setSetting(SETTING_KEYS.notifications, next)
  }

  const toggleNotifications = async () => {
    if (notifications.enabled) {
      await saveNotifications({ ...notifications, enabled: false })
      toast('Уведомления выключены')
      return
    }
    if (!notificationsSupported()) {
      toast('Браузер не умеет уведомления — приложение работает и без них', 'error')
      return
    }
    const result = await requestPermission()
    if (result !== 'granted') {
      toast('Разрешение не выдано. Включить можно в настройках браузера', 'error')
      return
    }
    await saveNotifications({ ...notifications, enabled: true })
    await sendTestNotification()
    toast('Уведомления включены')
  }

  const onImportFile = async (file: File) => {
    try {
      const text = await file.text()
      const res = await importJson(text)
      toast(`Восстановлено: ${res.orders} заказов, ${res.clients} клиентов`)
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Не получилось прочитать файл', 'error')
    }
  }

  const wipe = async () => {
    await wipeAll()
    await seedIfEmpty()
    toast('Все данные удалены')
  }

  const themeOptions: Array<{ value: ThemeMode; label: string; icon: typeof Sun }> = [
    { value: 'light', label: 'Светлая', icon: Sun },
    { value: 'dark', label: 'Тёмная', icon: Moon },
    { value: 'system', label: 'Как в системе', icon: Monitor },
  ]

  return (
    <div className="pb-2">
      <Header title="Настройки" />

      {/* ── Установка на телефон ────────────────────────────────── */}
      {!installed && (
        <section className="px-4">
          <Card className="flex items-center gap-4 p-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-btn bg-accent/10 text-accent dark:bg-accent/15">
              <Smartphone size={20} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-body font-medium">На главный экран</div>
              <p className="mt-0.5 text-caption text-muted">
                {canInstall
                  ? 'Откроется как обычное приложение, без адресной строки'
                  : 'В меню браузера выбери «Установить приложение» или «На главный экран»'}
              </p>
            </div>
            {canInstall && (
              <Button size="sm" onClick={install}>
                Установить
              </Button>
            )}
          </Card>
        </section>
      )}

      {/* ── Источники ───────────────────────────────────────────── */}
      <section ref={sourcesRef} className="mt-6 px-4 scroll-mt-4">
        <SectionTitle
          action={
            <button
              onClick={() => setCreatingSource(true)}
              className="flex items-center gap-1 text-caption font-medium text-accent"
            >
              <Plus size={15} /> Добавить
            </button>
          }
        >
          Источники заказов
        </SectionTitle>
        <Card className="divide-y divide-line">
          {(sources ?? []).map((s) => (
            <div key={s.id} className="flex items-center gap-3 px-4 py-3">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-body font-medium">{s.name}</div>
                <div className="text-caption text-muted">
                  {s.commissionRate > 0 ? `Комиссия ${percent(s.commissionRate)}` : 'Без комиссии'}
                  {usage.get(s.id) ? ` · ${plural(usage.get(s.id)!, 'заказ', 'заказа', 'заказов')}` : ''}
                </div>
              </div>
              <button
                onClick={() => setEditingSource(s)}
                aria-label="Изменить"
                className="tap flex items-center justify-center rounded-btn text-muted transition-colors duration-150 ease-out hover:text-ink"
              >
                <Pencil size={17} />
              </button>
              <button
                onClick={() => setDeletingSource(s)}
                aria-label="Удалить"
                className="tap flex items-center justify-center rounded-btn text-muted transition-colors duration-150 ease-out hover:text-danger"
              >
                <Trash2 size={17} />
              </button>
            </div>
          ))}
          {(sources ?? []).length === 0 && (
            <div className="flex items-center gap-3 px-4 py-6 text-body text-muted">
              <Tags size={18} /> Справочник пуст — добавь первый источник
            </div>
          )}
        </Card>
        <p className="mt-2 px-1 text-caption text-muted">
          Процент комиссии сохраняется в заказе на момент создания: изменение ставки не тронет
          прошлые заказы.
        </p>
      </section>

      {/* ── Тема ────────────────────────────────────────────────── */}
      <section className="mt-6 px-4">
        <SectionTitle>Внешний вид</SectionTitle>
        <Card className="p-4">
          <div className="mb-2.5 flex items-center gap-2 text-caption font-medium text-muted">
            <Palette size={15} /> Тема
          </div>
          <Choice
            options={themeOptions.map((o) => ({ value: o.value, label: o.label }))}
            value={mode}
            onChange={setMode}
          />
        </Card>
      </section>

      {/* ── Уведомления ─────────────────────────────────────────── */}
      <section className="mt-6 px-4">
        <SectionTitle>Уведомления</SectionTitle>
        <Card className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-btn bg-surface-2 text-muted">
              <Bell size={18} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-body font-medium">Напоминания о сроках</div>
              <p className="mt-0.5 text-caption text-muted">
                Утром — что горит сегодня, что просрочено и какие «Сдан» висят дольше недели.
              </p>
            </div>
            <Switch checked={notifications.enabled} onChange={toggleNotifications} />
          </div>

          {notifications.enabled && (
            <div className="mt-4 space-y-4 border-t border-line pt-4">
              <div>
                <span className="mb-1.5 block text-caption font-medium text-muted">
                  Во сколько напоминать
                </span>
                <Choice
                  options={[7, 8, 9, 10, 11, 12].map((h) => ({
                    value: String(h),
                    label: `${h}:00`,
                  }))}
                  value={String(notifications.morningHour)}
                  onChange={(v) => saveNotifications({ ...notifications, morningHour: Number(v) })}
                />
              </div>
              <ToggleRow
                label="Сообщать о просроченном"
                checked={notifications.overdue}
                onChange={(v) => saveNotifications({ ...notifications, overdue: v })}
              />
              <ToggleRow
                label="Напоминать про «Сдан» дольше недели"
                checked={notifications.unpaid}
                onChange={(v) => saveNotifications({ ...notifications, unpaid: v })}
              />
              <Button variant="secondary" size="sm" onClick={sendTestNotification}>
                Прислать тестовое
              </Button>
            </div>
          )}

          {permission() === 'denied' && (
            <p className="mt-3 text-caption text-danger">
              Браузер запретил уведомления для сайта. Разреши их в настройках сайта в браузере.
            </p>
          )}
        </Card>
      </section>

      {/* ── Данные ──────────────────────────────────────────────── */}
      <section className="mt-6 px-4">
        <SectionTitle>Данные</SectionTitle>
        <Card className="divide-y divide-line">
          <RowButton icon={<Download size={18} />} title="Экспорт в JSON" subtitle="Полная резервная копия" onClick={exportJson} />
          <RowButton icon={<Download size={18} />} title="Экспорт заказов в CSV" subtitle="Открывается в Excel и Google Таблицах" onClick={exportCsv} />
          <RowButton
            icon={<Upload size={18} />}
            title="Импорт из JSON"
            subtitle="Заменит текущие данные копией из файла"
            onClick={() => fileRef.current?.click()}
          />
        </Card>
        <input
          ref={fileRef}
          type="file"
          accept="application/json,.json"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) void onImportFile(f)
            e.target.value = ''
          }}
        />
      </section>

      {/* ── Опасная зона ────────────────────────────────────────── */}
      <section className="mt-6 px-4">
        <Card className="p-4">
          <div className="text-body font-medium">Очистить все данные</div>
          <p className="mt-0.5 text-caption text-muted">
            Удалит заказы, клиентов, задачи и источники. Сначала сделай экспорт.
          </p>
          <Button variant="danger" className="mt-3" onClick={() => setConfirmWipe(true)}>
            Очистить
          </Button>
        </Card>
        <p className="mt-4 px-1 text-center text-caption text-muted">
          Заказы · всё хранится только на этом устройстве
        </p>
      </section>

      <SourceEditorSheet
        open={creatingSource || !!editingSource}
        source={editingSource}
        onClose={() => {
          setCreatingSource(false)
          setEditingSource(null)
        }}
      />

      <DeleteSourceSheet
        source={deletingSource}
        sources={sources ?? []}
        onClose={() => setDeletingSource(null)}
      />

      <ConfirmSheet
        open={confirmWipe}
        onClose={() => setConfirmWipe(false)}
        onConfirm={wipe}
        title="Удалить все данные?"
        text="Заказы, клиенты, задачи и источники исчезнут навсегда. Справочник источников вернётся к стандартному набору."
        confirmLabel="Да, удалить всё"
      />
    </div>
  )
}

/** Удаление источника: если он уже в заказах — спрашиваем, что с ними делать. */
function DeleteSourceSheet({
  source,
  sources,
  onClose,
}: {
  source: Source | null
  sources: Source[]
  onClose: () => void
}) {
  const toast = useToast()
  const [count, setCount] = useState(0)
  const [targetId, setTargetId] = useState<string | null>(null)

  useEffect(() => {
    if (!source) return
    setTargetId(null)
    countOrdersBySource(source.id).then(setCount)
  }, [source])

  const others = sources.filter((s) => s.id !== source?.id)

  const remove = async (mode: 'reassign' | 'clear') => {
    if (!source) return
    await deleteSource(source.id, mode, targetId ?? undefined)
    toast('Источник удалён')
    onClose()
  }

  return (
    <Sheet
      open={!!source}
      onClose={onClose}
      title={`Удалить «${source?.name ?? ''}»?`}
      subtitle={
        count > 0
          ? `Источник стоит в ${plural(count, 'заказе', 'заказах', 'заказах')} — выбери, что с ними делать`
          : 'Источник нигде не используется'
      }
      footer={
        count === 0 ? (
          <div className="flex gap-3">
            <Button variant="secondary" full onClick={onClose}>
              Отмена
            </Button>
            <Button variant="danger" full onClick={() => remove('clear')}>
              Удалить
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            <Button
              full
              size="lg"
              disabled={!targetId}
              onClick={() => remove('reassign')}
            >
              Перенести заказы и удалить
            </Button>
            <Button variant="secondary" full onClick={() => remove('clear')}>
              Оставить заказы без источника
            </Button>
          </div>
        )
      }
    >
      {count > 0 && (
        <div>
          <span className="mb-1.5 block text-caption font-medium text-muted">
            Перенести заказы на источник
          </span>
          <Choice
            options={others.map((s) => ({ value: s.id, label: s.name, color: s.color }))}
            value={targetId}
            onChange={setTargetId}
          />
          <p className="mt-3 text-caption text-muted">
            Комиссия в перенесённых заказах останется прежней — она хранится в самом заказе.
          </p>
        </div>
      )}
    </Sheet>
  )
}

function RowButton({
  icon,
  title,
  subtitle,
  onClick,
}: {
  icon: ReactNode
  title: string
  subtitle?: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors duration-150 ease-out hover:bg-surface-2"
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-btn bg-surface-2 text-muted">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body font-medium">{title}</span>
        {subtitle && <span className="mt-0.5 block text-caption text-muted">{subtitle}</span>}
      </span>
    </button>
  )
}

function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-body">{label}</span>
      <Switch checked={checked} onChange={() => onChange(!checked)} />
    </div>
  )
}

/** Переключатель. Плавный, с крупной областью нажатия. */
function Switch({ checked, onChange }: { checked: boolean; onChange: () => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="tap flex shrink-0 items-center justify-center"
    >
      <span
        className={cn(
          'flex h-7 w-12 items-center rounded-full px-0.5 transition-colors duration-200 ease-out',
          checked ? 'bg-accent' : 'bg-line',
        )}
      >
        <span
          className={cn(
            'h-6 w-6 rounded-full bg-white shadow-soft transition-transform duration-200 ease-out',
            checked ? 'translate-x-5' : 'translate-x-0',
          )}
        />
      </span>
    </button>
  )
}
