'use client'

import { useEffect, useRef } from 'react'

type Props = {
  value: string
  onChange: (value: string) => void
  onSave?: () => void
  saving?: boolean
  hasChanges?: boolean
  label?: string
  placeholder?: string
  className?: string
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function renderEditableMarkup(value: string): string {
  const escaped = escapeHtml(value)
  const withBold = escaped.replace(/\*\*([\s\S]+?)\*\*/g, '<strong data-note-format="bold">$1</strong>')
  const withHighlight = withBold.replace(
    /==([\s\S]+?)==/g,
    '<mark data-note-format="highlight" style="background:#fef08a;padding:0 2px;border-radius:2px;">$1</mark>'
  )
  return withHighlight.replace(/\n/g, '<br/>')
}

function serializeNode(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.nodeValue || ''
  if (node.nodeType !== Node.ELEMENT_NODE) return ''

  const element = node as HTMLElement
  const tag = element.tagName.toLowerCase()
  if (tag === 'br') return '\n'

  const children = Array.from(element.childNodes).map(serializeNode).join('')
  const isBold = tag === 'strong' || tag === 'b' || element.dataset.noteFormat === 'bold'
  const isHighlighted =
    tag === 'mark' ||
    element.dataset.noteFormat === 'highlight' ||
    Boolean(element.style.backgroundColor)

  let formatted = children
  if (isBold) formatted = `**${formatted}**`
  if (isHighlighted) formatted = `==${formatted}==`
  if (tag === 'div' || tag === 'p') formatted += '\n'
  return formatted
}

function serializeEditor(editor: HTMLElement): string {
  const serialized = Array.from(editor.childNodes).map(serializeNode).join('')
  return serialized.replace(/\n$/, '')
}

export function RichTextEditor({
  value,
  onChange,
  onSave,
  saving = false,
  hasChanges = false,
  label = 'Editor',
  placeholder = '入力してください',
  className = '',
}: Props) {
  const editorRef = useRef<HTMLDivElement | null>(null)
  const lastExternalValue = useRef(value)
  const initialHtml = useRef(renderEditableMarkup(value)).current

  useEffect(() => {
    const editor = editorRef.current
    if (!editor || value === lastExternalValue.current) return
    if (document.activeElement === editor) return
    editor.innerHTML = renderEditableMarkup(value)
    lastExternalValue.current = value
  }, [value])

  const handleInput = () => {
    const editor = editorRef.current
    if (!editor) return
    const next = serializeEditor(editor)
    lastExternalValue.current = next
    onChange(next)
  }

  const applyFormat = (command: 'bold' | 'highlight') => {
    const editor = editorRef.current
    const selection = window.getSelection()
    if (!editor || !selection || selection.rangeCount === 0 || selection.isCollapsed) return

    const range = selection.getRangeAt(0)
    if (!editor.contains(range.commonAncestorContainer)) return

    if (command === 'highlight') {
      // Use a stable element instead of browser-specific hiliteColor markup.
      const mark = document.createElement('mark')
      mark.dataset.noteFormat = 'highlight'
      mark.style.backgroundColor = '#fef08a'
      mark.style.padding = '0 2px'
      mark.style.borderRadius = '2px'
      mark.appendChild(range.extractContents())
      range.insertNode(mark)

      const nextRange = document.createRange()
      nextRange.selectNodeContents(mark)
      selection.removeAllRanges()
      selection.addRange(nextRange)
    } else {
      document.execCommand('bold', false)
    }
    handleInput()
    editor.focus()
  }

  const handlePaste = (event: React.ClipboardEvent<HTMLDivElement>) => {
    event.preventDefault()
    const text = event.clipboardData.getData('text/plain')
    document.execCommand('insertText', false, text)
    handleInput()
  }

  return (
    <div className={`border border-gray-200 rounded-lg bg-white ${className}`}>
      <div className="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-gray-50 px-3 py-2">
        <span className="text-xs font-medium text-gray-600 mr-1">{label}</span>
        <button
          type="button"
          className="btn-secondary px-2 py-1 text-xs"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => applyFormat('bold')}
          title="選択範囲を太字にする"
        >
          太字
        </button>
        <button
          type="button"
          className="btn-secondary px-2 py-1 text-xs"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => applyFormat('highlight')}
          title="選択範囲を黄色ハイライトにする"
        >
          黄色ハイライト
        </button>
        {onSave && (
          <button
            type="button"
            className="btn-primary px-3 py-1 text-xs ml-auto"
            onClick={onSave}
            disabled={saving || !hasChanges}
          >
            {saving ? '保存中...' : '保存'}
          </button>
        )}
      </div>
      <div
        ref={editorRef}
        contentEditable
        suppressContentEditableWarning
        role="textbox"
        aria-label={label}
        aria-multiline="true"
        data-placeholder={placeholder}
        className="min-h-[160px] max-h-[560px] overflow-y-auto p-4 text-sm text-gray-800 whitespace-pre-wrap focus:outline-none focus:ring-2 focus:ring-primary-500"
        dangerouslySetInnerHTML={{ __html: initialHtml }}
        onInput={handleInput}
        onPaste={handlePaste}
      />
    </div>
  )
}
