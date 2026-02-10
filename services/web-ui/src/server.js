const express = require("express");
const path = require("path");
const client = require("prom-client");
const bodyParser = require("body-parser");

const app = express();
app.use(bodyParser.json());

// In-memory stores (replace with DB in production)
let incidents = [
  { id: 1, title: "DB latency", severity: "critical", createdAt: "2026-02-08T08:00:00Z", acknowledgedAt: null, resolvedAt: null },
  { id: 2, title: "API errors", severity: "high", createdAt: "2026-02-09T09:30:00Z", acknowledgedAt: "2026-02-09T09:45:00Z", resolvedAt: null },
  { id: 3, title: "Cache miss", severity: "low", createdAt: "2026-02-07T12:00:00Z", acknowledgedAt: "2026-02-07T12:10:00Z", resolvedAt: "2026-02-07T13:00:00Z" }
];

let rotation = ["alice", "bob", "carol"];
let onCallIndex = 0;

// prometheus registry & metrics
const register = new client.Registry();
client.collectDefaultMetrics({ register });

const gaugeIncidentsTotal = new client.Gauge({ name: "app_incidents_total", help: "Total incidents", registers: [register] });
const gaugeIncidentsOpen = new client.Gauge({ name: "app_incidents_open", help: "Open incidents (not resolved)", registers: [register] });
const gaugeMTTASeconds = new client.Gauge({ name: "app_mtta_seconds", help: "Mean time to acknowledge in seconds", registers: [register] });
const gaugeMTTRSeconds = new client.Gauge({ name: "app_mttr_seconds", help: "Mean time to resolve in seconds", registers: [register] });

function updateMetrics() {
  gaugeIncidentsTotal.set(incidents.length);
  gaugeIncidentsOpen.set(incidents.filter(i => !i.resolvedAt).length);

  const mttaList = incidents.filter(i => i.acknowledgedAt).map(i => (new Date(i.acknowledgedAt) - new Date(i.createdAt)) / 1000);
  const mttrList = incidents.filter(i => i.resolvedAt).map(i => {
    const start = i.acknowledgedAt ? new Date(i.acknowledgedAt) : new Date(i.createdAt);
    return (new Date(i.resolvedAt) - start) / 1000;
  });

  const avg = arr => (arr.length ? arr.reduce((a,b)=>a+b,0)/arr.length : 0);
  gaugeMTTASeconds.set(avg(mttaList));
  gaugeMTTRSeconds.set(avg(mttrList));
}
updateMetrics();

// Serve static build if present
const distPath = path.join(__dirname, "..", "dist");
app.use(express.static(distPath));

// API endpoints
app.get("/api/v1/incidents", (req, res) => res.status(200).json({ data: incidents }));

app.post("/api/v1/alerts", (req, res) => {
  const { service, severity, message } = req.body || {};
  if (!service || !severity) return res.status(400).json({ error: "service and severity required" });
  const id = incidents.length ? Math.max(...incidents.map(i=>i.id))+1 : 1;
  const inc = { id, title: `${service}: ${message||"alert"}`, severity, createdAt: new Date().toISOString(), acknowledgedAt: null, resolvedAt: null };
  incidents.push(inc);
  updateMetrics();
  res.status(201).json({ data: inc });
});

app.put("/api/v1/incidents/:id/acknowledge", (req, res) => {
  const id = Number(req.params.id);
  const it = incidents.find(i=>i.id===id);
  if (!it) return res.status(404).json({ error: "not found" });
  if (!it.acknowledgedAt) it.acknowledgedAt = new Date().toISOString();
  updateMetrics();
  res.status(200).json({ data: it });
});

app.put("/api/v1/incidents/:id/resolve", (req, res) => {
  const id = Number(req.params.id);
  const it = incidents.find(i=>i.id===id);
  if (!it) return res.status(404).json({ error: "not found" });
  if (!it.resolvedAt) it.resolvedAt = new Date().toISOString();
  updateMetrics();
  res.status(200).json({ data: it });
});

app.get("/api/v1/oncall/current", (req, res) => res.status(200).json({ current: rotation[onCallIndex], rotation }));

app.post("/api/v1/oncall/rotate", (req, res) => {
  onCallIndex = (onCallIndex + 1) % rotation.length;
  res.status(200).json({ current: rotation[onCallIndex] });
});
app.post("/api/v1/oncall/shuffle", (req, res) => {
  rotation = rotation.sort(() => Math.random()-0.5);
  onCallIndex = 0;
  res.status(200).json({ rotation });
});

// health & metrics
app.get("/health", (req, res) => res.status(200).json({ status: "ok" }));
app.get("/metrics", async (req, res) => {
  try {
    res.set("Content-Type", register.contentType);
    res.end(await register.metrics());
  } catch (err) {
    res.status(500).end(err.message);
  }
});

// SPA fallback
app.get("*", (req, res) => {
  res.sendFile(path.join(distPath, "index.html"), err => { if (err) res.status(404).send("Not Found"); });
});

module.exports = app;

if (require.main === module) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`Server listening on ${port}`));
}
