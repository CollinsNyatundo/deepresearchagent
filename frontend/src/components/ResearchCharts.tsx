import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

const COLORS = ['#3a7bd5', '#00d2ff', '#7c3aed', '#c026d3', '#e11d48', '#f59e0b']

interface LineChartProps {
  data: { name: string; value: number }[]
  title?: string
}

export function ResearchLineChart({ data, title }: LineChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-sm font-medium text-[#c4c6d8] mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="name" stroke="#c4c6d8" fontSize={12} />
          <YAxis stroke="#c4c6d8" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
            }}
          />
          <Line type="monotone" dataKey="value" stroke="#3a7bd5" strokeWidth={2} dot={{ fill: '#3a7bd5' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function ResearchBarChart({ data, title }: LineChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-sm font-medium text-[#c4c6d8] mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="name" stroke="#c4c6d8" fontSize={12} />
          <YAxis stroke="#c4c6d8" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
            }}
          />
          <Bar dataKey="value" fill="#3a7bd5" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

interface PieChartProps {
  data: { name: string; value: number }[]
  title?: string
}

export function ResearchPieChart({ data, title }: PieChartProps) {
  return (
    <div className="w-full">
      {title && <h3 className="text-sm font-medium text-[#c4c6d8] mb-4">{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent ? percent * 100 : 0).toFixed(0)}%`}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
