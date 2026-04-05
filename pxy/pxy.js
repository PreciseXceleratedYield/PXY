const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80; // change port if needed

// Serve HTML
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// Serve sys folder for CSV
app.use('/sys', express.static(path.join(__dirname, 'sys')));

// WebSocket: stream tmux npxy session (only new lines)
wss.on('connection', (ws) => {
    console.log('Client connected');

    let lastLength = 0;

    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -100 -J -e', (err, stdout, stderr) => {
            if (err) {
                ws.send(`\x1b[31mError: ${stderr || err.message}\x1b[0m\n`);
                return;
            }
            const lines = stdout.split("\n");
            const newLines = lines.slice(lastLength);
            if(newLines.length > 0) ws.send(newLines.join("\n"));
            lastLength = lines.length;
        });
    }, 500); // fetch tmux every 0.5s

    ws.on('close', () => {
        console.log('Client disconnected');
        clearInterval(interval);
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running at http://localhost`);
});
