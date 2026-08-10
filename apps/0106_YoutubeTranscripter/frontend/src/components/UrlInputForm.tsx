'use client'

import { useState, FormEvent } from 'react'
import { apiClient } from '@/lib/api'

interface UrlInputFormProps {
  onJobCreated: (jobId: string) => void
  disabled?: boolean
}

export default function UrlInputForm({ onJobCreated, disabled }: UrlInputFormProps) {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [language, setLanguage] = useState('ja')
  const [model, setModel] = useState('gpt-4o-mini-transcribe')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [urlError, setUrlError] = useState<string | null>(null)

  const validateYoutubeUrl = (url: string): boolean => {
    if (!url) {
      setUrlError('YouTube URLを入力してください')
      return false
    }

    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/
    if (!youtubeRegex.test(url)) {
      setUrlError('有効なYouTube URLを入力してください')
      return false
    }

    setUrlError(null)
    return true
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!validateYoutubeUrl(youtubeUrl)) {
      return
    }

    setIsLoading(true)

    try {
      const response = await apiClient.createJob(youtubeUrl, language, model)
      onJobCreated(response.job_id)
      setYoutubeUrl('')
    } catch (err: any) {
      console.error('Failed to create job:', err)
      setError(
        err.response?.data?.detail || 
        'ジョブの作成に失敗しました。もう一度お試しください。'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* YouTube URL入力 */}
      <div>
        <label htmlFor="youtube-url" className="block text-sm font-medium text-gray-700 mb-2">
          YouTube動画URL
        </label>
        <input
          id="youtube-url"
          type="text"
          value={youtubeUrl}
          onChange={(e) => {
            setYoutubeUrl(e.target.value)
            setUrlError(null)
          }}
          onBlur={() => youtubeUrl && validateYoutubeUrl(youtubeUrl)}
          placeholder="https://www.youtube.com/watch?v=..."
          className={`input-field ${urlError ? 'border-red-500' : ''}`}
          disabled={disabled || isLoading}
        />
        {urlError && (
          <p className="mt-1 text-sm text-red-600">{urlError}</p>
        )}
        <p className="mt-1 text-sm text-gray-500">
          ※ 動画の長さはモデルにより制限があります（長い場合は自動で分割して処理されます）
        </p>
      </div>

      {/* 言語選択 */}
      <div>
        <label htmlFor="language" className="block text-sm font-medium text-gray-700 mb-2">
          文字起こし言語
        </label>
        <select
          id="language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="input-field"
          disabled={disabled || isLoading}
        >
          <option value="ja">日本語</option>
          <option value="en">英語</option>
        </select>
      </div>

      {/* モデル選択 */}
      <div>
        <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-2">
          文字起こしモデル
        </label>
        <select
          id="model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="input-field"
          disabled={disabled || isLoading}
        >
          <option value="gpt-4o-mini-transcribe">GPT-4o Mini (高速・経済的)</option>
          <option value="gpt-4o-transcribe">GPT-4o (高精度)</option>
        </select>
      </div>

      {/* エラーメッセージ */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* 送信ボタン */}
      <button
        type="submit"
        disabled={disabled || isLoading || !youtubeUrl}
        className="btn-primary w-full"
      >
        {isLoading ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            処理中...
          </span>
        ) : (
          '文字起こしを開始'
        )}
      </button>
    </form>
  )
}
