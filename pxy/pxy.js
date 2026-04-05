// pxy.js
const express = require('express');
const path = require('path');
const { Client } = require('ssh2');
const WebSocket = require('ws');

const app = express();

// Serve xterm.js CSS/JS and static files
app.use('/xterm', express.static(path.join(__dirname, 'node_modules/@xterm/xterm')));
app.use(express.static(path.join(__dirname)));

const username = 'neo';
const password = '1';
const host = 'localhost'; // same VM

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

// HTTP server
const server = app.listen(80, '0.0.0.0', () => {
    console.log('Server running on port 80');
});

// WebSocket server
const wss = new WebSocket.Server({ server });

let tmuxStream = null;

wss.on('connection', (ws) => {
    console.log('Browser connected via WebSocket');

    // Stream existing output if already connected
    if (tmuxStream) {
        tmuxStream.on('data', (data) => ws.send(data.toString()));
        tmuxStream.stderr.on('data', (data) => ws.send(data.toString()));
    }
});

// SSH connect to attach to tmux npxy session
const conn = new Client();
conn.on('ready', () => {
    console.log('SSH connected, attaching to tmux npxy session');

    // Attach or create session, read-only output
    conn.exec(
        "tmux has-session -t npxy 2>/dev/null && tmux attach -t npxy || tmux new -s npxy 'pxyexe'",
        (err, stream) => {
            if (err) throw err;
            tmuxStream = stream;

            stream.on('data', (data) => {
                wss.clients.forEach(client => {
                    if (client.readyState === WebSocket.OPEN) {
                        client.send(data.toString());
                    }
                });
            });

            stream.stderr.on('data', (data) => {
                wss.clients.forEach(client => {
                    if (client.readyState === WebSocket.OPEN) {
                        client.send(data.toString());
                    }
                });
            });

            stream.on('close', () => console.log('tmux session closed'));
        }
    );
}).connect({ host, port: 22, username, password });
