/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#050814",
          900: "#0b1020",
          800: "#111832",
          700: "#1a2344",
          600: "#233057",
        },
        electric: {
          500: "#3b82f6",
          400: "#60a5fa",
          300: "#93c5fd",
        },
        violet: {
          500: "#8b5cf6",
          400: "#a78bfa",
        },
      },
      boxShadow: {
        glow: "0 0 24px rgba(59, 130, 246, 0.35)",
        "glow-violet": "0 0 24px rgba(139, 92, 246, 0.35)",
      },
      backgroundImage: {
        "grad-hero":
          "radial-gradient(ellipse at top, rgba(59,130,246,0.15), transparent 60%), radial-gradient(ellipse at bottom, rgba(139,92,246,0.15), transparent 60%)",
      },
    },
  },
  plugins: [],
};
