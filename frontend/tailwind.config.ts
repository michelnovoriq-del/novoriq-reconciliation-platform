import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        skybrand: "#0EA5E9",
        skysoft: "#38BDF8",
        deepblue: "#0284C7",
        cream: "#F8F1E5",
        beige: "#EADCC8",
        ink: "#111827",
      },
      boxShadow: {
        soft: "0 18px 60px rgba(17, 24, 39, 0.12)",
        glass: "0 20px 80px rgba(2, 132, 199, 0.22)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-16px)" },
        },
      },
      animation: {
        float: "float 7s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
