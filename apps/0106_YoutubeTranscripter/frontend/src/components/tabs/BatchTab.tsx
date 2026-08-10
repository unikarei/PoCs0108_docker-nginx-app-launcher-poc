'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { apiClient } from '@/lib/api'
import { AppSettings } from '@/lib/settings'

type BatchInputMode = 'url_list' | 'csv' | 'expand'

type QueueItem = {
  key: string
  youtubeUrl: string
  userTitle?: string
  tags?: string
  jobId?: string
  status?: string
  progress?: number
  error?: string
}

type Props = {
  settings: AppSettings
  onSelectJob: (jobId: string) => void
}

const TERMINAL_STATUSES = ['completed', 'failed', 'canceled']

function isTerminalStatus(status?: string): boolean {
  return !!status && TERMINAL_STATUSES.includes(status)
}

const isYoutubeUrl = (url: string) => /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i.test(url)

function normalizeTags(raw?: string): string | undefined {
  if (!raw) return undefined
  const cleaned = raw
    .split(/[;]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .join(';')
  return cleaned || undefined
}

function parseUrlList(text: string): Array<{ youtubeUrl: string }> {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .filter(isYoutubeUrl)
    .map((youtubeUrl) => ({ youtubeUrl }))
}

function parseCsv(text: string): Array<{ youtubeUrl: string; userTitle?: string; tags?: string }> {
  // Minimal CSV parser: url,title,tags (no quoted commas)
  const rows = text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)

  const parsed: Array<{ youtubeUrl: string; userTitle?: string; tags?: string }> = []
  for (const row of rows) {
    const cols = row.split(',').map((c) => c.trim())
    const youtubeUrl = cols[0]
    if (!youtubeUrl || !isYoutubeUrl(youtubeUrl)) continue
    const userTitle = cols[1] || undefined
    const tags = normalizeTags((cols[2] || '').replace(/,/g, ';'))
    parsed.push({ youtubeUrl, userTitle, tags })
  }
  return parsed
}

