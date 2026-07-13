/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bourbon: '#D91227', obsidienne: '#0B0C10', surface: '#1A1B22', plume: '#F8F9FA', neutre: '#8B8D98', or: '#D4AF37',
        marine: {
          950: '#0E1B2E',
          900: '#132743',
          800: '#1B355A',
          700: '#254773',
          600: '#345C93',
          100: '#E7ECF3',
          50: '#F3F6FA',
        },
        bronze: {
          600: '#9C7A3C',
          500: '#B08F4F',
          100: '#F1E9D8',
        },
        ink: {
          900: '#1B1E24',
          700: '#3D424C',
          500: '#6B7280',
          300: '#D1D5DB',
          100: '#F4F5F7',
        },
      },
      fontFamily: {
        display: ['"Source Serif 4"', 'Georgia', 'serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
