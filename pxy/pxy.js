const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80; // port 80 requires sudo or setcap

// Serve HTML
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// WebSocket: stream tmux npxy session
wss.on('connection', (ws) => {
    console.log('Client connected');

    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -100 -J -e', (err, stdout, stderr) => {
            if (err) {
                ws.send(`\x1b[31mError: ${stderr || err.message}\x1b[0m\n`);
                return;
            }
            ws.send(stdout);
        });
    }, 500); // update every 0.5s

    ws.on('close', () => {
        console.log('Client disconnected');
        clearInterval(interval);
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
