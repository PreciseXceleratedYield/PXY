const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80;

// ⭐ IMPORTANT FIX (THIS IS WHAT YOU'RE MISSING)
app.use(express.static(__dirname));

// Serve frontend
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// WebSocket stream from tmux
wss.on('connection', (ws) => {
    console.log('Client connected');

    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -200 -J -e', (err, stdout, stderr) => {
            if (err) {
                ws.send(`ERROR: ${stderr || err.message}\n`);
                return;
            }
            ws.send(stdout);
        });
    }, 500);

    ws.on('close', () => {
        clearInterval(interval);
        console.log('Client disconnected');
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
