const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = 80;

// Serve HTML
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

wss.on('connection', (ws) => {
    console.log('Client connected');

    // Terminal: tmux updates
    const termInterval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -100 -J -e', (err, stdout) => {
            if (err) return ws.send(`\x1b[31mError: ${err.message}\x1b[0m\n`);
            ws.send(stdout);
        });
    }, 200); // faster updates, terminal smooth

    // Chart: CSV updates
    const chartInterval = setInterval(() => {
        fs.readFile(path.join(__dirname, 'sys', 'line_data.csv'), 'utf8', (err, data) => {
            if (err) return;
            const lines = data.trim().split('\n').slice(1);
            const chartData = lines.map(l => {
                const [time, close] = l.split(',');
                return { time: parseInt(time), close: parseFloat(close) };
            });
            ws.send(JSON.stringify({ chart: chartData }));
        });
    }, 1000); // 1 second chart update

    ws.on('close', () => {
        console.log('Client disconnected');
        clearInterval(termInterval);
        clearInterval(chartInterval);
    });
});

server.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://localhost`);
});
