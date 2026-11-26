const API = "http://127.0.0.1:8000";
let interactionId = null;

const promptEl = document.getElementById("prompt");
const sendBtn = document.getElementById("sendBtn");
const newChatBtn = document.getElementById("newChatBtn");
const replyEl = document.getElementById("reply");
const previewEl = document.getElementById("preview");
const downloadEl = document.getElementById("download");
const codeDetails = document.getElementById("codeDetails");
const codeBlock = document.getElementById("codeBlock");

newChatBtn.addEventListener("click", () => {
  interactionId = null;
  promptEl.value = "";
  replyEl.textContent = "Started a new session.";
  previewEl.style.display = "none";
  downloadEl.style.display = "none";
  codeDetails.style.display = "none";
});

sendBtn.addEventListener("click", async () => {
  const prompt = promptEl.value.trim();
  if (!prompt) return;

  sendBtn.disabled = true;
  replyEl.textContent = "Generating, running build123d, and visually inspecting...";

  try {
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        previous_interaction_id: interactionId,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));

    interactionId = data.interaction_id;
    replyEl.textContent = data.reply || "Done.";

    if (data.artifact) {
      if (data.artifact.image_url) {
        previewEl.src = `${data.artifact.image_url}?t=${Date.now()}`;
        previewEl.style.display = "block";
      }
      if (data.artifact.step_url) {
        downloadEl.href = data.artifact.step_url;
        downloadEl.textContent = `Download ${data.artifact.filename.replace(/\.py$/, ".step")}`;
        downloadEl.style.display = "inline-block";
      }
      if (data.artifact.code) {
        codeBlock.textContent = data.artifact.code;
        codeDetails.style.display = "block";
      }
    }
  } catch (err) {
    replyEl.textContent = `Error: ${err.message}`;
  } finally {
    sendBtn.disabled = false;
  }
});