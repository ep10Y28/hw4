// Every call to the FastAPI backend goes through this file.

export type SizeStock = {
  size: string
  quantity: number
}

export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_file_path: string
  image_url: string
  price: number
  total_stock: number
  category: string
  sizes_in_stock: string[]
  inventory?: SizeStock[]
}

// A product as the chat shows it. Built by the backend from the database.
export type ChatProduct = {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  short_description: string
  colors: string[]
  total_stock: number
}

// The /api/chat contract: the agent's reply, plus the products it found
// (built from the database) and a heading for them.
export type ChatReply = {
  reply: string
  products: ChatProduct[]
  results_label: string | null
  message_redacted: string | null // set when the safety guardrail removed something
  notice: string | null
}

export type User = {
  id: number
  first_name: string
  last_name: string
  email: string
}

type AuthResponse = { token: string; user: User }

// The session token from the backend. Only this random token is kept in the
// browser, never the password.
const TOKEN_KEY = 'cc_session'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage blocked: stay logged in for this tab only */
  }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(url, { ...init, headers })
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') message = body.detail
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return getJson<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function signup(data: {
  first_name: string
  last_name: string
  email: string
  password: string
}): Promise<User> {
  const res = await postJson<AuthResponse>('/api/auth/signup', data)
  setToken(res.token)
  return res.user
}

export async function login(email: string, password: string): Promise<User> {
  const res = await postJson<AuthResponse>('/api/auth/login', { email, password })
  setToken(res.token)
  return res.user
}

export async function logout(): Promise<void> {
  try {
    await postJson('/api/auth/logout', {})
  } finally {
    setToken(null)
  }
}

export async function fetchMe(): Promise<User | null> {
  if (!getToken()) return null
  try {
    return await getJson<User>('/api/auth/me')
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) setToken(null)
    return null
  }
}

export function fetchProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<Product> {
  return getJson<Product>(`/api/products/${encodeURIComponent(productId)}`)
}

// Where the shopper is when they send a message, so "this" can be resolved.
export type PageContext = {
  path: string
  product_id: string | null
}

export type ChatTurn = { role: 'user' | 'assistant'; content: string }

// Sends one shopper message to the PydanticAI agent behind /api/chat.
// `guestHistory` is only used when logged out (logged-in history is saved on the server).
export function sendChat(message: string, page: PageContext, guestHistory: ChatTurn[] = []): Promise<ChatReply> {
  return postJson<ChatReply>('/api/chat', { message, page, history: guestHistory.slice(-10) })
}

export type HistoryMessage = {
  role: 'user' | 'assistant'
  content: string
  products: ChatProduct[]
  results_label: string | null
  created_at: string
}

export function fetchChatHistory(): Promise<HistoryMessage[]> {
  return getJson<HistoryMessage[]>('/api/chat/history')
}

export function clearChatHistory(): Promise<{ deleted: number }> {
  return getJson('/api/chat/history', { method: 'DELETE' })
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

export function shortDescription(text: string, max = 90): string {
  if (text.length <= max) return text
  return text.slice(0, text.lastIndexOf(' ', max)).replace(/[,;:]$/, '') + '…'
}
