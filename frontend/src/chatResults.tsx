import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { ChatProduct } from './api.ts'

// The products the chat agent most recently found. The chat panel writes them
// here; the <ChatResults> section on the page reads them and shows them as cards.

type ChatResultsState = {
  label: string | null
  products: ChatProduct[]
  query: string
  version: number // goes up on every new set of results (used to scroll + animate)
  expanded: boolean
  show: (products: ChatProduct[], label: string | null, query: string) => void
  setExpanded: (open: boolean) => void
  clear: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [label, setLabel] = useState<string | null>(null)
  const [products, setProducts] = useState<ChatProduct[]>([])
  const [query, setQuery] = useState('')
  const [version, setVersion] = useState(0)
  const [expanded, setExpanded] = useState(true)

  const value: ChatResultsState = {
    label,
    products,
    query,
    version,
    expanded,
    show: (p, l, q) => {
      setProducts(p)
      setLabel(l)
      setQuery(q)
      setExpanded(true)
      setVersion((v) => v + 1)
    },
    setExpanded,
    clear: () => {
      setProducts([])
      setLabel(null)
      setQuery('')
    },
  }

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
