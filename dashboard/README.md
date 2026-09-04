# PolyLLM Gateway — Admin Dashboard

A visual React + TypeScript + Tailwind CSS admin dashboard for monitoring circuit breaker states, latency distributions, request rates, USD token costs, audit logs, and hot-reloading configurations in real time.

## Quick Start

### 1. Install Dependencies

```bash
cd dashboard
npm install
```

### 2. Run Development Server

```bash
npm run dev -- --port 3001
```

The dashboard will open at **http://localhost:3001**.

### 3. Connect to PolyLLM Gateway

- **Gateway Base URL**: `http://localhost:8000`
- **Gateway API Key**: `dev-key` (or matching `GATEWAY_API_KEY` in `.env`)

If the gateway server is offline, the dashboard automatically displays live interactive demo stats.

---

## Features

- **KPI Cards**: Real-time request counts, estimated USD cost, average latency, error rate %, and token totals.
- **Circuit Breaker Status Cards**: Visual status cards for Groq & Gemini providers (CLOSED = green badge, OPEN = red badge, HALF_OPEN = amber badge) with failure count progress bars.
- **Analytics Charts**: Recharts latency histograms and cost breakdown pie charts.
- **Audit Logs Table**: Filterable and searchable table of the last 50 audit entries.
- **Config Hot-Reload**: Interactive `config.yaml` viewer with a "Trigger Hot-Reload" button calling `POST /admin/reload`.
