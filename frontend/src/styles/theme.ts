import { createTheme } from '@mantine/core';

export const theme = createTheme({
  primaryColor: 'indigo',
  fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
  headings: {
    fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  defaultRadius: 'md',
  components: {
    Button: { defaultProps: { radius: 'md' } },
    Card: { defaultProps: { radius: 'md', shadow: 'sm' } },
    TextInput: { defaultProps: { radius: 'md' } },
    Textarea: { defaultProps: { radius: 'md' } },
    Tabs: { defaultProps: { radius: 'md' } },
    Paper: { defaultProps: { radius: 'md' } },
    Modal: { defaultProps: { radius: 'lg', centered: true } },
    NavLink: { defaultProps: { style: { borderRadius: 'var(--mantine-radius-md)' } } },
  },
  colors: {
    brand: [
      '#eef2ff', '#e0e7ff', '#c7d2fe', '#a5b4fc', '#818cf8',
      '#6366f1', '#4f46e5', '#4338ca', '#3730a3', '#312e81',
    ],
  },
});
