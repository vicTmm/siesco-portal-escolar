import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SIESCO · Portal escolar",
    short_name: "SIESCO",
    lang: "pt-BR",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f8f5",
    theme_color: "#17664e",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
