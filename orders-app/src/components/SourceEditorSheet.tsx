import { useEffect, useState } from 'react'
import { createSource, updateSource } from '../db/repo'
import type { Source } from '../db/types'
import { cn } from '../lib/utils'
import { Button } from '../ui/Button'
import { Field, Input } from '../ui/Field'
import { Sheet } from '../ui/Sheet'
import { useToast } from '../ui/Toast'

/** Палитра для источников — спокойные, различимые между собой цвета. */
export const SOURCE_COLORS = [
  '#4A6FE3',
  '#2AA3E0',
  '#12A578',
  '#0E8F6E',
  '#2FA8A0',
  '#7C6BE0',
  '#B05FA8',
  '#E9A23B',
  '#D4785C',
  '#E05A47',
  '#8E7CC3',
  '#6B7684',
]

interface Props {
  open: boolean
  onClose: () => void
  /** Если передан — редактируем, иначе создаём. */
  source?: Source | null
  /** Подставить имя (когда создаём источник прямо из формы заказа). */
  presetName?: string
  onCreated?: (source: Source) => void
}

export function SourceEditorSheet({ open, onClose, source, presetName, onCreated }: Props) {
  const toast = useToast()
  const [name, setName] = useState('')
  const [percent, setPercent] = useState('0')
  const [color, setColor] = useState(SOURCE_COLORS[0])

  useEffect(() => {
    if (!open) return
    setName(source?.name ?? presetName ?? '')
    setPercent(source ? String(Math.round(source.commissionRate * 1000) / 10) : '0')
    setColor(source?.color ?? SOURCE_COLORS[Math.floor(Math.random() * SOURCE_COLORS.length)])
  }, [open, source, presetName])

  const save = async () => {
    const trimmed = name.trim()
    if (!trimmed) {
      toast('Впиши название источника', 'error')
      return
    }
    const rate = Math.max(0, Math.min(100, Number(percent.replace(',', '.')) || 0)) / 100
    if (source) {
      await updateSource(source.id, { name: trimmed, commissionRate: rate, color })
      toast('Источник обновлён')
    } else {
      const created = await createSource({ name: trimmed, commissionRate: rate, color })
      onCreated?.(created)
      toast('Источник добавлен')
    }
    onClose()
  }

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={source ? 'Источник' : 'Новый источник'}
      subtitle={
        source
          ? 'Изменение процента не тронет уже созданные заказы'
          : 'Например, «Instagram-блогер» с комиссией 15 %'
      }
      footer={
        <Button full size="lg" onClick={save}>
          Сохранить
        </Button>
      }
    >
      <div className="space-y-4">
        <Field label="Название">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Например, Telegram-канал"
            autoFocus={!source}
          />
        </Field>

        <Field label="Комиссия, %" hint="Сколько площадка забирает с суммы заказа. Нет комиссии — оставь 0">
          <Input
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
            inputMode="decimal"
            placeholder="0"
          />
        </Field>

        <div>
          <span className="mb-2 block text-caption font-medium text-muted">Цвет</span>
          <div className="flex flex-wrap gap-2.5">
            {SOURCE_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                aria-label={`Цвет ${c}`}
                className={cn(
                  'h-11 w-11 rounded-btn transition-transform duration-150 ease-out',
                  color === c ? 'scale-105 ring-2 ring-accent ring-offset-2 ring-offset-surface' : '',
                )}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      </div>
    </Sheet>
  )
}
