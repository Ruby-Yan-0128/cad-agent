const API = "http://127.0.0.1:8000";

document.getElementById("runBtn").addEventListener("click", async () => {
  const filename = document.getElementById("filename").value.trim();
  const code = document.getElementById("code").value.trim();
  const statusEl = document.getElementById("status");
  const previewEl = document.getElementById("preview");
  const downloadEl = document.getElementById("download");

  statusEl.textContent = "Running...";
  previewEl.style.display = "none";
  downloadEl.style.display = "none";

  try {
    let data;
    if (code) {
      const res = await fetch(`${API}/save-and-run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, code }),
      });
      data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
    } else {
      const res = await fetch(`${API}/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script_path: filename }),
      });
      data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
    }

    statusEl.textContent = JSON.stringify(data.run ?? { ok: data.ok }, null, 2);

    if (data.image_url) {
      // Cache-bust query param forces the browser to reload the updated PNG
      previewEl.src = `${data.image_url}?t=${Date.now()}`;
      previewEl.style.display = "block";
    }

    const stem = filename.replace(/\.py$/, "").split(/[\\/]/).pop();
    downloadEl.href = `${API}/exports/${stem}.step`;
    downloadEl.style.display = "inline-block";
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  }
});