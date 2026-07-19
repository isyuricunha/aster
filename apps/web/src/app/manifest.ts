import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Aster",
    short_name: "Aster",
    description: "A self-hosted AI chat application",
    start_url: "/",
    display: "standalone",
    background_color: "#060707",
    theme_color: "#0b0c0e",
    icons: [
      {
        src: "/brand/aster-logo.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/brand/aster-maskable.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
  };
}
