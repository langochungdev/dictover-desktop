import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Options } from "@wdio/types";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appBinary =
  process.env.WDIO_TAURI_BIN ??
  path.resolve(__dirname, "src-tauri/target/release/dictover_desktop");

export const config: Options.Testrunner = {
  runner: "local",
  specs: ["./tests/e2e/**/*.spec.ts"],
  maxInstances: 1,
  capabilities: [
    {
      platformName: "Windows",
      automationName: "TauriDriver",
      "tauri:app": appBinary,
      "tauri:options": {
        commandTimeout: 30000,
        debug: false,
      },
    },
  ],
  services: [
    [
      "@wdio/tauri-service",
      {
        commandTimeout: 30000,
        debug: false,
        autoInstallTauriDriver: true,
      },
    ],
  ],
  framework: "mocha",
  reporters: ["spec"],
  mochaOpts: {
    ui: "bdd",
    timeout: 120000,
  },
  autoCompileOpts: {
    autoCompile: true,
    tsNodeOpts: {
      transpileOnly: true,
      project: "tsconfig.node.json",
    },
  },
};
