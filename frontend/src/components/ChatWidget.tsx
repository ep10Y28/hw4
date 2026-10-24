import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router-dom'
import type { ChatProduct, ChatTurn, PageContext } from '../api.ts'
import { clearChatHistory, fetchChatHistory, sendChat } from '../api.ts'
import { useAuth } from '../auth.tsx'
import { useChatResults } from '../chatResults.tsx'

type Shown = { products: ChatProduct[]; label: string }
type Message = {
  role: 'user' | 'assistant'
  content: string
  shown?: Shown
  greeting?: boolean
  notice?: boolean // safety notice from the guardrail (not sent back as history)
}

function greeting(firstName?: string, returning = false): Message {
  let content = "Hey there. Looking for something specific? Ask me about a size, a color, or what's in stock."
  if (firstName && returning) content = `Welcome back, ${firstName}. Your earlier chat is above. Pick up where you left off, or ask me something new.`
  else if (firstName) content = `Hey ${firstName}. Looking for something specific? Ask me about a size, a color, or what's in stock.`
  return { role: 'assistant', content, greeting: true }
}

// Problem 9: one-tap starter questions. On a product page they're about "this" item.
const GENERAL_CHIPS = [
  'What hoodies do you have?',
  'Anything under $40?',
  "What's in stock in medium?",
  'Show me Harvard-Yale gear',
  'Gray quarter-zips',
]
const PRODUCT_CHIPS = [
  'Is this in stock in medium?',
  'What colors does this come in?',
  'How much is this?',
  'Show me similar items in stock',
]

// "/products/basic-hoodie-big-yale" -> that product_id. Everything else -> null.
function pageContext(pathname: string): PageContext {
  const m = pathname.match(/^\/products\/([^/]+)\/?$/)
  return { path: pathname, product_id: m ? decodeURIComponent(m[1]) : null }
}

export default function ChatWidget() {
  const { user, ready } = useAuth()
  const results = useChatResults()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  // Logged in: reload saved history from the database. Guest (or after logout): start fresh.
  useEffect(() => {
    if (!ready) return
    let cancelled = false
    if (!user) {
      setMessages([greeting()])
      return
    }
    fetchChatHistory()
      .then((saved) => {
        if (cancelled) return
        const restored: Message[] = saved.map((m) => ({
          role: m.role,
          content: m.content,
          shown:
            m.products.length > 0 ? { products: m.products, label: m.results_label ?? 'From your chat' } : undefined,
        }))
        // Old messages first, then the welcome-back line as the newest message.
        setMessages(restored.length > 0 ? [...restored, greeting(user.first_name, true)] : [greeting(user.first_name)])
      })
      .catch(() => {
        if (!cancelled) setMessages([greeting(user.first_name)])
      })
    return () => {
      cancelled = true
    }
  }, [ready, user?.id, user?.first_name]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages, open])

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || sending) return
    // Guests: send the last few turns so the agent can follow the conversation.
    const guestHistory: ChatTurn[] = user
      ? []
      : messages.filter((m) => !m.greeting && !m.notice).map((m) => ({ role: m.role, content: m.content }))
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const res = await sendChat(text, pageContext(location.pathname), guestHistory)
      const label = res.results_label ?? 'From your chat'
      // Show cards on the page, unless the only result is the product already on screen.
      const onPage = pageContext(location.pathname).product_id
      const justThisProduct = res.products.length === 1 && res.products[0].product_id === onPage
      if (res.products.length > 0 && !justThisProduct) results.show(res.products, label, res.message_redacted ?? text)
      setMessages((m) => {
        const next = [...m]
        // Safety guardrail: show the shopper what was actually sent (card number etc. removed).
        if (res.message_redacted) {
          for (let i = next.length - 1; i >= 0; i--) {
            if (next[i].role === 'user') {
              next[i] = { ...next[i], content: res.message_redacted }
              break
            }
          }
        }
        if (res.notice) next.push({ role: 'assistant', content: `🔒 ${res.notice}`, notice: true })
        next.push({
          role: 'assistant',
          content: res.reply,
          shown: res.products.length > 0 ? { products: res.products, label } : undefined,
        })
        return next
      })
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: "I can't reach the shop right now. Please try again in a minute." },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  async function handleClear() {
    try {
      await clearChatHistory()
    } finally {
      setMessages([greeting(user?.first_name)])
      results.clear()
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Chat with Campus Customs">
          <header className="chat-header">
            <div>
              <strong>Ask the counter</strong>
              <span>{user ? 'Your chat is saved to your account' : 'Log in to save this chat'}</span>
            </div>
            <div className="chat-header-actions">
              {user && messages.length > 1 && (
                <button className="chat-clear" onClick={handleClear}>
                  Clear history
                </button>
              )}
              <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
                ×
              </button>
            </div>
          </header>
          <div className="chat-messages" ref={listRef}>
            {messages.map((m, i) => (
              <div key={i} className={`turn turn-${m.role}`}>
                <div className={`bubble bubble-${m.role} ${m.notice ? 'bubble-notice' : ''}`}>{m.content}</div>
                {m.shown && (
                  <button
                    className="chat-shown"
                    onClick={() => results.show(m.shown!.products, m.shown!.label, '')}
                    title="Show these on the page"
                  >
                    ↖ {m.shown.products.length} {m.shown.products.length === 1 ? 'item' : 'items'}:{' '}
                    {m.shown.label}
                  </button>
                )}
              </div>
            ))}
            {sending && <div className="bubble bubble-assistant bubble-typing">Typing…</div>}
          </div>
          <div className="chat-chips" aria-label="Suggested questions">
            {(pageContext(location.pathname).product_id ? PRODUCT_CHIPS : GENERAL_CHIPS).map((chip) => (
              <button key={chip} className="chat-chip" disabled={sending} onClick={() => void send(chip)}>
                {chip}
              </button>
            ))}
          </div>
          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                pageContext(location.pathname).product_id
                  ? 'Ask about this item: sizes, colors, stock…'
                  : 'Do you have a navy hoodie in medium?'
              }
              aria-label="Message"
            />
            <button type="submit" disabled={sending || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        className={`chat-toggle ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Ask the counter: chat with Campus Customs'}
      >
        <span className="patch-ring" aria-hidden="true" />
        <span className="patch-label">{open ? 'Close' : 'Ask the counter'}</span>
      </button>
    </div>
  )
}
