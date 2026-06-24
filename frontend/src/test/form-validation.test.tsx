import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

const querySchema = z.object({
  query: z.string().min(3, 'Query must be at least 3 characters'),
  depth: z.number().min(1).max(5),
  model: z.string().optional(),
})

type QueryForm = z.infer<typeof querySchema>

function QueryPanelTest() {
  const form = useForm<QueryForm>({
    resolver: zodResolver(querySchema),
    defaultValues: { query: '', depth: 3, model: '' },
  })

  return (
    <form onSubmit={form.handleSubmit(() => {})}>
      <input {...form.register('query')} placeholder="Enter query" />
      {form.formState.errors.query && (
        <span className="error">{form.formState.errors.query.message}</span>
      )}
      <button type="submit">Submit</button>
    </form>
  )
}

describe('QueryPanel Form Validation', () => {
  it('should show error when query is too short', async () => {
    const user = userEvent.setup()
    render(<QueryPanelTest />)

    const input = screen.getByPlaceholderText('Enter query')
    await user.type(input, 'ab')
    await user.click(screen.getByText('Submit'))

    await waitFor(() => {
      expect(screen.getByText('Query must be at least 3 characters')).toBeInTheDocument()
    })
  })

  it('should not show error when query is valid', async () => {
    const user = userEvent.setup()
    render(<QueryPanelTest />)

    const input = screen.getByPlaceholderText('Enter query')
    await user.type(input, 'valid query')
    await user.click(screen.getByText('Submit'))

    await waitFor(() => {
      expect(screen.queryByText('Query must be at least 3 characters')).not.toBeInTheDocument()
    })
  })
})
