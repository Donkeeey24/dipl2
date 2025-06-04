import React, { useEffect, useState } from "react";
import axios from "axios";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function Dashboard({ token, setToken }) {
  const [deviceEui, setDeviceEui] = useState("");
  const [devices, setDevices] = useState([]);
  const [data, setData] = useState([]);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch allowed devices for selection (admin only endpoint in backend, adjust as needed)
    axios.get("http://localhost:8000/allowed_devices", {
      headers: { Authorization: "Bearer " + token }
    }).then(res => setDevices(res.data)).catch(() => {});
  }, [token]);

  const fetchData = () => {
    if (!deviceEui) return;
    setLoading(true);
    let url = `http://localhost:8000/measurements?device_eui=${deviceEui}`;
    if (from) url += `&from_ts=${from}`;
    if (to) url += `&to_ts=${to}`;
    axios.get(url, {
      headers: { Authorization: "Bearer " + token }
    }).then(res => setData(res.data)).finally(() => setLoading(false));
  };

  return (
    <div className="cvut-card">
      <div className="cvut-header">Dashboard</div>
      <button className="cvut-btn" style={{float:"right"}} onClick={() => { setToken(null); localStorage.removeItem("token"); }}>Odhlásit se</button>
      <div>
        <label>
          Meteostanice:
          <select className="cvut-input" value={deviceEui} onChange={e => setDeviceEui(e.target.value)}>
            <option value="">-- vyber --</option>
            {devices.map(dev => <option key={dev} value={dev}>{dev}</option>)}
          </select>
        </label>
      </div>
      <div style={{marginTop:10}}>
        <label>Od: <input className="cvut-input" type="datetime-local" value={from} onChange={e => setFrom(e.target.value)} /></label>
        <label>Do: <input className="cvut-input" type="datetime-local" value={to} onChange={e => setTo(e.target.value)} /></label>
        <button className="cvut-btn" onClick={fetchData} disabled={loading}>Načíst data</button>
      </div>
      <div style={{height:350, marginTop:20}}>
        {data.length > 0 ?
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="measured_at" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" stroke="#0065a4" />
          </LineChart>
        </ResponsiveContainer> : "Žádná data."}
      </div>
    </div>
  );
}