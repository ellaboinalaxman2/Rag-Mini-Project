import { useEffect, useState } from "react";

function App() {
  const [status, setStatus] = useState("Connecting...");

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/api/health`)
      .then((response) => response.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Backend connection failed"));
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0b1020",
        color: "white",
        display: "grid",
        placeItems: "center",
        fontFamily: "Arial",
      }}
    >
      <div>
        <h1>Intelligent RAG Routing</h1>
        <p>AI Knowledge Platform</p>
        <p>Backend Status: {status}</p>
      </div>
    </div>
  );
}

export default App;
