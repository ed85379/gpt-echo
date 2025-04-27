document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chat-form");
    const responseText = document.getElementById("response-text");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userInput = document.getElementById("user-input").value.trim();
        if (!userInput) return;

        try {
            const res = await fetch("/chat", {
                method: "POST",
                body: new URLSearchParams({ "prompt": userInput }),
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            });
            const data = await res.json();
            responseText.textContent = data.response || "No response.";
        } catch (err) {
            console.error("Error:", err);
            responseText.textContent = "Error reaching Threshold.";
        }
    });

    document.getElementById("play-button").addEventListener("click", () => {
        playVoice();
    });
});

function playVoice() {
    const text = document.getElementById("response-text").innerText;
    fetch(`${API_URL}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const audio = document.getElementById("echo-audio");
        audio.src = url;
        audio.style.display = "block";
        audio.play();
    })
    .catch(err => console.error("TTS failed", err));
}
