const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80;

// =====================
// STATIC FILE ACCESS (IMPORTANT)
// =====================
app.use(express.static(__dirname));
app.use('/sys', express.static(path.join(__dirname, 'sys')));

// =====================
// FRONTEND
// =====================
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// =====================
// TERMINAL STREAM (tmux)
// =====================
wss.on('connection', (ws) => {
    console.log('Client connected');

    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -200 -J -e', (err, stdout) => {
            if (!err && stdout) {
                ws.send(stdout);
            }
        });
    }, 500);

    ws.on('close', () => clearInterval(interval));
});

// =====================
server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