export default function BatchTab({ settings, onSelectJob }: Props) {
  const [mode, setMode] = useState<BatchInputMode>('url_list')
  const [urlListText, setUrlListText] = useState('')
  const [csvText, setCsvText] = useState('')
  const [expandUrl, setExpandUrl] = useState('')
  const [expandItems, setExpandItems] = useState<Array<{ youtube_url: string; title?: string }>>([])
  const [isExpanding, setIsExpanding] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [preview, setPreview] = useState<any | null>(null)
  const [cancelingKeys, setCancelingKeys] = useState<string[]>([])
  const canceledKeysRef = useRef<Set<string>>(new Set())

  const inputItems = useMemo(() => {
    if (mode === 'url_list') return parseUrlList(urlListText)
    if (mode === 'csv') return parseCsv(csvText)
    return expandItems.map((it) => ({ youtubeUrl: it.youtube_url, userTitle: it.title }))
  }, [mode, urlListText, csvText, expandItems])

  const isCanceling = (key: string) => cancelingKeys.includes(key)

  const beginCanceling = (key: string) => {
    setCancelingKeys((prev) => (prev.includes(key) ? prev : [...prev, key]))
  }

  const endCanceling = (key: string) => {
    setCancelingKeys((prev) => prev.filter((value) => value !== key))
  }

  useEffect(() => {
    const timer = setInterval(async () => {
      const itemsToPoll = queue.filter((q) => q.jobId && q.status && !isTerminalStatus(q.status))
      if (itemsToPoll.length === 0) return

      const updates = await Promise.all(
        itemsToPoll.map(async (item) => {
          try {
            const status = await apiClient.getJobStatus(item.jobId!)
            return { key: item.key, status: status.status, progress: status.progress, error: status.error_message }
          } catch {
            return { key: item.key }
          }
        })
      )

      setQueue((prev) =>
        prev.map((item) => {
          const u = updates.find((x) => x.key === item.key)
          if (!u) return item
          return {
            ...item,
            status: u.status ?? item.status,
            progress: u.progress ?? item.progress,
            error: u.error ?? item.error,
          }
        })
      )
    }, 3000)

    return () => clearInterval(timer)
  }, [queue])

  const cancelQueueItem = async (item: QueueItem) => {
    if (isTerminalStatus(item.status) || isCanceling(item.key)) return

    if (!item.jobId) {
      canceledKeysRef.current.add(item.key)
      setQueue((prev) =>
        prev.map((q) =>
          q.key === item.key
            ? { ...q, status: 'canceled', error: '投入を取り消しました' }
            : q
        )
      )
      if (selectedKey === item.key) {
        setPreview(null)
      }
      return
    }

    beginCanceling(item.key)
    try {
      const res = await apiClient.cancelJob(item.jobId)
      canceledKeysRef.current.add(item.key)
      setQueue((prev) =>
        prev.map((q) =>
          q.key === item.key
            ? { ...q, status: res.status, error: res.message }
            : q
        )
      )
      if (selectedKey === item.key) {
        setPreview(null)
      }
    } catch (err: any) {
      canceledKeysRef.current.delete(item.key)
      alert(err?.response?.data?.detail || '取消に失敗しました')
    } finally {
      endCanceling(item.key)
    }
  }

  const handleExpand = async () => {
    if (!expandUrl.trim()) return
    setIsExpanding(true)
    try {
      const data = await apiClient.expandUrl(expandUrl.trim())
      setExpandItems(data.items || [])
    } catch (err: any) {
      alert(err?.response?.data?.detail || '展開に失敗しました')
    } finally {
      setIsExpanding(false)
    }
  }

  const handleRun = async () => {
    if (inputItems.length === 0) return
    setIsRunning(true)

    try {
      // Pre-create queue rows
      const initialQueue: QueueItem[] = inputItems.map((it, idx) => {
        const youtubeUrl = (it as any).youtubeUrl || (it as any).youtube_url
        return {
          key: `${Date.now()}-${idx}`,
          youtubeUrl,
          userTitle: (it as any).userTitle,
          tags: normalizeTags((it as any).tags),
          status: 'pending',
          progress: 0,
        }
      })
      setQueue((prev) => [...initialQueue, ...prev])
      setSelectedKey(initialQueue[0]?.key || null)

      for (const item of initialQueue) {
        if (canceledKeysRef.current.has(item.key)) {
          continue
        }

        try {
          const res = await apiClient.createJob(item.youtubeUrl, settings.language, settings.transcriptionModel, {
            user_title: item.userTitle,
            tags: item.tags,
          })
          const jobId = res.job_id as string

          if (canceledKeysRef.current.has(item.key)) {
            setQueue((prev) => prev.map((q) => (q.key === item.key ? { ...q, jobId } : q)))
            try {
              const cancelRes = await apiClient.cancelJob(jobId)
              setQueue((prev) =>
                prev.map((q) =>
                  q.key === item.key
                    ? { ...q, jobId, status: cancelRes.status, error: cancelRes.message }
                    : q
                )
              )
            } catch (err: any) {
              setQueue((prev) =>
                prev.map((q) =>
                  q.key === item.key
                    ? { ...q, jobId, status: 'failed', error: err?.response?.data?.detail || '取消に失敗しました' }
                    : q
                )
              )
            }
            continue
          }

          setQueue((prev) => prev.map((q) => (q.key === item.key ? { ...q, jobId } : q)))
        } catch (err: any) {
          setQueue((prev) =>
            prev.map((q) =>
              q.key === item.key
                ? { ...q, status: 'failed', error: err?.response?.data?.detail || '投入に失敗しました' }
                : q
            )
          )
        }
      }
    } finally {
      setIsRunning(false)
    }
  }

  const selectRow = async (item: QueueItem) => {
    setSelectedKey(item.key)
    if (!item.jobId) {
      setPreview(null)
      return
    }

    try {
      const data = await apiClient.getJobResult(item.jobId)
      setPreview(data)
    } catch {
      setPreview(null)
    }
  }

  const selected = queue.find((q) => q.key === selectedKey) || null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Input */}
      <section className="card">
        <h2 className="text-xl font-semibold mb-4">Batch Input</h2>

        <div className="space-y-4">
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700">入力方式</div>
            <div className="flex flex-wrap gap-4 text-sm text-gray-700">
              <label className="flex items-center space-x-2">
                <input
                  type="radio"
                  name="batchMode"
                  checked={mode === 'url_list'}
                  onChange={() => setMode('url_list')}
                />
                <span>URLリスト</span>
              </label>
              <label className="flex items-center space-x-2">
                <input type="radio" name="batchMode" checked={mode === 'csv'} onChange={() => setMode('csv')} />
                <span>CSV貼り付け</span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="radio"
                  name="batchMode"
                  checked={mode === 'expand'}
                  onChange={() => setMode('expand')}
                />
                <span>プレイリスト/チャンネル</span>
              </label>
            </div>
          </div>

          {mode === 'url_list' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">URLリスト（複数行）</label>
              <textarea
                value={urlListText}
                onChange={(e) => setUrlListText(e.target.value)}
                className="input-field"
                rows={8}
                placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/..."
              />
            </div>
          )}

          {mode === 'csv' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">CSV（url,title,tags）</label>
              <textarea
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                className="input-field"
                rows={8}
                placeholder="https://www.youtube.com/watch?v=...,任意タイトル,tag1;tag2"
              />
              <p className="mt-1 text-sm text-gray-500">tagは `;` 区切り</p>
            </div>
          )}

          {mode === 'expand' && (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">プレイリスト/チャンネルURL</label>
                <input
                  value={expandUrl}
                  onChange={(e) => setExpandUrl(e.target.value)}
                  className="input-field"
                  placeholder="https://www.youtube.com/playlist?list=..."
                />
              </div>
              <button onClick={handleExpand} disabled={isExpanding || !expandUrl.trim()} className="btn-primary">
                {isExpanding ? '展開中...' : '展開して取り込む'}
              </button>

              {expandItems.length > 0 && (
                <div className="text-sm text-gray-600">
                  取り込み対象: {expandItems.length} 件
                </div>
              )}
            </div>
          )}

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700">
            <div className="font-medium mb-1">共通設定（Settingsの既定値）</div>
            <div>言語: {settings.language}</div>
            <div>モデル: {settings.transcriptionModel}</div>
            <div>分割: MAX_SINGLE_CHUNK_SEC={settings.maxSingleChunkSec}</div>
            <div>Proofread: {settings.proofreadEnabled ? 'ON' : 'OFF'} / QA: {settings.qaEnabled ? 'ON' : 'OFF'}</div>
          </div>

          <button
            onClick={handleRun}
            disabled={isRunning || inputItems.length === 0}
            className="btn-primary w-full"
          >
            {isRunning ? '投入中...' : `Run（${inputItems.length}件をQueueに投入）`}
          </button>
        </div>
      </section>

      {/* Right: Queue + Preview */}
      <section className="card">
        <h2 className="text-xl font-semibold mb-4">Queue</h2>

        <div className="overflow-x-auto border border-gray-200 rounded-lg">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-gray-700">
              <tr>
                <th className="text-left px-3 py-2">状態</th>
                <th className="text-left px-3 py-2">タイトル</th>
                <th className="text-left px-3 py-2">進捗</th>
                <th className="text-left px-3 py-2">エラー</th>
                <th className="text-left px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((item) => (
                <tr
                  key={item.key}
                  className={`border-t cursor-pointer ${item.key === selectedKey ? 'bg-gray-50' : ''}`}
                  onClick={() => selectRow(item)}
                >
                  <td className="px-3 py-2">{item.status || '-'}</td>
                  <td className="px-3 py-2">
                    <div className="text-gray-900">{item.userTitle || '—'}</div>
                    <div className="text-gray-500 truncate max-w-[320px]">{item.youtubeUrl}</div>
                  </td>
                  <td className="px-3 py-2">{typeof item.progress === 'number' ? `${item.progress}%` : '-'}</td>
                  <td className="px-3 py-2 text-red-700">{item.error || ''}</td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        void cancelQueueItem(item)
                      }}
                      disabled={isTerminalStatus(item.status) || isCanceling(item.key)}
                      className="btn-secondary px-3 py-1 text-xs whitespace-nowrap disabled:opacity-50"
                    >
                      {item.status === 'canceled' ? '取消済み' : isCanceling(item.key) ? '取消中...' : '取消'}
                    </button>
                  </td>
                </tr>
              ))}
              {queue.length === 0 && (
                <tr>
                  <td className="px-3 py-6 text-gray-500" colSpan={5}>
                    まだ投入されていません
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4">
          <div className="font-medium text-gray-900 mb-2">最新結果プレビュー</div>
          {selected?.jobId ? (
            <div className="space-y-2">
              <div className="text-sm text-gray-600">job_id: {selected.jobId}</div>
              <button onClick={() => onSelectJob(selected.jobId!)} className="btn-primary">
                Resultsで詳細を見る
              </button>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm">
                <div className="text-gray-700 font-medium mb-1">Transcript</div>
                <div className="text-gray-700 whitespace-pre-wrap">
                  {(preview?.transcript?.text || '').slice(0, 400) || '（未完了）'}
                </div>

                <div className="text-gray-700 font-medium mt-3 mb-1">Proofread</div>
                <div className="text-gray-700 whitespace-pre-wrap">
                  {(preview?.corrected_transcript?.corrected_text || '').slice(0, 400) || '（未作成）'}
                </div>

                <div className="text-gray-700 font-medium mt-3 mb-1">QA</div>
                <div className="text-gray-700 whitespace-pre-wrap">
                  {preview?.qa_results?.length
                    ? `${preview.qa_results[preview.qa_results.length - 1].question}\n${preview.qa_results[preview.qa_results.length - 1].answer}`.slice(0, 400)
                    : '（なし）'}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">行を選択するとプレビューが表示されます（詳細はResults）。</div>
          )}
        </div>
      </section>
    </div>
  )
}
