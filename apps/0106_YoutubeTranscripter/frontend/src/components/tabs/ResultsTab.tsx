'use client'

import { useEffect, useMemo, useState, useCallback } from 'react'
import { apiClient } from '@/lib/api'
import { AppSettings } from '@/lib/settings'
import { InlineEditTitle } from '../InlineEditTitle'
import { RichTextEditor } from '../RichTextEditor'

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
  id: string
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
    language_detected?: string
    transcription_model?: string
    source?: 'youtube' | 'audio'
    segments?: Array<{ start: number; duration: number; text: string }>
    created_at: string
  }
  youtube_transcript?: {
    status: 'available' | 'unavailable' | 'error'
    video_id?: string
    text?: string
    language_code?: string
    language_name?: string
    is_generated?: boolean
    available_tracks?: Array<{
      language_code: string
      language_name: string
      is_generated: boolean
    }>
    segments?: Array<{ start: number; duration: number; text: string }>
    error_message?: string
    created_at?: string
  }
  corrected_transcript?: {
    corrected_text: string
    created_at: string
  }
  key_points_summary?: {
    status: 'pending' | 'completed' | 'error'
    key_points_text?: string
    key_points_model?: string
    prompt?: string
    error_message?: string
    created_at?: string
  }
  qa_results?: QaResult[]
  error_message?: string
}

type KeyPointsModel = 'gpt-4o-mini' | 'gpt-4o' | 'gpt-5-mini'
type SubTab = 'youtube-transcript' | 'transcript' | 'key-points' | 'qa' | 'note'

