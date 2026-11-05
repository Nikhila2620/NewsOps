import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg:       'var(--bg)',
        surface:  'var(--surface)',
        surface2: 'var(--surface2)',
        ink:      'var(--ink)',
        mute:     'var(--mute)',
        line:     'var(--line)',
        accent:   'var(--accent)',
        scout:    'var(--scout)',
        analyst:  'var(--analyst)',
        editor:   'var(--editor)',
      },
      fontFamily: {
        heading: ['Bricolage Grotesque', 'system-ui', 'sans-serif'],
        body:    ['Instrument Sans', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Cascadia Code', 'monospace'],
      },
      borderRadius: {
        card: '16px',
        sm:   '8px',
      },
    },
  },
  plugins: [],
}

export default config
