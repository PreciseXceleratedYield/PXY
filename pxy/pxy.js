const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const path = require('path');
const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });
const PORT = 80;

/* =========================
   STATIC ROOT
   ========================= */
app.use(express.static(__dirname));

/* =========================
   EXPLICIT JSON ROUTE
   ========================= */
app.get('/pxy.json', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.json'));
});

/* =========================
   MAIN PAGE
   ========================= */
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'pxy.html'));
});

/* =========================
   RUN SHELL SCRIPT AS USER neo
   NOTE: run this once on server first:
   echo 'root ALL=(neo) NOPASSWD: ALL' >> /etc/sudoers
   ========================= */
const ALLOWED_SCRIPTS = [
    'pxyupdate',
    'runpxy.sh',
    'runchrpxy.sh'
    // add more script names here as needed
];

const SCRIPT_DIR = '/root/pxy'; // change if your scripts live elsewhere

app.get('/run/:script', (req, res) => {
    const script = req.params.script;
    if (!ALLOWED_SCRIPTS.includes(script)) {
        return res.status(403).json({ error: 'Script not allowed' });
    }
    const fullPath = path.join(SCRIPT_DIR, script);
    exec(`sudo -u neo ${fullPath}`, (err, stdout, stderr) => {
        if (err) return res.status(500).json({ error: stderr || err.message });
        res.json({ ok: true, output: stdout });
    });
});

/* =========================
   WEBSOCKET
   ========================= */
wss.on('connection', (ws) => {
    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -200 -J -e', (err, stdout) => {
            if (!err && stdout) ws.send(stdout);
        });
    }, 500);
    ws.on('close', () => clearInterval(interval));
});

/* =========================
   START
   ========================= */
server.listen(PORT, '0.0.0.0', () => {
    console.log("Server running on http://localhost");
});
