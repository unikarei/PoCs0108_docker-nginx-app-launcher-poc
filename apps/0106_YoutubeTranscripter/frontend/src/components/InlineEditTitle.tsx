'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'

// Simple SVG icons (avoiding external dependencies)
const PencilIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
  </svg>
)

const CheckIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
)

const XIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
)

interface InlineEditTitleProps {
  value: string
  onSave: (newValue: string) => Promise<void>
  onClick?: () => void
  className?: string
  minLength?: number
  maxLength?: number
}

/**
 * インライン編集可能なタイトルコンポーネント
 * クリックで編集モードに切り替わり、Enter or チェックで保存、Escape or X で取消
 */
export function InlineEditTitle({
  value,
  onSave,
  onClick,
  className = '',
  minLength = 1,
  maxLength = 500,
}: InlineEditTitleProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(value)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // 外部からvalueが変更されたら編集値も更新
  useEffect(() => {
    if (!isEditing) {
      setEditValue(value)
    }
  }, [value, isEditing])

  // 編集モード開始時にフォーカス
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const startEditing = () => {
    setIsEditing(true)
    setEditValue(value)
    setError(null)
  }

  const cancelEditing = () => {
    setIsEditing(false)
    setEditValue(value)
    setError(null)
  }

  const validateInput = (val: string): string | null => {
    const trimmed = val.trim()
    if (trimmed.length < minLength) {
      return `タイトルは${minLength}文字以上必要です`
    }
    if (trimmed.length > maxLength) {
      return `タイトルは${maxLength}文字以下にしてください`
    }
    return null
  }

  const handleSave = async () => {
    const trimmedValue = editValue.trim()
    
    // バリデーション
    const validationError = validateInput(trimmedValue)
    if (validationError) {
      setError(validationError)
      return
    }

    // 変更がなければ閉じるだけ
    if (trimmedValue === value) {
      cancelEditing()
      return
    }

    setIsSaving(true)
    setError(null)

    try {
      await onSave(trimmedValue)
      setIsEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存に失敗しました')
    } finally {
      setIsSaving(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      cancelEditing()
    }
  }

  if (!isEditing) {
    return (
      <div className={`group flex items-center gap-2 ${className}`}>
        <span
          className={`truncate ${onClick ? 'cursor-pointer hover:text-blue-600' : ''}`}
          title={value}
          onClick={onClick}
        >
          {value}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            startEditing()
          }}
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          title="タイトルを編集"
          aria-label="タイトルを編集"
        >
          <PencilIcon />
        </button>
      </div>
    )
  }

  return (
    <div className={`flex flex-col ${className}`}>
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          type="text"
          value={editValue}
          onChange={(e) => {
            setEditValue(e.target.value)
            setError(null)
          }}
          onKeyDown={handleKeyDown}
          disabled={isSaving}
          className={`flex-1 px-2 py-1 border rounded text-sm
            ${error ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'}
            bg-white dark:bg-gray-800 
            focus:outline-none focus:ring-2 focus:ring-blue-500
            disabled:opacity-50`}
          maxLength={maxLength}
          onClick={(e) => e.stopPropagation()}
        />
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleSave()
          }}
          disabled={isSaving}
          className="p-1 hover:bg-green-100 dark:hover:bg-green-900 rounded text-green-600 disabled:opacity-50"
          title="保存"
          aria-label="保存"
        >
          <CheckIcon />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            cancelEditing()
          }}
          disabled={isSaving}
          className="p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded text-red-600 disabled:opacity-50"
          title="キャンセル"
          aria-label="キャンセル"
        >
          <XIcon />
        </button>
      </div>
      {error && (
        <span className="text-xs text-red-500 mt-1">{error}</span>
      )}
      {isSaving && (
        <span className="text-xs text-gray-500 mt-1">保存中...</span>
      )}
    </div>
  )
}
