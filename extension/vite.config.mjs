import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],

  build: {
    outDir: resolve(rootDir, "dist"),
    emptyOutDir: true,

    rollupOptions: {
      input: {
        index: resolve(rootDir, "index.html"),
        content: resolve(rootDir, "src/content/content.js"),
        background: resolve(rootDir, "src/background/background.js")
      },

      output: {
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === "index") {
            return "popup.js";
          }

          if (chunkInfo.name === "content") {
            return "content.js";
          }

          if (chunkInfo.name === "background") {
            return "background.js";
          }

          return "assets/[name].js";
        },

        chunkFileNames: "assets/[name].js",

        assetFileNames: (assetInfo) => {
  if (assetInfo.name === "content.css") {
    return "content.css";
  }

  return "assets/[name][extname]";
}
      }
    }
  }
});