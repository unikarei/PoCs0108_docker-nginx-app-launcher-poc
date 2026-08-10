'use client'

import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { AppSettings } from '@/lib/settings'
import { InlineEditTitle } from '../InlineEditTitle'

type Props = {
  jobId: string | null
  settings: AppSettings
  onSelectJob: (jobId: string) => void
}

type StatusData = {
  job_id: string
  status: string
  stage?: string
  stage_detail?: any
  progress: number
  error_message?: string
  youtube_url: string
  user_title?: string
  tags?: string
  language: string
  model: string
  created_at: string
  updated_at: string
}

type QaResult = {
  question: string
  answer: string
  qa_model?: string
  created_at: string
}

type JobResult = {
  job_id: string
  status: string
  model?: string
  audio_file?: {
    title?: string
    duration_seconds?: number
  }
  transcript?: {
    text: string
    created_at: string
  }
  corrected_transcript?: {
    corrected_text: string
    created_at: string
  }
  qa_results?: QaResult[]
  error_message?: string
}

type SubTab = 'transcript' | 'proofread' | 'qa' | 'note'

function downloadText(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

function renderNoteMarkup(raw: string): string {
  // Escape first to prevent HTML/script injection, then apply lightweight markup.
  const escaped = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  const withBold = escaped.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>')
  const withHighlight = withBold.replace(
    /==([\s\S]+?)==/g,
    '<mark style="background:#fef08a;padding:0 2px;border-radius:2px;">$1</mark>'
  )

  return withHighlight.replace(/\n/g, '<br/>')
}

export default function ResultsTab({ jobId, settings, onSelectJob }: Props) {
  const [active, setActive] = useState<SubTab>('transcript')
  const [status, setStatus] = useState<StatusData | null>(null)
  const [result, setResult] = useState<JobResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const [qaQuestion, setQaQuestion] = useState('')
  const [qaModel, setQaModel] = useState(settings.qaModel)
  const [isQaSubmitting, setIsQaSubmitting] = useState(false)
  const [isProofreading, setIsProofreading] = useState(false)
  const [proofreadModel, setProofreadModel] = useState(settings.proofreadModel)

  const [noteContent, setNoteContent] = useState('')
  const [originalNote, setOriginalNote] = useState('')
  const [isNoteSaving, setIsNoteSaving] = useState(false)
  const [noteLastSaved, setNoteLastSaved] = useState<string | null>(null)
  const noteTextareaRef = useRef<HTMLTextAreaElement | null>(null)

  const [reRunModel, setReRunModel] = useState(settings.transcriptionModel)

  useEffect(() => {
    setQaModel(settings.qaModel)
    setProofreadModel(settings.proofreadModel)
    setReRunModel(settings.transcriptionModel)
  }, [settings.qaModel, settings.proofreadModel, settings.transcriptionModel])

  const fetchAll = async () => {
    if (!jobId) return
    setIsLoading(true)
    setError(null)
    try {
      const [s, r, n] = await Promise.all([
        apiClient.getJobStatus(jobId),
        apiClient.getJobResult(jobId),
        apiClient.getNote(jobId).catch(() => ({ content: null, updated_at: null }))
      ])
      setStatus(s)
      setResult(r)
      setNoteContent(n.content || '')
      setOriginalNote(n.content || '')
      setNoteLastSaved(n.updated_at || null)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '結果の取得に失敗しました')
      setStatus(null)
      setResult(null)
    } finally {
      setIsLoading(false)
    }
  }

  const pollForProofreadResult = async (timeoutMs: number = 60000): Promise<boolean> => {
    if (!jobId) return false
    const startedAt = Date.now()
    const currentJobId = jobId

    while (Date.now() - startedAt < timeoutMs) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      if (jobId !== currentJobId) return false

      try {
        const r = await apiClient.getJobResult(currentJobId)
        setResult(r)
        if (r?.corrected_transcript?.corrected_text) {
          try {
            const s = await apiClient.getJobStatus(currentJobId)
            setStatus(s)
          } catch {
            // ignore status refresh failures
          }
          return true
        }
      } catch {
        // ignore transient failures and keep polling
      }
    }

    return false
  }

  useEffect(() => {
    setActive('transcript')
    setQaQuestion('')
    setNoteContent('')
    setOriginalNote('')
    setNoteLastSaved(null)
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId])

  const displayTitle = useMemo(() => {
    const userTitle = status?.user_title
    const audioTitle = result?.audio_file?.title
    return userTitle || audioTitle || '—'
  }, [status?.user_title, result?.audio_file?.title])

  // タイトル更新ハンドラー
  const handleTitleUpdate = useCallback(async (newTitle: string) => {
    if (!jobId) return
    try {
      await apiClient.updateJobTitle(jobId, newTitle)
      // ローカルstateを更新
      setStatus((prev) => prev ? { ...prev, user_title: newTitle } : prev)
    } catch (err: any) {
      throw new Error(err?.response?.data?.detail || 'タイトルの更新に失敗しました')
    }
  }, [jobId])

  const transcriptText = result?.transcript?.text || ''
  const proofreadText = result?.corrected_transcript?.corrected_text || ''

  const exportText = () => {
    if (!jobId) return
    const text = proofreadText || transcriptText
    downloadText(`transcript_${jobId.slice(0, 8)}.txt`, text)
  }

  const exportJson = () => {
    if (!jobId) return
    downloadJson(`result_${jobId.slice(0, 8)}.json`, { status, result })
  }

  const saveNote = async () => {
    if (!jobId) return
    setIsNoteSaving(true)
    try {
      const res = await apiClient.updateNote(jobId, noteContent)
      setOriginalNote(noteContent)
      setNoteLastSaved(res.updated_at || new Date().toISOString())
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Noteの保存に失敗しました')
    } finally {
      setIsNoteSaving(false)
    }
  }

  const noteHasChanges = noteContent !== originalNote
  const renderedNoteHtml = useMemo(() => renderNoteMarkup(noteContent), [noteContent])

  const wrapNoteSelection = (prefix: string, suffix: string = prefix) => {
    const el = noteTextareaRef.current
    if (!el) return

    const start = el.selectionStart ?? 0
    const end = el.selectionEnd ?? 0
    const selected = noteContent.slice(start, end)
    const before = noteContent.slice(0, start)
    const after = noteContent.slice(end)
    const next = `${before}${prefix}${selected}${suffix}${after}`
    setNoteContent(next)

    const cursorStart = start + prefix.length
    const cursorEnd = cursorStart + selected.length
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(cursorStart, cursorEnd)
    })
  }

  const triggerProofread = async () => {
    if (!jobId) return
    setIsProofreading(true)
    try {
      await apiClient.requestProofread(jobId, proofreadModel)
      // Proofreadは非同期でDB反映に時間がかかるので、反映されるまでポーリング
      const ok = await pollForProofreadResult()
      if (!ok) {
        // timeout: fall back to a full refresh (may still be pending)
        fetchAll()
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Proofreadのリクエストに失敗しました')
    } finally {
      setIsProofreading(false)
    }
  }

  const triggerQa = async () => {
    if (!jobId || !qaQuestion.trim()) return
    setIsQaSubmitting(true)
    try {
      const question = qaQuestion.trim()
      const previousLength = result?.qa_results?.length || 0
      await apiClient.askQuestion(jobId, question, qaModel)
      setQaQuestion('')

      const startedAt = Date.now()
      const currentJobId = jobId
      const timeoutMs = 60000
      let ok = false

      while (Date.now() - startedAt < timeoutMs) {
        await new Promise((resolve) => setTimeout(resolve, 1000))
        if (jobId !== currentJobId) return

        try {
          const r = await apiClient.getJobResult(currentJobId)
          setResult(r)
          const next = r?.qa_results || []
          const hasNew = next.length > previousLength
          const hasMatchingQuestion = next.some((x: any) => x.question === question)

          if (hasNew || hasMatchingQuestion) {
            ok = true
            try {
              const s = await apiClient.getJobStatus(currentJobId)
              setStatus(s)
            } catch {
              // ignore status refresh failures
            }
            return
          }
        } catch {
          // ignore transient failures
        }
      }

      if (!ok) {
        // timeout: fall back to a full refresh (may still be pending)
        fetchAll()
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'QAのリクエストに失敗しました')
    } finally {
      setIsQaSubmitting(false)
    }
  }

  const reRun = async () => {
    if (!status?.youtube_url) return
    try {
      const res = await apiClient.createJob(status.youtube_url, status.language, reRunModel)
      onSelectJob(res.job_id)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Re-runに失敗しました')
    }
  }

  if (!jobId) {
    return (
      <div className="card">
        <h2 className="text-xl font-semibold mb-2">Results</h2>
        <div className="text-sm text-gray-500">LibraryまたはBatchから1件選択してください。</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <InlineEditTitle
              value={displayTitle}
              onSave={handleTitleUpdate}
              className="text-xl font-semibold"
            />
            <div className="text-sm text-gray-600 truncate">
              {status?.youtube_url ? (
                <a href={status.youtube_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">
                  {status.youtube_url}
                </a>
              ) : (
                '—'
              )}
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {status?.created_at ? `作成: ${status.created_at}` : ''}
              {status?.tags ? ` / tags: ${status.tags}` : ''}
              {result?.audio_file?.duration_seconds ? ` / 長さ: ${Math.floor(result.audio_file.duration_seconds / 60)}分${result.audio_file.duration_seconds % 60}秒` : ''}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {settings.autoSaveToDb ? (
              <span className="text-xs bg-gray-100 border border-gray-200 rounded-full px-3 py-1 text-gray-700">
                Saved
              </span>
            ) : (
              <button className="btn-primary" disabled>
                Save to DB
              </button>
            )}

            <button className="btn-primary" onClick={exportText} disabled={!transcriptText && !proofreadText}>
              Export txt
            </button>
            <button className="btn-primary" onClick={exportJson}>
              Export json
            </button>

            <div className="flex items-center gap-2">
              <select
                value={reRunModel}
                onChange={(e) => setReRunModel(e.target.value as any)}
                className="input-field"
              >
                <option value="gpt-4o-mini-transcribe">gpt-4o-mini-transcribe</option>
                <option value="gpt-4o-transcribe">gpt-4o-transcribe</option>
              </select>
              <button className="btn-primary" onClick={reRun}>
                Re-run
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="flex items-center gap-2 mb-4">
          <button
            className={`px-4 py-2 rounded ${active === 'transcript' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('transcript')}
          >
            Transcript
          </button>
          <button
            className={`px-4 py-2 rounded ${active === 'proofread' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('proofread')}
          >
            Proofread
          </button>
          <button
            className={`px-4 py-2 rounded ${active === 'qa' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('qa')}
          >
            QA
          </button>
          <button
            className={`px-4 py-2 rounded ${active === 'note' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('note')}
          >
            Note
          </button>

          <button className="ml-auto btn-primary" onClick={fetchAll} disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">{error}</div>}

        {!error && active === 'transcript' && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            {transcriptText ? (
              <p className="whitespace-pre-wrap text-sm text-gray-800">{transcriptText}</p>
            ) : (
              <div className="text-sm text-gray-500">（未完了）</div>
            )}
          </div>
        )}

        {!error && active === 'proofread' && (
          <div className="space-y-3">
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-700">モデル:</label>
                <select
                  value={proofreadModel}
                  onChange={(e) => setProofreadModel(e.target.value as any)}
                  className="input-field"
                >
                  <option value="gpt-4o-mini">gpt-4o-mini</option>
                  <option value="gpt-4o">gpt-4o</option>
                </select>
              </div>
              <button className="btn-primary" onClick={triggerProofread} disabled={isProofreading}>
                {isProofreading ? 'Proofread中...' : 'Proofreadを実行'}
              </button>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              {proofreadText ? (
                <p className="whitespace-pre-wrap text-sm text-gray-800">{proofreadText}</p>
              ) : (
                <div className="text-sm text-gray-500">（未作成）</div>
              )}
            </div>
          </div>
        )}

        {!error && active === 'qa' && (
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <div className="flex-1 min-w-0">
                <input
                  value={qaQuestion}
                  onChange={(e) => setQaQuestion(e.target.value)}
                  className="input-field w-full"
                  placeholder="質問を入力"
                />
              </div>
              <select
                value={qaModel}
                onChange={(e) => setQaModel(e.target.value as any)}
                className="input-field w-full md:w-56 md:flex-none"
              >
                <option value="gpt-4o-mini">gpt-4o-mini</option>
                <option value="gpt-4o">gpt-4o</option>
              </select>
              <button
                className="btn-primary whitespace-nowrap md:flex-none"
                onClick={triggerQa}
                disabled={isQaSubmitting || !qaQuestion.trim()}
              >
                {isQaSubmitting ? '送信中...' : '送信'}
              </button>
            </div>

            <div className="space-y-2">
              {(result?.qa_results || []).map((qa, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-3">
                  <div className="text-sm font-medium text-gray-900">Q: {qa.question}</div>
                  <div className="text-sm text-gray-700 mt-2 whitespace-pre-wrap">{qa.answer}</div>
                  <div className="text-xs text-gray-500 mt-2">{qa.created_at}</div>
                </div>
              ))}
              {!result?.qa_results?.length && <div className="text-sm text-gray-500">（履歴なし）</div>}
            </div>
          </div>
        )}

        {!error && active === 'note' && (
          <div className="space-y-3">
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <button
                type="button"
                className="btn-primary"
                onClick={() => wrapNoteSelection('**')}
                title="選択範囲を太字にする"
              >
                太字
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => wrapNoteSelection('==')}
                title="選択範囲を黄色ハイライトにする"
              >
                黄色ハイライト
              </button>
              <button
                className="btn-primary"
                onClick={saveNote}
                disabled={isNoteSaving || !noteHasChanges}
              >
                {isNoteSaving ? '保存中...' : '保存'}
              </button>
              {noteLastSaved && (
                <span className="text-xs text-gray-500">
                  最終保存: {new Date(noteLastSaved).toLocaleString()}
                </span>
              )}
              {noteHasChanges && (
                <span className="text-xs text-amber-600">
                  未保存の変更があります
                </span>
              )}
            </div>

            <textarea
              ref={noteTextareaRef}
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              className="w-full h-64 p-4 border border-gray-200 rounded-lg text-sm text-gray-800 resize-y focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder={"メモを入力...\n太字: **文字**\n黄色ハイライト: ==文字=="}
            />

            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="text-xs text-gray-500 mb-2">プレビュー</div>
              <div
                className="text-sm text-gray-800 whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ __html: renderedNoteHtml || '（空）' }}
              />
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
