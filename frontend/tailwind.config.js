import typography from "@tailwindcss/typography";
import animate from "tailwindcss-animate";

/** Design tokens live as CSS variables in src/index.css (light + dark); this maps them. */
const token = (name) => `hsl(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1rem", screens: { "2xl": "1280px" } },
    extend: {
      fontFamily: {
        sans: ['"Inter Variable"', "Inter", "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        mono: ["ui-monospace", '"Cascadia Code"', "Consolas", "monospace"],
      },
      colors: {
        border: token("border"),
        input: token("input"),
        ring: token("ring"),
        background: token("background"),
        foreground: token("foreground"),
        primary: { DEFAULT: token("primary"), foreground: token("primary-foreground") },
        secondary: { DEFAULT: token("secondary"), foreground: token("secondary-foreground") },
        muted: { DEFAULT: token("muted"), foreground: token("muted-foreground") },
        accent: { DEFAULT: token("accent"), foreground: token("accent-foreground") },
        destructive: { DEFAULT: token("destructive"), foreground: token("destructive-foreground") },
        success: { DEFAULT: token("success"), soft: token("success-soft") },
        warning: { DEFAULT: token("warning"), soft: token("warning-soft") },
        card: { DEFAULT: token("card"), foreground: token("card-foreground") },
        popover: { DEFAULT: token("popover"), foreground: token("popover-foreground") },
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        soft: "0 1px 2px hsl(var(--shadow) / 0.06), 0 4px 16px -4px hsl(var(--shadow) / 0.08)",
        lifted: "0 2px 4px hsl(var(--shadow) / 0.06), 0 16px 40px -12px hsl(var(--shadow) / 0.22)",
      },
      keyframes: {
        blink: { "0%, 100%": { opacity: "0.2" }, "50%": { opacity: "1" } },
      },
      animation: {
        blink: "blink 1.1s ease-in-out infinite",
      },
    },
  },
  plugins: [typography, animate],
};
