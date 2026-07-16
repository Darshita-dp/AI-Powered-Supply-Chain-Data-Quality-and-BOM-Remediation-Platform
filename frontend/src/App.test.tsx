import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App shell', () => {
  it('renders the platform title', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /BOM Guardian AI/i })).toBeInTheDocument()
  })
})
