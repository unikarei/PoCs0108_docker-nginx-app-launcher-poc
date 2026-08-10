'use client'

import { useEffect, useState } from 'react'
import { AppSettings, saveSettings } from '@/lib/settings'

type Props = {
  settings: AppSettings
  onChange: (next: AppSettings) => void
}

type FolderFieldProps = {
  label: string
  value: string
  placeholder: string
  onChange: (next: string) => void
}

function FolderField({ label, value, placeholder, onChange }: FolderFieldProps) {
  const handlePick = async () => {
    try {
      const picker = (window as Window & {
        showDirectoryPicker?: (options?: { mode?: 'read' | 'readwrite' }) => Promise<{ name: string }>
      }).showDirectoryPicker

      if (picker) {
        const handle = await picker({ mode: 'readwrite' })
        onChange(handle.name)
        return
      }

      const next = window.prompt('バックアップ先フォルダ名を入力してください', value)
      if (next !== null) {
        onChange(next.trim())
      }
    } catch {
      // Folder selection was cancelled.
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="input-field flex-1"
        />
        <button type="button" onClick={handlePick} className="btn-secondary px-4 whitespace-nowrap">
          フォルダ選択
        </button>
      </div>
      <p className="mt-1 text-sm text-gray-500">ブラウザのフォルダ選択で指定した値を保存します。</p>
    </div>
  )
}

export default function SettingsTab({ settings, onChange }: Props) {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    setHydrated(true)
  }, [])

  const set = (patch: Partial<AppSettings>) => {
    const next = { ...settings, ...patch }
    onChange(next)
    if (hydrated) saveSettings(next)
  }

  return (
    <div className="space-y-6">
      <section className="card">
        <h2 className="text-xl font-semibold mb-4">Defaults</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">言語</label>
            <select
              value={settings.language}
              onChange={(e) => set({ language: e.target.value as AppSettings['language'] })}
              className="input-field"
            >
              <option value="ja">日本語</option>
              <option value="en">英語</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">文字起こしモデル</label>
            <select
              value={settings.transcriptionModel}
              onChange={(e) =>
                set({ transcriptionModel: e.target.value as AppSettings['transcriptionModel'] })
              }
              className="input-field"
            >
              <option value="gpt-4o-mini-transcribe">GPT-4o Mini (高速・経済的)</option>
              <option value="gpt-4o-transcribe">GPT-4o (高精度)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">分割方針（秒）</label>
            <input
              type="number"
              min={0}
              value={settings.maxSingleChunkSec}
              onChange={(e) => set({ maxSingleChunkSec: Number(e.target.value) })}
              className="input-field"
            />
            <p className="mt-1 text-sm text-gray-500">
              `MAX_SINGLE_CHUNK_SEC` の既定値。0以下で無効化。
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">保存ポリシー</label>
            <label className="flex items-center space-x-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={settings.autoSaveToDb}
                onChange={(e) => set({ autoSaveToDb: e.target.checked })}
              />
              <span>自動保存（UI上は “Saved” 表示）</span>
            </label>
            <p className="mt-1 text-sm text-gray-500">
              現状バックエンドはジョブを常にDBへ保存します（この設定は表示挙動のため）。
            </p>
          </div>
        </div>
      </section>

      <section className="card">
        <h2 className="text-xl font-semibold mb-4">Optional Steps</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="flex items-center space-x-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={settings.proofreadEnabled}
                onChange={(e) => set({ proofreadEnabled: e.target.checked })}
              />
              <span>Proofread を投入時に有効化</span>
            </label>

            <div className="mt-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Proofreadモデル</label>
              <select
                value={settings.proofreadModel}
                onChange={(e) => set({ proofreadModel: e.target.value as AppSettings['proofreadModel'] })}
                className="input-field"
                disabled={!settings.proofreadEnabled}
              >
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gpt-4o">GPT-4o</option>
              </select>
            </div>
          </div>

          <div>
            <label className="flex items-center space-x-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={settings.qaEnabled}
                onChange={(e) => set({ qaEnabled: e.target.checked })}
              />
              <span>QA を投入時に有効化</span>
            </label>

            <div className="mt-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">QAモデル</label>
              <select
                value={settings.qaModel}
                onChange={(e) => set({ qaModel: e.target.value as AppSettings['qaModel'] })}
                className="input-field"
                disabled={!settings.qaEnabled}
              >
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gpt-4o">GPT-4o</option>
              </select>
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <h2 className="text-xl font-semibold mb-4">Backup</h2>

        <div className="grid grid-cols-1 gap-4">
          <FolderField
            label="DB バックアップフォルダ"
            value={settings.dbBackupFolder}
            placeholder="例: D:/backups/transcriptor/db"
            onChange={(next) => set({ dbBackupFolder: next })}
          />

          <FolderField
            label="Audio File バックアップフォルダ"
            value={settings.audioBackupFolder}
            placeholder="例: D:/backups/transcriptor/audio"
            onChange={(next) => set({ audioBackupFolder: next })}
          />
        </div>
      </section>
    </div>
  )
}
