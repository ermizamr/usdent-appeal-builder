import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      colors: {
        bone: "#f7f1e8",
        ink: "#1c1b19",
        copper: "#cf5c3b",
        ocean: "#2e6a95",
        parchment: "#fff7eb",
        line: "#e7d9c7",
        haze: "#6f6b64",
      },
      boxShadow: {
        card: "0 18px 40px rgba(28, 27, 25, 0.12)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
