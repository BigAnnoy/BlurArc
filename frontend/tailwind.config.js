/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#0891b2',
          hover: '#0e7490',
          active: '#0782a3',
          light: '#e0f7fa',
          muted: '#cef0f5',
        },
        page: '#f4f7f9',
        card: '#ffffff',
        border: {
          DEFAULT: '#d8e2e8',
          strong: '#b8c8d4',
        },
        text: {
          primary: '#1a2a3a',
          secondary: '#5a6a7a',
          tertiary: '#8a9aaa',
        },
      },
      fontFamily: {
        sans: ['IBM Plex Sans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        'sidebar': '250px',
        'header': '52px',
      },
      borderRadius: {
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
      },
    },
  },
  plugins: [],
}
