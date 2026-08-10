'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'

interface JobStatusProps {
  jobId: string
  onStatusChange: (status: string) => void
}

interface StatusData {
  job_id: string
  status: string
  stage?: string
  stage_detail?: any
  progress: number
  error_message?: string
  youtube_url: string
  created_at: string
  updated_at: string
}

const stageMessages: Record<string, string> = {
  download_extract: 'ダウンロード/音声抽出中...',
  preprocess: '前処理中（圧縮/分割）...',
  transcribe: '文字起こし中（チャンク処理）...',
  merge: '結合中...',
  export: '出力準備中...',
}

const statusMessages: Record<string, string> = {
  pending: '処理待機中...',
  processing: '音声ファイルを抽出中...',
  transcribing: '文字起こし中...',
  correcting: 'LLMで校正中...',
  completed: '処理完了',
  failed: '処理失敗',
  canceled: 'キャンセル済み',
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-200',
  processing: 'bg-blue-500',
  transcribing: 'bg-blue-500',
  correcting: 'bg-purple-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  canceled: 'bg-amber-200',
}

export default function JobStatus({ jobId, onStatusChange }: JobStatusProps) {
  const [statusData, setStatusData] = useState<StatusData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    const fetchStatus = async () => {
      try {
        const data = await apiClient.getJobStatus(jobId)
        setStatusData(data)
        onStatusChange(data.status)

        // Stop polling if job reached a terminal state
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'canceled') {
          if (intervalId) clearInterval(intervalId)
        }
      } catch (err: any) {
        console.error('Failed to fetch status:', err)
        setError('ステータスの取得に失敗しました')
        if (intervalId) clearInterval(intervalId)
      }
    }

    // Fetch immediately
    fetchStatus()

    // Then poll every 3 seconds
    intervalId = setInterval(fetchStatus, 3000)

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [jobId, onStatusChange])

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    )
  }

  if (!statusData) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const { status, stage, stage_detail, progress, error_message } = statusData
  const isProcessing = !['completed', 'failed', 'canceled'].includes(status)

  const stageText = stage ? (stageMessages[stage] || stage) : null
  const chunkInfo =
    stage === 'transcribe' && stage_detail?.chunk_count
      ? ` (${stage_detail.chunk_index || 0}/${stage_detail.chunk_count})`
      : ''

  return (
    <div className="space-y-4">
      {/* ステータスバッジ */}
      <div className="flex items-center space-x-3">
        <div className={`px-4 py-2 rounded-full ${statusColors[status]} ${status === 'pending' || status === 'failed' || status === 'canceled' ? 'text-gray-700' : 'text-white'} font-medium`}>
          {statusMessages[status] || status}
        </div>
        {isProcessing && (
          <div className="flex items-center text-gray-600">
            <svg className="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            処理中
          </div>
        )}
      </div>

      {/* ステージ表示（互換性維持のため任意表示） */}
      {isProcessing && stageText && (
        <div className="text-sm text-gray-600">
          <span className="font-medium">ステージ:</span> {stageText}
          {chunkInfo}
        </div>
      )}

      {/* プログレスバー */}
      {isProcessing && (
        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>進捗状況</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-primary-600 h-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* エラーメッセージ */}
      {error_message && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <p className="font-medium">エラーが発生しました</p>
          <p className="text-sm mt-1">{error_message}</p>
        </div>
      )}

      {/* 完了メッセージ */}
      {status === 'completed' && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          <p className="font-medium">✓ 文字起こしが完了しました</p>
          <p className="text-sm mt-1">下の結果をご確認ください。</p>
        </div>
      )}

      {status === 'canceled' && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded">
          <p className="font-medium">処理はキャンセルされました</p>
          <p className="text-sm mt-1">必要であれば Batch から再投入してください。</p>
        </div>
      )}

      {/* ジョブ情報 */}
      <div className="text-sm text-gray-500 space-y-1">
        <p>ジョブID: <span className="font-mono">{jobId.slice(0, 8)}...</span></p>
        <p>動画URL: <a href={statusData.youtube_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">{statusData.youtube_url.slice(0, 50)}...</a></p>
      </div>
    </div>
  )
}
