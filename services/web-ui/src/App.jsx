import React, { useEffect, useState } from "react";
import axios from "axios";
import dayjs from "dayjs";

function humanSeconds(s) {
  if (!s) return "-";
  s = Math.round(s);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s/60);
  if (m < 60) return `${m}m ${s%60}s`;
  const h = Math.floor(m/60);
  return `${h}h ${m%60}m`;
}

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [oncall, setOncall] = useState({});
  const [metricsText, setMetricsText] = useState("");

  const load = async () => {
    try {
      const [r1, r2] = await Promise.all([axios.get("/api/v1/incidents"), axios.get("/api/v1/oncall/current")]);
      setIncidents(r1.data.data || []);
      setOncall(r2.data || {});
      const m = await axios.get("/metrics");
      setMetricsText(m.data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, []);

  const ack = async id => { await axios.put(`/api/v1/incidents/${id}/acknowledge`); await load(); };
  const resolveIt = async id => { await axios.put(`/api/v1/incidents/${id}/resolve`); await load(); };
  const rotate = async () => { await axios.post("/api/v1/oncall/rotate"); await load(); };
  const shuffle = async () => { await axios.post("/api/v1/oncall/shuffle"); await load(); };

  const parseMetric = name => {
    const m = metricsText.match(new RegExp(`^${name} (\\d+\\.?\\d*)$`, "m"));
    return m ? Number(m[1]) : null;
  };
  const mtta = parseMetric("app_mtta_seconds");
  const mttr = parseMetric("app_mttr_seconds");

  return (
    <div style={{ padding: 20, fontFamily: "system-ui, sans-serif" }}>
      <h1>Incident Platform</h1>
      <section style={{ marginBottom: 16 }}>
        <strong>On-call:</strong> {oncall.current} <button onClick={rotate}>Next</button> <button onClick={shuffle}>Shuffle</button>
      </section>

      <section style={{ marginBottom: 16 }}>
        <h2>Incidents</h2>
        {incidents.map(it => (
          <div key={it.id} style={{ background: "#fff", padding: 12, marginBottom: 8, borderLeft: it.severity==="critical" ? "4px solid #dc3545":"4px solid #ffc107" }}>
            <div><strong>{it.title}</strong> <small>({it.severity})</small></div>
            <div>Created: {dayjs(it.createdAt).format("YYYY-MM-DD HH:mm")}</div>
            <div>Ack: {it.acknowledgedAt ? dayjs(it.acknowledgedAt).format("YYYY-MM-DD HH:mm") : "-"}</div>
            <div>Resolved: {it.resolvedAt ? dayjs(it.resolvedAt).format("YYYY-MM-DD HH:mm") : "-"}</div>
            <div style={{ marginTop: 8 }}>
              <button onClick={() => ack(it.id)}>Ack</button>
              <button onClick={() => resolveIt(it.id)}>Resolve</button>
            </div>
          </div>
        ))}
      </section>

      <section>
        <h2>Metrics</h2>
        <div>Total incidents: {incidents.length}</div>
        <div>MTTA: {humanSeconds(mtta)}</div>
        <div>MTTR: {humanSeconds(mttr)}</div>
      </section>
    </div>
  );
}