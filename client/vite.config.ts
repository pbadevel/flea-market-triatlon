import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'
import tsconfigPaths from 'vite-tsconfig-paths'

import { tanstackStart } from '@tanstack/react-start/plugin/vite'

import { nitro } from "nitro/vite";
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

const config = defineConfig(({ mode }) => ({
  server: {
    port: 3001,
    allowedHosts: true,
  },
  plugins: [
    devtools(),
    tsconfigPaths({ projects: ['./tsconfig.json'] }),
    tailwindcss(),
    tanstackStart(),
    mode === "production" ? nitro() : null,
    viteReact(),
  ],
  resolve: {
      alias: {
      '@': path.resolve(__dirname, './src'), // Должен указывать на src
    },
  }
}));

export default config;
