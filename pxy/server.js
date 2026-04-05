const express = require('express');
const { Client } = require('ssh2');
const path = require('path');
const app = express();

app.use(express.json());
app.use(express.static('.')); // serve index.html

let sshConnections = {};

app.post('/connect', (req, res) => {
  const { host, username, password } = req.body;
  const conn = new Client();
  conn.on('ready', () => {
    sshConnections[username] = conn;
    res.send('Connected!');
  }).on('error', (err) => {
    res.status(500).send('SSH error: ' + err.message);
  }).connect({
    host,
    port: 22,
    username,
    password
  });
});

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

app.listen(3000, () => console.log('Server running at http://localhost:3000'));
