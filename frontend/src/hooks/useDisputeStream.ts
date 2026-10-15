import { useEffect, useRef, useState } from 'react'
import { api, type AgentMessage, type Dispute } from '../api'

/* ============================================================
 * Live dispute stream
 * ============================================================
 * Subscribes to the backend SSE stream for a dispute. The backend
 * publishes agent messages and event types ('resolving',
 * 'advocates_done', 'ruling_ready') on a per-dispute Redis channel.
 * We seed the message list with whatever the REST endpoint returns,
 * then append any streamed events that look like agent messages.
 */

export type StreamEvent =
  | { kind: 'agent_message'; message: AgentMessage }
  | { kind: 'event'; type: string; data: Record<string, unknown> }
  | { kind: 'open' }
  | { kind: 'error'; error: string }
  | { kind: 'closed' }

interface UseDisputeStreamResult {
  dispute: Dispute | null
  messages: AgentMessage[]
  events: { type: string; ts: number }[]
  live: boolean
  loading: boolean
  error: string | null
}

export function useDisputeStream(disputeId: number): UseDisputeStreamResult {
  const [dispute, setDispute] = useState<Dispute | null>(null)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const [events, setEvents] = useState<{ type: string; ts: number }[]>([])
  const [live, setLive] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const seenIds = useRef<Set<number>>(new Set())

  /* Initial REST fetch for dispute + already-persisted messages. */
  useEffect(() => {
    let cancelled = false
    Promise.all([api.getDispute(disputeId), api.getMessages(disputeId)])
      .then(([d, msgs]) => {
        if (cancelled) return
        setDispute(d)
        setMessages(msgs)
        for (const m of msgs) seenIds.current.add(m.id)
        // A dispute is "live" while the backend is still deliberating:
        // status is "open" and no ruling has been delivered yet.
        setLive(d.status === 'open')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load dispute.')
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [disputeId])

  /* SSE subscription. We also poll every 4s as a safety net in case
   * SSE never connects (e.g. dev server without redis). */
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') return

    const url = api.streamUrl(disputeId)
    const es = new EventSource(url)

    es.onopen = () => {
      // connected; we'll keep `live` true until we see a ruling-ready event
      setLive((prev) => prev || true)
    }
    es.onerror = () => {
      // The browser will auto-retry. We don't surface this to the UI
      // because the polling fallback below covers it.
    }
    es.onmessage = (ev) => {
      let payload: { type?: string; data?: unknown; id?: number } | null = null
      try {
        payload = JSON.parse(ev.data) as { type?: string; data?: unknown; id?: number }
      } catch {
        return
      }
      if (!payload || !payload.type) return

      const evtType = payload.type
      if (evtType === 'agent_message') {
        const msg = (payload as { data?: AgentMessage }).data
        if (msg && typeof msg === 'object' && typeof msg.id === 'number') {
          if (!seenIds.current.has(msg.id)) {
            seenIds.current.add(msg.id)
            setMessages((prev) =>
              prev.some((m) => m.id === msg.id) ? prev : [...prev, msg],
            )
          }
        }
        return
      }
      // Other event types: 'resolving', 'advocates_done', 'ruling_ready', 'connected'
      setEvents((prev) => [...prev, { type: evtType, ts: Date.now() }])
      if (evtType === 'ruling_ready') {
        setLive(false)
      }
    }

    return () => {
      es.close()
    }
  }, [disputeId])

  /* Polling fallback: every 4s, refetch messages; this catches messages
   * the SSE may have missed (e.g. dev mode without redis) and also lets
   * us update the `live` flag once the ruling arrives. */
  useEffect(() => {
    const id = window.setInterval(() => {
      api
        .getMessages(disputeId)
        .then((msgs) => {
          let added = false
          for (const m of msgs) {
            if (!seenIds.current.has(m.id)) {
              seenIds.current.add(m.id)
              added = true
            }
          }
          if (added) setMessages(msgs)
        })
        .catch(() => undefined)
      api
        .getDispute(disputeId)
        .then((d) => {
          setDispute(d)
          if (d.status !== 'open') setLive(false)
        })
        .catch(() => undefined)
    }, 4000)
    return () => window.clearInterval(id)
  }, [disputeId])

  return { dispute, messages, events, live, loading, error }
}
