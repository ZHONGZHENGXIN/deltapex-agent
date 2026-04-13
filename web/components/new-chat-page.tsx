'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Send } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { fetcher } from '@/util/fetcher'
import { useGlobalChatState } from '@/hooks/use-global-chat-state'
import { useGlobalDataCache } from '@/hooks/use-global-data-cache'
import type { Chat } from '@/app/[locale]/types'

interface NewChatPageProps {
  onChatCreated?: (chat: Chat, initialMessage: string) => void
}

export default function NewChatPage({ onChatCreated }: NewChatPageProps) {
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState<string>('')
  const t = useTranslations()

  const { isGloballyLocked, getLockStatusMessage } = useGlobalChatState()
  const { agents, fetchAgents } = useGlobalDataCache()

  useEffect(() => {
    const loadAgents = async () => {
      try {
        const agentsList = await fetchAgents()
        if (agentsList.length > 0 && !selectedAgentId) {
          setSelectedAgentId(agentsList[0].id.toString())
        }
      } catch (error) {
        console.error('Failed to load agents:', error)
      }
    }

    void loadAgents()
  }, [fetchAgents, selectedAgentId])

  const lockStatusMessage = getLockStatusMessage()

  const handleCreateChat = async () => {
    const message = inputValue.trim()
    const agentId = selectedAgentId ? parseInt(selectedAgentId, 10) : null

    if (!agentId || message.length <= 2 || isGloballyLocked) {
      return
    }

    setLoading(true)
    try {
      const response = await fetcher('/chat', {
        method: 'POST',
        auth: true,
        body: JSON.stringify({
          title: message.slice(0, 20),
          agent_id: agentId,
        }),
      })

      const newChat = response as Chat
      setInputValue('')
      onChatCreated?.(newChat, message)
    } catch (error) {
      console.error('Failed to create chat:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full w-full max-w-3xl flex-col justify-center px-6 py-12">
      <div className="mb-6 flex flex-col">
        <span className="mb-3 h-1 w-16 rounded bg-primary" />
        <h1 className="text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
          {t('pages.home.helloWorld')}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground md:text-base">
          Market structure, order flow, and execution ideas in one focused workspace.
        </p>
      </div>

      {isGloballyLocked && lockStatusMessage && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-900/20">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
            <span className="text-sm font-medium text-red-700 dark:text-red-300">
              {lockStatusMessage}
            </span>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-border/80 bg-white p-5 shadow-sm dark:bg-card">
        <textarea
          className={`h-[8rem] max-h-40 min-h-[3rem] w-full resize-none rounded-md border border-border/60 bg-[#fbfdff] px-4 py-3 text-base outline-none transition focus:border-primary/40 dark:bg-background ${
            isGloballyLocked ? 'cursor-not-allowed opacity-50' : ''
          }`}
          placeholder={
            isGloballyLocked
              ? lockStatusMessage || t('chat.limits.globalLockActive')
              : t('chat.newChatPlaceholder')
          }
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          disabled={isGloballyLocked}
          rows={6}
          autoFocus
          onKeyDown={async (event) => {
            if (event.key === 'Enter' && !event.shiftKey && !loading && !isGloballyLocked) {
              event.preventDefault()
              await handleCreateChat()
            }
          }}
        />

        <div className="mt-4 flex items-end gap-3">
          <div className="w-[180px] flex-shrink-0">
            <Select value={selectedAgentId} onValueChange={setSelectedAgentId} disabled={loading}>
              <SelectTrigger className="h-11 w-full border-border/70 bg-white dark:bg-background">
                <SelectValue placeholder={t('chat.selectAgent')} />
              </SelectTrigger>
              <SelectContent>
                {(agents || []).map((agent) => (
                  <SelectItem key={agent.id} value={agent.id.toString()}>
                    <div className="max-w-[140px] truncate" title={agent.name}>
                      {agent.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1" />

          <Button
            className="flex h-11 min-w-11 items-center justify-center rounded-md bg-primary px-4 text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            onClick={handleCreateChat}
            disabled={inputValue.trim().length <= 1 || !selectedAgentId || loading || isGloballyLocked}
          >
            {loading ? (
              <svg className="h-5 w-5 animate-spin text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
              </svg>
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
