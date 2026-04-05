const express = require('express');
const path = require('path');
const { Client } = require('ssh2');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

app.use(bodyParser.json());
app.use(express.static(__dirname)); // serve pxy.html and node_modules

// Store SSH connections by username
const sshConnections = {};

app.post('/connect', (req, res) => {
    const { host, username, password } = req.body;

    const conn = new Client();
    conn.on('ready', () => {
        sshConnections[username] = conn;
        res.send('SSH Connection established!\n');
    }).on('error', (err) => {
        res.send('SSH Connection error: ' + err.message + '\n');
    }).connect({
        host,
        port: 22,         // SSH port
        username,
        password
    });
});

app.post('/run', (req, res) => {
    const { username, command } = req.body;
    const conn = sshConnections[username];
    if (!conn) return res.send('No SSH connection established\n');

    conn.exec(command, (err, stream) => {
        if (err) return res.send('Command error: ' + err.message + '\n');

        let output = '';
        stream.on('data', (data) => output += data)
              .on('close', () => res.send(output));
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${PORT}`);
});
