import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

describe('App (logged out)', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the login form when no token is stored', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Smart Expense Tracker' })).toBeInTheDocument()
    expect(screen.getByText('Login to continue')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument()
  })

  it('switches to the register form when the toggle is clicked', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Need an account? Register' }))

    expect(screen.getByText('Create your account')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Register' })).toBeInTheDocument()
  })

  it('does not call the backend before the user submits the form', () => {
    const fetchSpy = vi.spyOn(global, 'fetch')

    render(<App />)

    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
