'use client'

import { useState, useEffect, useRef } from 'react'
import { apiClient } from '@/lib/api'

interface TranscriptResultProps {
  jobId: string
}

interface JobResult {
  job_id: string
  status: string
  model?: string
  audio_file?: {
    title: string
    duration_seconds: number
    format: string
    file_size_bytes: number
  }
  transcript?: {
    text: string
    language_detected: string
    transcription_model: string
    created_at: string
  }
  corrected_transcript?: {
    corrected_text: string
    original_text: string
    correction_model: string
    changes_summary: string
    created_at: string
  }
  qa_results?: QaResult[]
  error_message?: string
}

interface QaResult {
  question: string
  answer: string
  qa_model?: string
  created_at: string
}

export default function TranscriptResult({ jobId }: TranscriptResultProps) {
  const [result, setResult] = useState<JobResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isQaSubmitting, setIsQaSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [exportFormat, setExportFormat] = useState<'txt' | 'srt' | 'vtt'>('txt')
  const [isExporting, setIsExporting] = useState(false)
  const [activeTab, setActiveTab] = useState<'original' | 'proofread' | 'qa'>('original')
  const [isProofreading, setIsProofreading] = useState(false)
  const [proofreadModel, setProofreadModel] = useState('gpt-4o-mini')
  const [qaModel, setQaModel] = useState('gpt-4o-mini')
  const [qaQuestion, setQaQuestion] = useState('')
  const [qaHistory, setQaHistory] = useState<QaResult[]>([])
  const autoProofreadQueuedRef = useRef(false)

  const normalizeProofreadModel = (jobModel?: string) => {
    // Job.model is a transcription model (e.g. gpt-4o-mini-transcribe).
    // Proofread expects chat models: gpt-4o-mini | gpt-4o.
    if (!jobModel) return 'gpt-4o-mini'
    if (jobModel.startsWith('gpt-4o-mini')) return 'gpt-4o-mini'
    if (jobModel.startsWith('gpt-4o')) return 'gpt-4o'
    return 'gpt-4o-mini'
  }

  useEffect(() => {
    // Reset state on job change
    setActiveTab('original')
    setProofreadModel('gpt-4o-mini')
    setQaModel('gpt-4o-mini')
    setQaQuestion('')
    setQaHistory([])
    autoProofreadQueuedRef.current = false
    fetchResult()
  }, [jobId])

  const fetchResult = async () => {
    try {
      const data = await apiClient.getJobResult(jobId)
      setResult(data)
      setQaHistory(data.qa_results || [])

      // 自動Proofread: 文字起こし完了かつ校正結果なしの場合に実行
      if (data.transcript && !data.corrected_transcript && !autoProofreadQueuedRef.current) {
        const defaultModel = normalizeProofreadModel(data.model)
        setProofreadModel(defaultModel)
        autoProofreadQueuedRef.current = true
        await triggerProofread(defaultModel, false)
      }
    } catch (err: any) {
      console.error('Failed to fetch result:', err)
      setError('結果の取得に失敗しました')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const blob = await apiClient.exportTranscript(jobId, exportFormat)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `transcript_${jobId.slice(0, 8)}.${exportFormat}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      console.error('Failed to export:', err)
      alert('エクスポートに失敗しました')
    } finally {
      setIsExporting(false)
    }
  }

  const triggerProofread = async (model: string, showAlert = true) => {
    setIsProofreading(true)
    try {
      await apiClient.requestProofread(jobId, model)
      if (showAlert) {
        alert('Proofreadを開始しました。少し待ってから結果を確認してください。')
      }
      setTimeout(fetchResult, 2000)
    } catch (err: any) {
      console.error('Failed to request proofread:', err)
      alert('Proofreadのリクエストに失敗しました')
    } finally {
      setIsProofreading(false)
    }
  }

  const pollForQaResult = async (previousLength: number, timeoutMs: number = 20000) => {
    const startedAt = Date.now()
    const currentJobId = jobId

    while (Date.now() - startedAt < timeoutMs) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      // jobが切り替わったら中断
      if (jobId !== currentJobId) return

      try {
        const data = await apiClient.getJobResult(currentJobId)
        setResult(data)
        const next = data.qa_results || []
        setQaHistory(next)
        if (next.length > previousLength) return
      } catch (err) {
        // 一時的な取得失敗は握りつぶして再試行
        console.warn('Failed to poll QA result:', err)
      }
    }
  }

  const triggerQa = async () => {
    if (!qaQuestion.trim()) return
    setIsQaSubmitting(true)
    try {
      const previousLength = qaHistory.length
      await apiClient.askQuestion(jobId, qaQuestion.trim(), qaModel)
      setQaQuestion('')
      // QAは非同期なので、結果がDBに保存されるまで少しポーリング
      await pollForQaResult(previousLength)
    } catch (err: any) {
      console.error('Failed to request QA:', err)
      alert('QAのリクエストに失敗しました')
    } finally {
      setIsQaSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    )
  }

  if (!result || !result.transcript) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
        文字起こし結果がまだありません
      </div>
    )
  }

  const { transcript, corrected_transcript, audio_file } = result
  const proofreadText = corrected_transcript?.corrected_text
  const displayText = activeTab === 'proofread' && proofreadText ? proofreadText : transcript.text

  return (
    <div className="space-y-6">
      {/* 音声ファイル情報 */}
      {audio_file && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-2">動画情報</h3>
          <div className="text-sm text-gray-600 space-y-1">
            <p>タイトル: {audio_file.title}</p>
            <p>長さ: {Math.floor(audio_file.duration_seconds / 60)}分{audio_file.duration_seconds % 60}秒</p>
            <p>形式: {audio_file.format?.toUpperCase()}</p>
          </div>
        </div>
      )}

      {/* タブ */}
      <div className="flex space-x-2">
        <button
          onClick={() => setActiveTab('original')}
          className={`px-4 py-2 rounded ${activeTab === 'original' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
        >
          Original
        </button>
        <button
          onClick={() => setActiveTab('proofread')}
          className={`px-4 py-2 rounded ${activeTab === 'proofread' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
        >
          Proofread
        </button>
        <button
          onClick={() => setActiveTab('qa')}
          className={`px-4 py-2 rounded ${activeTab === 'qa' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
        >
          QA
        </button>
      </div>

      {/* タブ内容 */}
      {activeTab === 'original' && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-medium text-gray-900">文字起こしテキスト</h3>
            <button onClick={() => handleCopy(transcript.text)} className="text-sm text-primary-600 hover:text-primary-700">
              {copied ? '✓ コピーしました' : 'コピー'}
            </button>
          </div>
          <div className="max-h-96 overflow-y-auto">
            <p className="whitespace-pre-wrap text-sm">{transcript.text}</p>
          </div>
        </div>
      )}

      {activeTab === 'proofread' && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:space-x-4 space-y-3 md:space-y-0">
            <div className="flex items-center space-x-2">
              <label className="text-sm text-gray-700">LLMモデル:</label>
              <select
                value={proofreadModel}
                onChange={(e) => setProofreadModel(e.target.value)}
                className="input-field"
              >
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gpt-4o">GPT-4o</option>
              </select>
            </div>
            <button
              onClick={() => triggerProofread(proofreadModel)}
              disabled={isProofreading}
              className="btn-primary"
            >
              {isProofreading ? 'Proofread中...' : 'Proofreadを実行'}
            </button>
          </div>

          {proofreadText ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-medium text-green-900">Proofread結果</h3>
                <button onClick={() => handleCopy(proofreadText)} className="text-sm text-green-700 hover:text-green-800">
                  {copied ? '✓ コピーしました' : 'コピー'}
                </button>
              </div>
              <div className="max-h-96 overflow-y-auto">
                <p className="whitespace-pre-wrap text-sm">{proofreadText}</p>
              </div>
              {corrected_transcript?.changes_summary && (
                <p className="text-sm text-green-800 mt-3">{corrected_transcript.changes_summary}</p>
              )}
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800">
              Proofread結果はまだありません。ボタンを押して実行してください。
            </div>
          )}
        </div>
      )}

      {activeTab === 'qa' && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:space-x-4 space-y-3 md:space-y-0">
            <div className="flex-1">
              <input
                type="text"
                value={qaQuestion}
                onChange={(e) => setQaQuestion(e.target.value)}
                placeholder="質問を入力してください"
                className="input-field w-full"
              />
            </div>
            <div className="flex items-center space-x-2">
              <select
                value={qaModel}
                onChange={(e) => setQaModel(e.target.value)}
                className="input-field"
              >
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gpt-4o">GPT-4o</option>
              </select>
              <button
                onClick={triggerQa}
                disabled={isQaSubmitting}
                className="btn-primary"
              >
                {isQaSubmitting ? '送信中...' : '質問する'}
              </button>
            </div>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4 max-h-96 overflow-y-auto">
            {qaHistory.length === 0 && (
              <p className="text-sm text-gray-600">まだQA結果がありません。質問を送信してください。</p>
            )}
            {qaHistory.map((qa, idx) => (
              <div key={`${qa.created_at}-${idx}`} className="space-y-2">
                <div className="text-sm font-medium text-gray-900">Q: {qa.question}</div>
                <div className="text-sm text-gray-800 whitespace-pre-wrap">A: {qa.answer}</div>
                <div className="text-xs text-gray-500">モデル: {qa.qa_model || '不明'} / {new Date(qa.created_at).toLocaleString()}</div>
                {idx < qaHistory.length - 1 && <hr className="border-gray-200" />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* エクスポート */}
      <div className="border-t pt-6">
        <h3 className="font-medium text-gray-900 mb-4">エクスポート</h3>
        <div className="flex items-center space-x-4">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as any)}
            className="input-field max-w-xs"
          >
            <option value="txt">TXT (テキストファイル)</option>
            <option value="srt">SRT (字幕ファイル)</option>
            <option value="vtt">VTT (WebVTT字幕)</option>
          </select>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="btn-secondary"
          >
            {isExporting ? 'エクスポート中...' : 'ダウンロード'}
          </button>
        </div>
      </div>
    </div>
  )
}
