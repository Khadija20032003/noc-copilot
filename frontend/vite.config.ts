import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5173 matches the backend CORS allow-list (backend/app/main.py).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 5173, strictPort: true },
});
