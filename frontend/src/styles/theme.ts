import { createTheme } from '@mantine/core';

export const theme = createTheme({
  primaryColor: 'mint',
  fontFamily: 'Fira Sans, system-ui, -apple-system, sans-serif',
  fontFamilyMonospace: 'Fira Code, Courier New, monospace',
  headings: {
    fontFamily: 'Fira Sans, system-ui, -apple-system, sans-serif',
    fontWeight: '700',
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
    mint: [
      '#e6fcf5', '#c3fae8', '#96f2d7', '#63e6be', '#38d9a9',
      '#20c997', '#12b886', '#0ca678', '#099268', '#087f5b',
    ],
  },
});
