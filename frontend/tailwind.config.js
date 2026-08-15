/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0f1117",
        panel: "#161922",
        border: "#262a36",
        accent: "#2563eb",
      },
    },
  },
  plugins: [],
};
