import express from "express";
import cors from "cors";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNodeHttpEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";

const app = express();

// ---------------------------------------------------------------------------
// Global Request Logger for GKE Debugging
// ---------------------------------------------------------------------------
app.use((req, res, next) => {
  const start = Date.now();
  res.on("finish", () => {
    const elapsed = Date.now() - start;
    console.log(`[HTTP] ${req.method} ${req.url} - ${res.statusCode} (${elapsed}ms)`);
  });
  next();
});

// ---------------------------------------------------------------------------
// CORS – allow the Vite dev server and any deployed frontend origin
// ---------------------------------------------------------------------------
app.use(
  cors({
    origin: process.env.FRONTEND_URL || "http://localhost:5173",
    credentials: true,
  })
);

// ---------------------------------------------------------------------------
// CopilotKit Runtime
// ---------------------------------------------------------------------------
const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime({
  agents: {
    // "my_agent" must match the `agent` prop on <CopilotKit> in the frontend
    my_agent: new HttpAgent({
      url: process.env.AGENT_URL || "http://localhost:8000/",
    }),
  },
});

// Use app.all (not app.use) so Express does NOT strip the "/copilotkit" prefix
// from req.url. The CopilotKit runtime's internal Hono router is configured with
// basePath "/copilotkit" and needs the full path to match its routes.
const copilotHandler = copilotRuntimeNodeHttpEndpoint({
  endpoint: "/copilotkit",
  runtime,
  serviceAdapter,
});

// eslint-disable-next-line @typescript-eslint/no-misused-promises
app.all("/copilotkit*", (req, res) => copilotHandler(req, res));

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
const PORT = parseInt(process.env.PORT ?? "3001", 10);

app.listen(PORT, () => {
  console.log(`✅  CopilotKit Runtime listening on http://localhost:${PORT}`);
  console.log(`   Agent URL : ${process.env.AGENT_URL || "http://localhost:8000/"}`);
  console.log(`   Frontend  : ${process.env.FRONTEND_URL || "http://localhost:5173"}`);
});
