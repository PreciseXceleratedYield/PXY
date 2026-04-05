// pxy.js
const express = require('express');
const path = require('path');
const { Client } = require('ssh2');
const WebSocket = require('ws');

const app = express();

// Serve static files (xterm.js CSS/JS)
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

let sshStream = null;

wss.on('connection', (ws) => {
    console.log('Browser connected via WebSocket');

    if (sshStream) {
        sshStream.on('data', (data) => ws.send(data.toString()));
        sshStream.stderr.on('data', (data) => ws.send(data.toString()));
    }
});

// SSH connection to attach npxy
const conn = new Client();
conn.on('ready', () => {
    console.log('SSH connected, attaching to npxy session');

    conn.exec('screen -r npxy', (err, stream) => {
        if (err) throw err;
        sshStream = stream;

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

        stream.on('close', () => console.log('Screen session closed'));
    });
}).connect({ host, port: 22, username, password });
