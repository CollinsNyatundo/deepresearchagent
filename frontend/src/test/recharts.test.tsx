import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ResearchLineChart, ResearchBarChart, ResearchPieChart } from '../components/ResearchCharts'

const mockData = [
  { name: 'A', value: 10 },
  { name: 'B', value: 20 },
  { name: 'C', value: 15 },
]

describe('Recharts Data Visualization', () => {
  it('renders line chart with title', () => {
    render(<ResearchLineChart data={mockData} title="Line Chart" />)
    expect(screen.getByText('Line Chart')).toBeTruthy()
  })

  it('renders bar chart with title', () => {
    render(<ResearchBarChart data={mockData} title="Bar Chart" />)
    expect(screen.getByText('Bar Chart')).toBeTruthy()
  })

  it('renders pie chart with title', () => {
    render(<ResearchPieChart data={mockData} title="Pie Chart" />)
    expect(screen.getByText('Pie Chart')).toBeTruthy()
  })

  it('renders chart without title', () => {
    const { container } = render(<ResearchLineChart data={mockData} />)
    expect(container.querySelector('.w-full')).toBeTruthy()
  })
})
