import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: { ink: "#0b1220", panel: "#111a2b", signal: "#5ee6a8" },
      boxShadow: { panel: "0 24px 80px rgba(0, 0, 0, 0.24)" },
    },
  },
  plugins: [],
};

export default config;
