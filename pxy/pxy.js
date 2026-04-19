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
   IMPORTANT: STATIC ROUTES
   ========================= */

// serve frontend files (pxy.html, js, etc.)
app.use(express.static(__dirname));

// serve /sys folder correctly (THIS FIXES YOUR ISSUE)
app.use('/sys', express.static(path.join(__dirname, 'sys')));

/* =========================
   MAIN PAGE
   ========================= */
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

/* =========================
   WEBSOCKET STREAM (tmux)
   ========================= */
wss.on('connection', (ws) => {
    console.log('Client connected');

    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -200 -J -e', (err, stdout) => {
            if (!err && stdout) {
                ws.send(stdout);
            }
        });
    }, 500);

    ws.on('close', () => {
        clearInterval(interval);
        console.log('Client disconnected');
    });
});

/* =========================
   START SERVER
   ========================= */
server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
