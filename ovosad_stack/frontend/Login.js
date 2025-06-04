import React, { useState } from "react";
import axios from "axios";

export default function Login({ setToken }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      const res = await axios.post("http://localhost:8000/token", new URLSearchParams({
        username,
        password
      }), {headers: {"Content-Type": "application/x-www-form-urlencoded"}});
      setToken(res.data.access_token);
      localStorage.setItem("token", res.data.access_token);
    } catch {
      setErr("Špatné jméno nebo heslo.");
    }
  };

  return (
    <div className="cvut-card">
      <div className="cvut-header">ČVUT Meteostanice</div>
      <form onSubmit={handleSubmit}>
        <input className="cvut-input" type="text" placeholder="Uživatelské jméno" value={username} onChange={e => setUsername(e.target.value)} />
        <input className="cvut-input" type="password" placeholder="Heslo" value={password} onChange={e => setPassword(e.target.value)} />
        <button className="cvut-btn" type="submit">Přihlásit se</button>
      </form>
      {err && <div style={{color:"red"}}>{err}</div>}
    </div>
  );
}