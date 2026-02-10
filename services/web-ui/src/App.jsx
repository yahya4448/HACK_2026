import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [incidents, setIncidents] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [onCall, setOnCall] = useState(null);
  const [error, setError] = useState(null);

  const refreshData = async () => {
    try {
      const [inc, aud, call] = await Promise.all([
        axios.get('http://localhost:8002/api/v1/incidents'),
        axios.get('http://localhost:8002/api/v1/audit'),
        axios.get('http://localhost:8003/api/v1/oncall/current')
      ]);
      setIncidents(inc.data);
      setAuditLogs(aud.data);
      setOnCall(call.data);
      setError(null);
    } catch (err) {
      setError("⚠️ DATABASE DOWN - Connection Lost");
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id, act) => {
    await axios.put(`http://localhost:8002/api/v1/incidents/${id}/${act}`);
    refreshData();
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1000px', margin: 'auto', fontFamily: 'sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #333', paddingBottom: '10px' }}>
        <h1>🛡️ SRE Dashboard</h1>
        {onCall && <div style={{ background: '#00cec9', padding: '10px', borderRadius: '5px' }}>👤 <strong>{onCall.primary.name}</strong> is On-Call</div>}
        <div style={{ display: 'flex', gap: '5px' }}>
          <button onClick={() => axios.post('http://localhost:8002/api/v1/chaos/kill-db')} style={{ background: 'red', color: 'white' }}>💀 KILL DB</button>
          <button onClick={() => axios.post('http://localhost:8002/api/v1/chaos/restore-db')} style={{ background: 'green', color: 'white' }}>♻️ RESTORE</button>
        </div>
      </header>

      {error && <div style={{ background: '#ff7675', padding: '20px', margin: '20px 0', borderRadius: '5px', textAlign: 'center', fontWeight: 'bold' }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', marginTop: '20px' }}>
        <section>
          <h2>Incidents Actifs</h2>
          {incidents.filter(i => i.status !== 'resolved').map(inc => (
            <div key={inc.id} style={{ border: '1px solid #ccc', padding: '15px', marginBottom: '10px', borderRadius: '8px', borderLeft: inc.title.includes('[URGENT]') ? '10px solid red' : '5px solid orange' }}>
              <h3>{inc.title} <small>({inc.service})</small></h3>
              <button onClick={() => handleAction(inc.id, 'acknowledge')}>👀 ACK</button>
              <button onClick={() => handleAction(inc.id, 'resolve')}>✅ RESOLVE</button>
            </div>
          ))}
        </section>

        <section>
          <h3>📜 Audit Trail</h3>
          <div style={{ background: '#2d3436', color: '#55efc4', padding: '10px', fontSize: '12px', height: '400px', overflowY: 'scroll' }}>
            {auditLogs.map(log => (
              <div key={log.id}>[{new Date(log.timestamp).toLocaleTimeString()}] {log.action} - ID:#{log.incident_id}</div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

export default App