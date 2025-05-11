
// chat.js

let socket;
let ttsEnabled = true;  // Toggle for auto-TTS

const API_URL = "http://localhost:5000";

function connectWebSocket() {
    socket = new WebSocket("ws://localhost:5000/ws");

    socket.onopen = () => {
        console.log("WebSocket connected.");
        socket.send(JSON.stringify({ listen_as: "frontend" }));
    };

    socket.onmessage = (event) => {
        console.log("Push received:", event.data);
        showPush(event.data);
    };

    socket.onclose = () => {
        console.log("WebSocket closed. Reconnecting in 5s...");
        setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket error:", err);
        socket.close();
    };
}

function showPush(message) {
    const responseBox = document.getElementById("response-text");
    responseBox.textContent = message;

    if (ttsEnabled) {
        playVoiceStream(message);
    } else {
        playPing();
    }
}

function playPing() {
    const ping = new Audio("/static/ping.mp3");
    ping.play();
}

document.addEventListener("DOMContentLoaded", () => {
    connectWebSocket();

    const form = document.getElementById("chat-form");
    const input = document.getElementById("user-input");
    const responseText = document.getElementById("response-text");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userInput = input.value.trim();
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

            if (ttsEnabled) {
                playVoiceStream(data.response);
            }
        } catch (err) {
            console.error("Error:", err);
            responseText.textContent = "Error reaching Threshold.";
        }

        input.value = "";
    });

    document.getElementById("play-button").addEventListener("click", () => {
        const text = document.getElementById("response-text").innerText;
        playVoiceStream(text);
    });

    document.getElementById("tts-toggle").addEventListener("change", (e) => {
        ttsEnabled = e.target.checked;
    });
});

async function playVoiceStream(text) {
    const response = await fetch(`${API_URL}/api/tts/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
    });

    const mediaSource = new MediaSource();
    const audio = new Audio();
    audio.src = URL.createObjectURL(mediaSource);

    mediaSource.addEventListener("sourceopen", async () => {
        const sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
        const reader = response.body.getReader();
        const queue = [];

        let isAppending = false;

        const appendFromQueue = () => {
            if (queue.length > 0 && !isAppending && !sourceBuffer.updating) {
                isAppending = true;
                sourceBuffer.appendBuffer(queue.shift());
            }
        };

        sourceBuffer.addEventListener("updateend", () => {
            isAppending = false;
            appendFromQueue();
        });

        const pump = () => {
            reader.read().then(({ done, value }) => {
                if (done) {
                    if (!sourceBuffer.updating) mediaSource.endOfStream();
                    return;
                }

                queue.push(value);
                appendFromQueue();
                pump();
            });
        };

        pump();
    });

    // Try to play immediately
    audio.play().catch(err => {
        console.warn("Autoplay failed or tab was inactive:", err);
    });

    // Resume audio if tab becomes active
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && audio.paused) {
            audio.play().catch(err => console.warn("Playback failed after tab resumed:", err));
        }
    });
}
