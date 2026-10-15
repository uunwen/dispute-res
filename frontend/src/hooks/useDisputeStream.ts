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
 *
 * Lifecycle rules (these are what prevent the Debate view from
 * hammering the backend forever):
 *   - The SSE connection and the polling fallback only run while the
 *     dispute is "live" (status === 'open'). Once a ruling arrives we
 *     tear both down.
 *   - On an SSE failure we close the EventSource (so the browser does
 *     not retry on its own) and reconnect once after a fixed delay,
 *     up to a small number of attempts.
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

/* Seconds between polling fallback ticks. */
const POLL_MS = 4000
/* Delay before reconnecting SSE after a failure (per requirement). */
const RECONNECT_DELAY_MS = 4000
/* Give up on SSE after this many consecutive failures; the polling
 * fallback still catches up messages while the dispute is live. */
const MAX_RECONNECTS = 10

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
        // status is "open" and no ruling has been delivered yet. This
        // gates the SSE + polling effects below.
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

  /* SSE + polling — only while the dispute is live. */
  useEffect(() => {
    if (!live) return

    let disposed = false
    let es: EventSource | null = null
    let reconnectTimer: number | undefined
    let retries = 0

    const teardownStream = () => {
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = undefined
      }
      if (es) {
        es.close()
        es = null
      }
    }

    const connect = () => {
      if (disposed) return
      es = new EventSource(api.streamUrl(disputeId))

      es.onopen = () => {
        // Connected cleanly; reset the failure counter.
        retries = 0
      }

      es.onmessage = (ev) => {
        let payload: { type?: string; data?: unknown } | null = null
        try {
          payload = JSON.parse(ev.data) as { type?: string; data?: unknown }
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

      es.onerror = () => {
        // Stop the browser's native auto-retry so we control the cadence.
        teardownStream()
        if (disposed) return
        retries += 1
        if (retries > MAX_RECONNECTS) return
        reconnectTimer = window.setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    /* Polling fallback: catches messages SSE may have missed (e.g. dev
     * mode without redis) and turns off `live` once the ruling lands. */
    const poll = window.setInterval(() => {
      if (disposed) return
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
          if (disposed) return
          setDispute(d)
          if (d.status !== 'open') setLive(false)
        })
        .catch(() => undefined)
    }, POLL_MS)

    return () => {
      disposed = true
      teardownStream()
      window.clearInterval(poll)
    }
  }, [disputeId, live])

  return { dispute, messages, events, live, loading, error }
}
