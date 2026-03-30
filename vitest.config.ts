import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**']
    }
  })
)
