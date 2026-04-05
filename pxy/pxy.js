const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80; // change if needed
const CSV_FILE = path.join(__dirname, 'sys', 'line_data.csv');

// ---------------- Serve HTML ----------------
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// ---------------- WebSocket for terminal ----------------
wss.on('connection', (ws) => {
    console.log('Client connected');

    // Terminal output interval
    const interval = setInterval(() => {
        // Try to capture tmux npxy session
        exec('tmux capture-pane -t npxy -pS -100 -J -e', (err, stdout, stderr) => {
            if (err) {
                // fallback output if tmux not running
                ws.send('\x1b[32mConnected. Terminal ready...\x1b[0m\n');
                return;
            }
            ws.send(stdout || '\x1b[32mConnected. Terminal ready...\x1b[0m\n');
        });
    }, 500);

    ws.on('close', () => {
        console.log('Client disconnected');
        clearInterval(interval);
    });
});

// ---------------- Serve CSV ----------------
app.get('/line_data.csv', (req, res) => {
    fs.readFile(CSV_FILE, 'utf8', (err, data) => {
        if (err) {
            return res.status(500).send('Error reading CSV');
        }
        res.header('Content-Type', 'text/csv');
        res.send(data);
    });
});

// ---------------- Start server ----------------
server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
