// pxy.js
const express = require('express');
const path = require('path');
const { Client } = require('ssh2');

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname)));

const sshConnections = {}; // store SSH sessions by username

// Connect to SSH
app.post('/connect', (req, res) => {
    const { host, username, password } = req.body;
    const conn = new Client();

    conn.on('ready', () => {
        sshConnections[username] = conn; // save connection
        res.send('SSH Connection established!');
    }).on('error', (err) => {
        res.send('SSH Connection error: ' + err.message);
    }).connect({
        host,
        port: 22,
        username,
        password
    });
});

// Run commands over SSH
app.post('/run', (req, res) => {
    const { username, command } = req.body;
    const conn = sshConnections[username];

    if (!conn) {
        return res.send('No SSH connection. Connect first.');
    }

    conn.exec(command, (err, stream) => {
        if (err) return res.send('Error: ' + err.message);

        let output = '';
        stream.on('close', () => {
            res.send(output);
        }).on('data', (data) => {
            output += data.toString();
        }).stderr.on('data', (data) => {
            output += data.toString();
        });
    });
});

// Listen on port 80
app.listen(80, '0.0.0.0', () => {
    console.log('Server running at http://0.0.0.0:80');
});
