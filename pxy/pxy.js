const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80; // change if needed

// Serve HTML
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// WebSocket: stream tmux npxy session + CSV for chart
wss.on('connection', (ws) => {
    console.log('Client connected');

    const interval = setInterval(() => {
        // 1️⃣ tmux terminal
        exec('tmux capture-pane -t npxy -pS -100 -J -e', (err, stdout) => {
            if (err) return ws.send(`\x1b[31mError: ${err.message}\x1b[0m\n`);
            ws.send(stdout);
        });

        // 2️⃣ Read CSV for chart
        fs.readFile(path.join(__dirname, 'sys', 'line_data.csv'), 'utf8', (err, data) => {
            if (err) return;
            const lines = data.trim().split('\n').slice(1); // skip header
            const chartData = lines.map(l => {
                const [time, close] = l.split(',');
                return { time: parseInt(time), close: parseFloat(close) };
            });
            ws.send(JSON.stringify({ chart: chartData }));
        });

    }, 500);

    ws.on('close', () => {
        console.log('Client disconnected');
        clearInterval(interval);
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
