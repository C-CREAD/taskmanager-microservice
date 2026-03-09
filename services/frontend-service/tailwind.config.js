/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
        body:    ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        forge: {
          bg:       '#0a0a0f',
          surface:  '#111118',
          border:   '#1e1e2e',
          muted:    '#2a2a3d',
          accent:   '#00ff9d',
          'accent-dim': '#00cc7d',
          warn:     '#ff7b3a',
          danger:   '#ff3a5c',
          info:     '#4d9fff',
          text:     '#e8e8f0',
          'text-2': '#9090a8',
          'text-3': '#55556a',
        }
      },
      animation: {
        'fade-in':    'fadeIn 0.4s ease forwards',
        'slide-up':   'slideUp 0.4s cubic-bezier(0.16,1,0.3,1) forwards',
        'slide-in':   'slideIn 0.35s cubic-bezier(0.16,1,0.3,1) forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'glow':       'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideIn: { from: { opacity: 0, transform: 'translateX(-12px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
        glow:    { from: { textShadow: '0 0 10px #00ff9d40' }, to: { textShadow: '0 0 20px #00ff9d80, 0 0 40px #00ff9d30' } },
      },
    },
  },
  plugins: [],
}
