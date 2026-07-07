import type { MetadataRoute } from "next";

// PWA web app manifest — Next.js auto-serves this at /manifest.webmanifest and
// injects the <link rel="manifest"> tag. Icons live in web/public/icons/.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Kukku — Personal AI",
    short_name: "Kukku",
    description:
      "A private, local-first personal AI for your Mac — answers on Telegram and a web dashboard.",
    start_url: "/",
    display: "standalone",
    background_color: "#0B0B0F",
    theme_color: "#0B0B0F",
    categories: ["productivity", "utilities"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
