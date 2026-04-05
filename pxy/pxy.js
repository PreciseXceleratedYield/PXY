const express = require('express');
const { Client } = require('ssh2');
const path = require('path');
const app = express();

// Serve static files (pxy.html)
app.use(express.static('.'));

// Parse JSON requests
app.use(express.json());

let sshConnections = {};

// Connect to SSH server
app.post('/connect', (req, res) => {
  const { host, username, password } = req.body;

  const conn = new Client();
  conn.on('ready', () => {
    sshConnections[username] = conn;
    res.send('Connected to SSH server!');
  }).on('error', (err) => {
    res.status(500).send('SSH error: ' + err.message);
  }).connect({
    host,
    port: 22,
    username,
    password
  });
});

// Run a command over SSH
app.post('/run', (req, res) => {
  const { username, command } = req.body;
  const conn = sshConnections[username];
  if (!conn) return res.status(400).send('Not connected');

  conn.exec(command, (err, stream) => {
    if (err) return res.send(err.message);

    let output = '';
    stream.on('data', (data) => { output += data.toString(); });
    stream.on('close', () => { res.send(output); });
  });
});

// Bind server to all network interfaces
app.listen(3000, '0.0.0.0', () => console.log('Server running at http://0.0.0.0:3000'));
