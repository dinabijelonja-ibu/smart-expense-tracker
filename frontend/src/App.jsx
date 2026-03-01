import { useEffect, useMemo, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const PAGES = {
  DASHBOARD: 'dashboard',
  EXPENSES: 'expenses',
  BUDGETS: 'budgets',
  CHAT: 'chat',
}

async function apiRequest(path, { method = 'GET', token, body } = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Backend is unreachable. Run API server or use preview mode.')
  }

  if (response.status === 204) {
    return null
  }

  const payload = await response.json()
  if (!response.ok) {
    if (Array.isArray(payload.detail)) {
      const formatted = payload.detail
        .map((item) => item?.msg)
        .filter(Boolean)
        .join('; ')
      throw new Error(formatted || 'Request failed')
    }
    throw new Error(payload.detail || 'Request failed')
  }

  return payload
}

function AuthView({ onAuthSuccess }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submitAuth(event) {
    event.preventDefault()
    setError('')

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }

    setLoading(true)
    try {
      const endpoint = mode === 'login' ? '/auth/login' : '/auth/register'
      const data = await apiRequest(endpoint, {
        method: 'POST',
        body: { email, password },
      })
      onAuthSuccess(data.access_token)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card auth-card">
      <h1>Smart Expense Tracker</h1>
      <p>{mode === 'login' ? 'Login to continue' : 'Create your account'}</p>
      <form onSubmit={submitAuth} className="stack">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          minLength={8}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Register'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <button
        className="text-button"
        onClick={() => setMode((current) => (current === 'login' ? 'register' : 'login'))}
      >
        {mode === 'login' ? 'Need an account? Register' : 'Already have an account? Login'}
      </button>
    </section>
  )
}

function DashboardView({ token }) {
  const [monthlySummary, setMonthlySummary] = useState(null)
  const [categorySummary, setCategorySummary] = useState([])
  const [forecast, setForecast] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true

    async function loadDashboard() {
      setError('')
      try {
        const [monthly, categories, projection] = await Promise.all([
          apiRequest('/analytics/monthly-summary', { token }),
          apiRequest('/analytics/category-summary', { token }),
          apiRequest('/analytics/forecast', { token }),
        ])

        if (!mounted) {
          return
        }

        setMonthlySummary(monthly)
        setCategorySummary(categories.items)
        setForecast(projection)
      } catch (requestError) {
        if (mounted) {
          setError(requestError.message)
        }
      }
    }

    loadDashboard()
    return () => {
      mounted = false
    }
  }, [token])

  const maxCategory = useMemo(() => {
    if (categorySummary.length === 0) {
      return 1
    }
    return Math.max(...categorySummary.map((item) => item.total_spent), 1)
  }, [categorySummary])

  return (
    <section className="stack-lg">
      <div className="grid stats">
        <article className="card">
          <h3>Total spent</h3>
          <strong>{monthlySummary ? `${monthlySummary.total_spent.toFixed(2)}` : '-'}</strong>
        </article>
        <article className="card">
          <h3>Expenses count</h3>
          <strong>{monthlySummary ? monthlySummary.expense_count : '-'}</strong>
        </article>
        <article className="card">
          <h3>Daily average</h3>
          <strong>{monthlySummary ? `${monthlySummary.average_daily_spend.toFixed(2)}` : '-'}</strong>
        </article>
        <article className="card">
          <h3>Forecast end of month</h3>
          <strong>{forecast ? `${forecast.projected_end_of_month_total.toFixed(2)}` : '-'}</strong>
        </article>
      </div>

      <article className="card">
        <h3>Category chart</h3>
        <div className="stack">
          {categorySummary.map((item) => (
            <div key={item.category} className="chart-row">
              <div className="chart-label">{item.category}</div>
              <div className="chart-bar-wrap">
                <div className="chart-bar" style={{ width: `${(item.total_spent / maxCategory) * 100}%` }} />
              </div>
              <div className="chart-value">{item.total_spent.toFixed(2)}</div>
            </div>
          ))}
          {categorySummary.length === 0 ? <p>No category data yet.</p> : null}
        </div>
      </article>

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}

