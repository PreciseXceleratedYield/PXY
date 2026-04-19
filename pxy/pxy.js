const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80;

/* =========================
   STATIC ROOT (IMPORTANT)
   ========================= */
app.use(express.static(__dirname));

/* =========================
   EXPLICIT JSON ROUTE (FOR DEBUG)
   ========================= */
app.get('/pxy.json', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.json'));
});

/* =========================
   MAIN PAGE
   ========================= */
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

/* =========================
   WEBSOCKET
   ========================= */
wss.on('connection', (ws) => {
    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -200 -J -e', (err, stdout) => {
            if (!err && stdout) ws.send(stdout);
        });
    }, 500);

    ws.on('close', () => clearInterval(interval));
});

/* =========================
   START
   ========================= */
server.listen(PORT, '0.0.0.0', () => {
    console.log("Server running on http://localhost");
});