const DEFAULT_KEY_POINTS_PROMPT = `詳細要点抽出プロンプト

以下のTranscriptを、章ごとに題目を付けて整理してください。

単なる短い要約ではなく、**内容を後からTranscriptを読み直さなくても把握できるレベルの「詳細な要点抽出」**を行ってください。

## 出力ルール

1. 内容の流れに沿って適切な章に分割し、各章に分かりやすい題目を付ける。
2. **各章について、重要事項を10〜20項目程度を目安に詳しく列記する。**
   - 内容の少ない章は無理に10項目に増やす必要はない。
   - 内容の多い章は20項目を超えてもよい。
   - 全体として、通常の簡潔な要約より**約3倍程度多くの情報を残す**こと。
3. 以下は省略せず、可能な限り独立した要点として残す。
   - 話者の主要な主張
   - その主張に至る理由・背景
   - 根拠として挙げている内容
   - 具体例
   - エピソード
   - 人物名・組織名・地名
   - 年代・数字・金額
   - 原因と結果の関係
   - 比較・対比
   - 話者が特に強調している点
   - 結論や今後の予測
   - 前後の話をつなぐ重要な補足説明
4. **複数の異なる論点を1つの短い箇条書きにまとめすぎないこと。**
   例えば、

   「Aが起き、その背景にはBがあり、その結果Cになった」

   という説明がある場合は、必要に応じて
   - Aという出来事
   - Aが起きた背景としてBを説明
   - その結果としてCが生じたと主張
   のように分ける。
5. 一つ一つの要点は、単語や短いフレーズだけではなく、**原則1〜3文程度で内容が理解できるように記述する。**
6. Transcript内で繰り返されているだけの内容は統合してよいが、**意味やニュアンスの異なる発言を安易に同一項目へ統合しない。**
7. Transcriptに登場する情報を優先し、勝手な推測や外部情報を付け加えない。
8. 話者の主張、推測、都市伝説、意見などについては、それを客観的事実として断定せず、
   - 「話者は〜と主張している」
   - 「動画では〜と説明している」
   - 「〜ではないかという説を紹介している」
   のように、**Transcript内の主張であることが分かる表現**にする。
9. 最後に情報量を自己チェックし、
   **「短くまとめすぎていないか」「重要な理由・具体例・背景を落としていないか」**
   を確認してから出力する。

## 出力形式

### 1. 章タイトル

- 要点1
- 要点2
- 要点3
- …
- 必要に応じて10〜20項目以上

### 2. 章タイトル

- 要点1
- 要点2
- 要点3

この形式でTranscript全体を最後まで処理してください。`

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
  const [keyPointsModel, setKeyPointsModel] = useState<KeyPointsModel>('gpt-4o-mini')
  const [keyPointsPrompt, setKeyPointsPrompt] = useState(DEFAULT_KEY_POINTS_PROMPT)
  const [isKeyPointsPromptEditing, setIsKeyPointsPromptEditing] = useState(false)
  const [isKeyPointsExtracting, setIsKeyPointsExtracting] = useState(false)

  const [editableDrafts, setEditableDrafts] = useState<Record<string, string>>({})
  const [savedEditableDrafts, setSavedEditableDrafts] = useState<Record<string, string>>({})
  const [savingEditableKey, setSavingEditableKey] = useState<string | null>(null)

  const [noteContent, setNoteContent] = useState('')
  const [originalNote, setOriginalNote] = useState('')
  const [isNoteSaving, setIsNoteSaving] = useState(false)
  const [noteLastSaved, setNoteLastSaved] = useState<string | null>(null)

  const [reRunModel, setReRunModel] = useState(settings.transcriptionModel)
  const [isReRunning, setIsReRunning] = useState(false)

  useEffect(() => {
    setQaModel(settings.qaModel)
    setReRunModel(settings.transcriptionModel)
  }, [settings.qaModel, settings.transcriptionModel])

  const mergeGeneratedEditableContent = (jobResult: JobResult) => {
    const generated: Record<string, string> = {}
    if (jobResult.youtube_transcript?.text) generated.youtube_transcript = jobResult.youtube_transcript.text
    if (jobResult.transcript?.text) generated.transcript = jobResult.transcript.text
    if (jobResult.corrected_transcript?.corrected_text) {
      generated.proofread = jobResult.corrected_transcript.corrected_text
    }
    if (jobResult.key_points_summary?.key_points_text) {
      generated.key_points = jobResult.key_points_summary.key_points_text
    }
    ;(jobResult.qa_results || []).forEach((qa) => {
      generated[`qa:${qa.id}:question`] = qa.question
      generated[`qa:${qa.id}:answer`] = qa.answer
    })

    const nextDrafts = { ...editableDrafts }
    const nextSavedDrafts = { ...savedEditableDrafts }
    Object.entries(generated).forEach(([key, value]) => {
      const currentDraft = editableDrafts[key]
      const currentSavedDraft = savedEditableDrafts[key]
      const hasNoLocalEdits = currentDraft === undefined || currentDraft === currentSavedDraft

      // Adopt newly generated content immediately, while preserving unsaved user edits.
      if (hasNoLocalEdits) {
        nextDrafts[key] = value
        nextSavedDrafts[key] = value
      }
    })
    setEditableDrafts(nextDrafts)
    setSavedEditableDrafts(nextSavedDrafts)
  }

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
      if (r?.key_points_summary?.prompt) {
        setKeyPointsPrompt(r.key_points_summary.prompt)
      }
      setNoteContent(n.content || '')
      setOriginalNote(n.content || '')
      setNoteLastSaved(n.updated_at || null)

      const drafts: Record<string, string> = {
        youtube_transcript: r?.youtube_transcript?.text || '',
        transcript: r?.transcript?.text || '',
        proofread: r?.corrected_transcript?.corrected_text || '',
        key_points: r?.key_points_summary?.key_points_text || '',
      }
      ;(r?.qa_results || []).forEach((qa: QaResult) => {
        drafts[`qa:${qa.id}:question`] = qa.question
        drafts[`qa:${qa.id}:answer`] = qa.answer
      })
      setEditableDrafts(drafts)
      setSavedEditableDrafts(drafts)

      if (!r?.corrected_transcript && !['failed', 'canceled'].includes(s.status)) {
        void pollForAutomaticProofread()
      }

    } catch (err: any) {
      setError(err?.response?.data?.detail || '結果の取得に失敗しました')
      setStatus(null)
      setResult(null)
    } finally {
      setIsLoading(false)
    }
  }

  const pollForKeyPointsResult = async (timeoutMs: number = 120000): Promise<boolean> => {
    if (!jobId) return false
    const startedAt = Date.now()
    const currentJobId = jobId

    while (Date.now() - startedAt < timeoutMs) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      if (jobId !== currentJobId) return false

      try {
        const r = await apiClient.getJobResult(currentJobId)
        setResult(r)
        mergeGeneratedEditableContent(r)
        const summary = r?.key_points_summary
        if (summary?.status === 'completed' || summary?.status === 'error') {
          try {
            const s = await apiClient.getJobStatus(currentJobId)
            setStatus(s)
          } catch {
            // ignore status refresh failures
          }
          return summary.status === 'completed'
        }
      } catch {
        // ignore transient failures and keep polling
      }
    }

    return false
  }

  const pollForAutomaticProofread = async (timeoutMs: number = 120000): Promise<boolean> => {
    if (!jobId) return false
    const startedAt = Date.now()
    const currentJobId = jobId

    while (Date.now() - startedAt < timeoutMs) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      if (jobId !== currentJobId) return false

      try {
        const r = await apiClient.getJobResult(currentJobId)
        setResult(r)
        mergeGeneratedEditableContent(r)
        if (r?.corrected_transcript?.corrected_text) {
          const s = await apiClient.getJobStatus(currentJobId)
          setStatus(s)
          return true
        }

        const s = await apiClient.getJobStatus(currentJobId)
        setStatus(s)
        if (s.status === 'failed' || s.status === 'canceled' || s.status === 'completed') {
          return false
        }
      } catch {
        // Ignore transient result/status failures and continue polling.
      }
    }

    return false
  }

  useEffect(() => {
    setActive('transcript')
    setQaQuestion('')
    setKeyPointsPrompt(DEFAULT_KEY_POINTS_PROMPT)
    setIsKeyPointsPromptEditing(false)
    setNoteContent('')
    setOriginalNote('')
    setNoteLastSaved(null)
    setEditableDrafts({})
    setSavedEditableDrafts({})
    setSavingEditableKey(null)
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

  const youtubeTranscriptText = editableDrafts.youtube_transcript ?? (result?.youtube_transcript?.text || '')
  const editableTranscriptText = editableDrafts.transcript ?? transcriptText
  const editableProofreadText = editableDrafts.proofread ?? proofreadText
  const editableKeyPointsText = editableDrafts.key_points ?? (result?.key_points_summary?.key_points_text || '')
  const transcriptDisplayText = proofreadText || transcriptText
  const transcriptDisplayValue = proofreadText ? editableProofreadText : editableTranscriptText
  const transcriptDisplayType = proofreadText ? 'proofread' : 'transcript'

  const updateEditableDraft = (key: string, value: string) => {
    setEditableDrafts((previous) => ({ ...previous, [key]: value }))
  }

  const saveEditableContent = async (contentType: string, key: string, content: string, qaId?: string) => {
    if (!jobId) return
    setSavingEditableKey(key)
    try {
      await apiClient.updateResultContent(jobId, contentType, content, qaId)
      setSavedEditableDrafts((previous) => ({ ...previous, [key]: content }))
    } catch (err: any) {
      alert(err?.response?.data?.detail || '本文の保存に失敗しました')
    } finally {
      setSavingEditableKey(null)
    }
  }

  const exportText = () => {
    if (!jobId) return
    const text = editableProofreadText || editableTranscriptText
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

  const triggerProofread = async () => {
    try {
      return
      // Proofreadは非同期でDB反映に時間がかかるので、反映されるまでポーリング
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Proofreadのリクエストに失敗しました')
    } finally {
    }
  }

  const triggerKeyPoints = async () => {
    if (!jobId || !keyPointsPrompt.trim()) return
    setIsKeyPointsExtracting(true)
    try {
      await apiClient.requestKeyPoints(jobId, keyPointsModel, keyPointsPrompt)
      const ok = await pollForKeyPointsResult()
      if (!ok) {
        fetchAll()
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || '要点抽出のリクエストに失敗しました')
    } finally {
      setIsKeyPointsExtracting(false)
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
          mergeGeneratedEditableContent(r)
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
    if (!status?.youtube_url || isReRunning) return
    setIsReRunning(true)
    try {
      const res = await apiClient.createJob(status.youtube_url, status.language, reRunModel, {
        proofread_model: settings.proofreadModel,
      })
      onSelectJob(res.job_id)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Re-runに失敗しました')
    } finally {
      setIsReRunning(false)
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
              <button
                className="btn-primary min-w-[104px] whitespace-nowrap"
                onClick={reRun}
                disabled={isReRunning || !status?.youtube_url}
              >
                {isReRunning ? 'Re-running...' : 'Re-run'}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="flex items-center gap-2 mb-4">
          <button
            className={`px-4 py-2 rounded ${active === 'youtube-transcript' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('youtube-transcript')}
          >
            YouTube Transcript
          </button>
          <button
            className={`px-4 py-2 rounded ${active === 'transcript' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('transcript')}
          >
            Transcript
          </button>
          <button
            className={`px-4 py-2 rounded ${active === 'key-points' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            onClick={() => setActive('key-points')}
          >
            要点抽出
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

        {!error && active === 'youtube-transcript' && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
            {result?.youtube_transcript?.status === 'available' ? (
              <>
                <div className="text-sm text-gray-700">
                  Language: {result.youtube_transcript.language_name || result.youtube_transcript.language_code || 'unknown'}
                  {' · '}
                  {result.youtube_transcript.is_generated ? 'Auto-generated' : 'Manually provided'}
                  {result.youtube_transcript.video_id ? ` · Video ID: ${result.youtube_transcript.video_id}` : ''}
                </div>
                {!!result.youtube_transcript.available_tracks?.length && (
                  <div className="text-xs text-gray-600">
                    Available subtitles:{' '}
                    {result.youtube_transcript.available_tracks
                      .map((track) => `${track.language_name || track.language_code} (${track.is_generated ? 'auto' : 'manual'})`)
                      .join(', ')}
                  </div>
                )}
                {youtubeTranscriptText ? (
                  <RichTextEditor
                    value={youtubeTranscriptText}
                    onChange={(value) => updateEditableDraft('youtube_transcript', value)}
                    onSave={() => saveEditableContent('youtube_transcript', 'youtube_transcript', youtubeTranscriptText)}
                    saving={savingEditableKey === 'youtube_transcript'}
                    hasChanges={youtubeTranscriptText !== savedEditableDrafts.youtube_transcript}
                    label="YouTube Transcript Editor"
                  />
                ) : (
                  <div className="text-sm text-gray-500">（本文なし）</div>
                )}
              </>
            ) : result?.youtube_transcript?.status === 'error' ? (
              <div className="text-sm text-amber-700">
                YouTube transcript retrieval failed; the audio transcription fallback was used.
              </div>
            ) : (
              <div className="text-sm text-gray-500">
                No YouTube-provided transcript is available for this video.
              </div>
            )}
          </div>
        )}

        {!error && active === 'transcript' && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            {transcriptDisplayText ? (
              <RichTextEditor
                value={transcriptDisplayValue}
                onChange={(value) => updateEditableDraft(transcriptDisplayType, value)}
                onSave={() => saveEditableContent(transcriptDisplayType, transcriptDisplayType, transcriptDisplayValue)}
                saving={savingEditableKey === transcriptDisplayType}
                hasChanges={transcriptDisplayValue !== savedEditableDrafts[transcriptDisplayType]}
                label="Transcript Editor"
                placeholder="Transcript はまだありません"
              />
            ) : (
              <div className="text-sm text-gray-500">（未完了）</div>
            )}
          </div>
        )}

        {false && (
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
                  <option value="gpt-5-mini">gpt-5-mini</option>
                </select>
              </div>
              <button className="btn-primary" onClick={triggerProofread} disabled={isProofreading}>
                {isProofreading ? 'Proofread中...' : 'Proofreadを実行'}
              </button>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              {proofreadText ? (
                <RichTextEditor
                  value={editableProofreadText}
                  onChange={(value) => updateEditableDraft('proofread', value)}
                  onSave={() => saveEditableContent('proofread', 'proofread', editableProofreadText)}
                  saving={savingEditableKey === 'proofread'}
                  hasChanges={editableProofreadText !== savedEditableDrafts.proofread}
                  label="Proofread Editor"
                />
              ) : (
                <div className="text-sm text-gray-500">（未作成）</div>
              )}
            </div>
          </div>
        )}

        {!error && active === 'key-points' && (
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row md:items-center gap-2">
              <select
                aria-label="要点抽出LLM"
                value={keyPointsModel}
                onChange={(e) => setKeyPointsModel(e.target.value as KeyPointsModel)}
                className="input-field"
              >
                <option value="gpt-4o-mini">gpt-4o-mini</option>
                <option value="gpt-4o">gpt-4o</option>
                <option value="gpt-5-mini">gpt-5-mini</option>
              </select>
              <button className="btn-primary" onClick={triggerKeyPoints} disabled={isKeyPointsExtracting || !keyPointsPrompt.trim()}>
                {isKeyPointsExtracting ? '要点抽出中...' : '要点抽出を実行'}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setIsKeyPointsPromptEditing((value) => !value)}
              >
                {isKeyPointsPromptEditing ? 'プロンプト編集を閉じる' : '要点抽出プロンプト編集'}
              </button>
            </div>

            {isKeyPointsPromptEditing && (
              <textarea
                value={keyPointsPrompt}
                onChange={(e) => setKeyPointsPrompt(e.target.value)}
                className="input-field min-h-[360px] w-full font-mono text-sm"
                aria-label="要点抽出プロンプト"
              />
            )}

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              {result?.key_points_summary?.status === 'pending' ? (
                <div className="text-sm text-gray-500">要点抽出を実行中です...</div>
              ) : result?.key_points_summary?.status === 'error' ? (
                <div className="text-sm text-red-700">
                  要点抽出に失敗しました: {result.key_points_summary.error_message || '不明なエラー'}
                </div>
              ) : editableKeyPointsText ? (
                <RichTextEditor
                  value={editableKeyPointsText}
                  onChange={(value) => updateEditableDraft('key_points', value)}
                  onSave={() => saveEditableContent('key_points', 'key_points', editableKeyPointsText)}
                  saving={savingEditableKey === 'key_points'}
                  hasChanges={editableKeyPointsText !== savedEditableDrafts.key_points}
                  label="Key Points Editor"
                />
              ) : (
                <div className="text-sm text-gray-500">（要点抽出結果はまだありません）</div>
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
                  <option value="gpt-5-mini">gpt-5-mini</option>
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
              {(result?.qa_results || []).map((qa) => {
                const questionKey = `qa:${qa.id}:question`
                const answerKey = `qa:${qa.id}:answer`
                const questionValue = editableDrafts[questionKey] ?? qa.question
                const answerValue = editableDrafts[answerKey] ?? qa.answer
                return (
                  <div key={qa.id} className="border border-gray-200 rounded-lg p-3 space-y-3">
                    <RichTextEditor
                      value={questionValue}
                      onChange={(value) => updateEditableDraft(questionKey, value)}
                      onSave={() => saveEditableContent('qa_question', questionKey, questionValue, qa.id)}
                      saving={savingEditableKey === questionKey}
                      hasChanges={questionValue !== savedEditableDrafts[questionKey]}
                      label="Q"
                      className="border-0"
                    />
                    <RichTextEditor
                      value={answerValue}
                      onChange={(value) => updateEditableDraft(answerKey, value)}
                      onSave={() => saveEditableContent('qa_answer', answerKey, answerValue, qa.id)}
                      saving={savingEditableKey === answerKey}
                      hasChanges={answerValue !== savedEditableDrafts[answerKey]}
                      label="A"
                      className="border-0"
                    />
                    <div className="text-xs text-gray-500">{qa.created_at}</div>
                  </div>
                )
              })}
              {!result?.qa_results?.length && <div className="text-sm text-gray-500">（履歴なし）</div>}
            </div>
          </div>
        )}

        {!error && active === 'note' && (
          <div className="space-y-3">
            <RichTextEditor
              value={noteContent}
              onChange={setNoteContent}
              onSave={saveNote}
              saving={isNoteSaving}
              hasChanges={noteHasChanges}
              label="Note Editor"
              placeholder="メモを入力..."
            />
            {noteLastSaved && (
              <span className="text-xs text-gray-500">
                最終保存: {new Date(noteLastSaved).toLocaleString()}
              </span>
            )}
            {noteHasChanges && (
              <span className="text-xs text-amber-600">未保存の変更があります</span>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
