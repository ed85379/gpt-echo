/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      animation: {
        'pulse-border': 'pulseBorder 1.5s ease-in-out infinite',
      },
      keyframes: {
        pulseBorder: {
          '0%, 100%': {
            boxShadow: '0 0 0px rgba(168, 85, 247, 0.0)',
          },
          '50%': {
            boxShadow: '0 0 12px 4px rgba(168, 85, 247, 0.5)',
          },
        },
      },
    },
  },
  plugins: [],
};
