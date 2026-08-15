import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Clean beige/neutral palette
        surface: {
          DEFAULT: '#ffffff',
          hover: '#f8f6f3',
          subtle: '#f5f3f0',
        },
        accent: {
          DEFAULT: 'hsl(28, 44%, 56%)',
          hover: 'hsl(28, 44%, 50%)',
          purple: 'hsl(35, 25%, 65%)',
          emerald: 'hsl(160, 30%, 55%)',
          warm: 'hsl(25, 45%, 60%)',
        },
        status: {
          success: 'hsl(142, 30%, 45%)',
          warning: 'hsl(38, 60%, 50%)',
          error: 'hsl(0, 50%, 55%)',
          info: 'hsl(199, 40%, 50%)',
        },
        ink: {
          DEFAULT: '#2c2a27',
          secondary: '#4a4845',
        },
        muted: {
          DEFAULT: '#6b6762',
          foreground: '#8a857f',
        },
      },
      boxShadow: {
        'glow': '0 0 24px rgba(59, 130, 246, 0.5)',
        'glow-purple': '0 0 24px rgba(168, 85, 247, 0.5)',
        'modern': '0 4px 12px rgba(0, 0, 0, 0.15)',
        'modern-lg': '0 8px 25px rgba(0, 0, 0, 0.25)',
        'modern-xl': '0 20px 40px rgba(0, 0, 0, 0.35)',
      },
      animation: {
        'drift': 'drift 35s ease-in-out infinite alternate',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        drift: {
          '0%': { transform: 'translate3d(0, 0, 0) scale(1) rotate(0deg)' },
          '50%': { transform: 'translate3d(-1%, 1%, 0) scale(1.02) rotate(0.5deg)' },
          '100%': { transform: 'translate3d(-2%, 2%, 0) scale(1.05) rotate(1deg)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};

export default config;

