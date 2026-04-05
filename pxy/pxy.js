// pxy.js
const express = require('express');
const path = require('path');
const { Client } = require('ssh2');

const app = express();
app.use(express.json());

// Serve static files (pxy.html and JS/CSS)
app.use(express.static(path.join(__dirname)));

// Endpoint to connect to SSH server
app.post('/connect', (req, res) => {
    const { host, username, password } = req.body;
    const conn = new Client();

    conn
      .on('ready', () => {
        res.send('SSH Connection established!');
        conn.end();
      })
      .on('error', (err) => {
        res.send('SSH Connection error: ' + err.message);
      })
      .connect({
        host,
        port: 22,      // use SSH port
        username,
        password
      });
});

// Endpoint to run commands
app.post('/run', (req, res) => {
    const { username, command } = req.body;
    // In real scenario, map username to SSH connection, here simple demo
    res.send(`Command received: ${command}\n(Not actually executed for security)`);
});

// Listen on port 80 (HTTP)
app.listen(80, '0.0.0.0', () => {
    console.log('Server running at http://0.0.0.0:80');
});
