/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Signature palette: deep ink background option is NOT used (this is
        // an operational dashboard, not a marketing page - operators stare at
        // this for hours, so it's a calm, high-legibility light surface with
        // a single confident accent, not a moody dark hero).
        ink: {
          50: "#f4f6f5",
          100: "#e4e9e7",
          200: "#c8d1cd",
          300: "#a2b0a9",
          400: "#748578",
          500: "#57685c",
          600: "#435047",
          700: "#37413a",
          800: "#2e3631",
          900: "#232a26",
          950: "#141813",
        },
        signal: {
          50: "#eefdf6",
          100: "#d6f9e8",
          200: "#b0f1d3",
          300: "#79e4b8",
          400: "#3fce97",
          500: "#1ab27b",
          600: "#0f9066",
          700: "#0e7354",
          800: "#0f5c45",
          900: "#0d4c3a",
        },
        amber: {
          400: "#f5b942",
          500: "#e8a325",
        },
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        sans: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
