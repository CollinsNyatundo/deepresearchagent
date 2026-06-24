import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Toaster, toast } from 'sonner'

describe('Sonner Toast Notifications', () => {
  it('should display a success toast when toast.success is called', async () => {
    const user = userEvent.setup()
    
    function TestComponent() {
      return (
        <div>
          <button onClick={() => toast.success('Note saved')}>Save</button>
          <Toaster position="bottom-right" theme="dark" />
        </div>
      )
    }
    
    render(<TestComponent />)
    
    // Click the save button
    await user.click(screen.getByText('Save'))
    
    // Toast should appear with message
    await waitFor(() => {
      expect(screen.getByText('Note saved')).toBeInTheDocument()
    })
  })

  it('should display an error toast when toast.error is called', async () => {
    const user = userEvent.setup()
    
    function TestComponent() {
      return (
        <div>
          <button onClick={() => toast.error('Failed to save')}>Fail</button>
          <Toaster position="bottom-right" theme="dark" />
        </div>
      )
    }
    
    render(<TestComponent />)
    
    await user.click(screen.getByText('Fail'))
    
    await waitFor(() => {
      expect(screen.getByText('Failed to save')).toBeInTheDocument()
    })
  })

  it('should display a promise toast with loading state', async () => {
    const user = userEvent.setup()
    
    const savePromise = () => new Promise((resolve) => setTimeout(resolve, 100))
    
    function TestComponent() {
      return (
        <div>
          <button onClick={() => {
            toast.promise(savePromise(), {
              loading: 'Saving...',
              success: 'Saved!',
              error: 'Error',
            })
          }}>Save Async</button>
          <Toaster position="bottom-right" theme="dark" />
        </div>
      )
    }
    
    render(<TestComponent />)
    
    await user.click(screen.getByText('Save Async'))
    
    // Should show loading state first
    await waitFor(() => {
      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })
    
    // Then success state
    await waitFor(() => {
      expect(screen.getByText('Saved!')).toBeInTheDocument()
    }, { timeout: 2000 })
  })
})
