import type { Metadata } from "next";
import "./globals.css";
import "highlight.js/styles/github-dark.css";

export const metadata: Metadata = {
  title: "Kukku — Local-first personal AI",
  description:
    "A private personal AI that lives on your Mac — answers on Telegram and a web dashboard. Semantic file search, OCR, voice, and memory. Nothing leaves home.",
  applicationName: "Kukku",
  appleWebApp: { capable: true, title: "Kukku", statusBarStyle: "black-translucent" },
  // SVG favicon preferred (crisp at any size), PNG fallback for older browsers.
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon-48.png", type: "image/png", sizes: "48x48" },
    ],
    apple: { url: "/apple-icon.png", sizes: "180x180" },
    shortcut: "/favicon-48.png",
  },
};

export const viewport = { themeColor: "#0B0B0F" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