function ExpensesView({ token }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [form, setForm] = useState({ amount: '', category: '', description: '', date: '' })

  async function loadExpenses() {
    setError('')
    try {
      const data = await apiRequest('/expenses', { token })
      setItems(data.items)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  useEffect(() => {
    loadExpenses()
  }, [])

  async function addExpense(event) {
    event.preventDefault()
    setError('')
    try {
      await apiRequest('/expenses', {
        method: 'POST',
        token,
        body: {
          amount: Number(form.amount),
          category: form.category,
          description: form.description || null,
          date: form.date,
        },
      })
      setForm({ amount: '', category: '', description: '', date: '' })
      await loadExpenses()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function removeExpense(expenseId) {
    setError('')
    try {
      await apiRequest(`/expenses/${expenseId}`, { method: 'DELETE', token })
      await loadExpenses()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <section className="grid two-col">
      <article className="card">
        <h3>Add expense</h3>
        <form className="stack" onSubmit={addExpense}>
          <input
            type="number"
            step="0.01"
            placeholder="Amount"
            value={form.amount}
            onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
            required
          />
          <input
            type="text"
            placeholder="Category"
            value={form.category}
            onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}
            required
          />
          <input
            type="text"
            placeholder="Description"
            value={form.description}
            onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
          />
          <input
            type="date"
            value={form.date}
            onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))}
            required
          />
          <button type="submit">Save expense</button>
        </form>
      </article>

      <article className="card">
        <h3>Expenses list</h3>
        <div className="stack">
          {items.map((expense) => (
            <div className="list-item" key={expense.id}>
              <div>
                <strong>{expense.category}</strong>
                <p>{expense.description || 'No description'}</p>
                <small>{expense.date}</small>
              </div>
              <div className="actions">
                <span>{expense.amount.toFixed(2)}</span>
                <button onClick={() => removeExpense(expense.id)}>Delete</button>
              </div>
            </div>
          ))}
          {items.length === 0 ? <p>No expenses yet.</p> : null}
        </div>
      </article>

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}

function BudgetsView({ token }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [category, setCategory] = useState('')
  const [monthlyLimit, setMonthlyLimit] = useState('')

  async function loadBudgets() {
    setError('')
    try {
      const data = await apiRequest('/budgets', { token })
      setItems(data.items)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  useEffect(() => {
    loadBudgets()
  }, [])

  async function submitBudget(event) {
    event.preventDefault()
    setError('')
    try {
      await apiRequest('/budgets', {
        method: 'POST',
        token,
        body: {
          category,
          monthly_limit: Number(monthlyLimit),
        },
      })
      setCategory('')
      setMonthlyLimit('')
      await loadBudgets()
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <section className="grid two-col">
      <article className="card">
        <h3>Set budget</h3>
        <form onSubmit={submitBudget} className="stack">
          <input
            type="text"
            placeholder="Category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            required
          />
          <input
            type="number"
            step="0.01"
            placeholder="Monthly limit"
            value={monthlyLimit}
            onChange={(event) => setMonthlyLimit(event.target.value)}
            required
          />
          <button type="submit">Save budget</button>
        </form>
      </article>

      <article className="card">
        <h3>Budgets</h3>
        <div className="stack">
          {items.map((budget) => (
            <div className="list-item" key={budget.id}>
              <div>
                <strong>{budget.category}</strong>
                <p>Limit: {budget.monthly_limit.toFixed(2)}</p>
                <small>Spent: {budget.spent_this_month.toFixed(2)}</small>
              </div>
              <div>
                <strong>{budget.usage_percent.toFixed(2)}%</strong>
              </div>
            </div>
          ))}
          {items.length === 0 ? <p>No budgets yet.</p> : null}
        </div>
      </article>

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}

function AIChatView({ token }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function sendMessage(event) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) {
      return
    }

    setLoading(true)
    setError('')
    setMessages((current) => [...current, { role: 'user', content: trimmed }])
    setInput('')

    try {
      const data = await apiRequest('/ai/chat', {
        method: 'POST',
        token,
        body: { message: trimmed },
      })
      setMessages((current) => [...current, { role: 'assistant', content: data.response }])
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card stack-lg">
      <h3>AI Chat</h3>
      <div className="chat-box">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
            <strong>{message.role === 'user' ? 'You' : 'Assistant'}:</strong> {message.content}
          </div>
        ))}
        {messages.length === 0 ? <p>No messages yet.</p> : null}
      </div>
      <form onSubmit={sendMessage} className="stack">
        <textarea
          rows={4}
          placeholder="Ask about your expenses, budgets, and forecasts"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('expense_tracker_token') || '')
  const [activePage, setActivePage] = useState(PAGES.DASHBOARD)

  function handleAuthSuccess(nextToken) {
    localStorage.setItem('expense_tracker_token', nextToken)
    setToken(nextToken)
  }

  function logout() {
    localStorage.removeItem('expense_tracker_token')
    setToken('')
  }

  if (!token) {
    return (
      <main className="app-shell center">
        <AuthView onAuthSuccess={handleAuthSuccess} />
      </main>
    )
  }

  return (
    <main className="app-shell">
      <header className="topbar card">
        <h2>Smart Expense Tracker</h2>
        <nav>
          <button onClick={() => setActivePage(PAGES.DASHBOARD)}>Dashboard</button>
          <button onClick={() => setActivePage(PAGES.EXPENSES)}>Expenses</button>
          <button onClick={() => setActivePage(PAGES.BUDGETS)}>Budgets</button>
          <button onClick={() => setActivePage(PAGES.CHAT)}>AI Chat</button>
        </nav>
        <button onClick={logout}>Logout</button>
      </header>

      {activePage === PAGES.DASHBOARD ? <DashboardView token={token} /> : null}
      {activePage === PAGES.EXPENSES ? <ExpensesView token={token} /> : null}
      {activePage === PAGES.BUDGETS ? <BudgetsView token={token} /> : null}
      {activePage === PAGES.CHAT ? <AIChatView token={token} /> : null}
    </main>
  )
}

export default App
