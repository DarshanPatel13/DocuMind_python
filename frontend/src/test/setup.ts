// Adds jest-dom matchers (toBeInTheDocument, etc.) and runs after each test.
// RTL auto-cleanup is wired automatically because vitest exposes afterEach
// globally (test.globals = true in vite.config.ts).
import "@testing-library/jest-dom";
