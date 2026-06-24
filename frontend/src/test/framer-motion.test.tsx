import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FadeIn, SlideIn, StaggerContainer, StaggerItem } from '../components/AnimatedContainer'

describe('Framer Motion Animations', () => {
  it('renders FadeIn with children', () => {
    render(<FadeIn>Test Content</FadeIn>)
    expect(screen.getByText('Test Content')).toBeTruthy()
  })

  it('renders SlideIn with children', () => {
    render(<SlideIn>Test Content</SlideIn>)
    expect(screen.getByText('Test Content')).toBeTruthy()
  })

  it('renders StaggerContainer with children', () => {
    render(
      <StaggerContainer>
        <StaggerItem>Item 1</StaggerItem>
        <StaggerItem>Item 2</StaggerItem>
      </StaggerContainer>
    )
    expect(screen.getByText('Item 1')).toBeTruthy()
    expect(screen.getByText('Item 2')).toBeTruthy()
  })

  it('applies custom className', () => {
    const { container } = render(<FadeIn className="custom-class">Test</FadeIn>)
    expect(container.querySelector('.custom-class')).toBeTruthy()
  })
})
