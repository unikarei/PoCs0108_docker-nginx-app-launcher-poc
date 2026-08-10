'use client'

import { useEffect, useState } from 'react'
import BatchTab from '@/components/tabs/BatchTab'
import ResultsTab from '@/components/tabs/ResultsTab'
import LibraryTab from '@/components/tabs/LibraryTab'
import SettingsTab from '@/components/tabs/SettingsTab'
import { AppSettings, loadSettings } from '@/lib/settings'

type TopTab = 'batch' | 'results' | 'library' | 'settings'

function getInitialTab(): TopTab {
  if (typeof window === 'undefined') return 'batch'
  const tab = new URLSearchParams(window.location.search).get('tab')
  if (tab === 'batch' || tab === 'results' || tab === 'library' || tab === 'settings') return tab
  return 'batch'
}

function getInitialJobId(): string | null {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.search).get('job_id')
}

function setQuery(params: { tab?: TopTab; job_id?: string | null }) {
  if (typeof window === 'undefined') return
  const sp = new URLSearchParams(window.location.search)
  if (params.tab) sp.set('tab', params.tab)
  if (params.job_id === null) sp.delete('job_id')
  else if (typeof params.job_id === 'string') sp.set('job_id', params.job_id)
  const next = `${window.location.pathname}?${sp.toString()}`
  window.history.replaceState(null, '', next)
}

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TopTab>('batch')
  const [jobId, setJobId] = useState<string | null>(null)
  const [settings, setSettings] = useState<AppSettings>(() => ({ ...loadSettings() }))

  useEffect(() => {
    const tab = getInitialTab()
    const id = getInitialJobId()
    setActiveTab(tab)
    setJobId(id)
  }, [])

  const selectJob = (id: string) => {
    setJobId(id)
    setActiveTab('results')
    setQuery({ tab: 'results', job_id: id })
  }

  const switchTab = (tab: TopTab) => {
    setActiveTab(tab)
    setQuery({ tab, job_id: jobId })
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => switchTab('batch')}
            className={`px-4 py-2 rounded ${activeTab === 'batch' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Batch
          </button>
          <button
            onClick={() => switchTab('results')}
            className={`px-4 py-2 rounded ${activeTab === 'results' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Results
          </button>
          <button
            onClick={() => switchTab('library')}
            className={`px-4 py-2 rounded ${activeTab === 'library' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Library
          </button>
          <button
            onClick={() => switchTab('settings')}
            className={`px-4 py-2 rounded ${activeTab === 'settings' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Settings
          </button>
        </div>
      </div>

      {activeTab === 'batch' && <BatchTab settings={settings} onSelectJob={selectJob} />}
      {activeTab === 'results' && <ResultsTab jobId={jobId} settings={settings} onSelectJob={selectJob} />}
      {activeTab === 'library' && <LibraryTab settings={settings} onSelectJob={selectJob} />}
      {activeTab === 'settings' && <SettingsTab settings={settings} onChange={setSettings} />}
    </div>
  )
}
