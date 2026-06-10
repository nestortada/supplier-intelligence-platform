/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#131315',
        surface: '#1c1b1d',
        panel: '#201f22',
        panelHigh: '#2a2a2c',
        outline: '#494454',
        text: '#e5e1e4',
        muted: '#cbc3d7',
        primary: '#d0bcff',
        primaryStrong: '#a078ff',
        success: '#4edea3',
        warning: '#ffb95f',
        danger: '#ffb4ab',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 24px rgba(208, 188, 255, 0.16)',
        successGlow: '0 0 24px rgba(78, 222, 163, 0.14)',
      },
    },
  },
  plugins: [],
}
