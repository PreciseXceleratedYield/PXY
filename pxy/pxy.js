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
   RUN SCRIPT AS USER neo
   Run this ONCE on server before using:
   echo 'root ALL=(neo) NOPASSWD: ALL' >> /etc/sudoers
   ========================= */
const ALLOWED_SCRIPTS = [
    'pxyupdate',
    'runpxy',
    'runchrpxy'
    // add more here as needed
];

const SCRIPT_DIR = '/home/neo/pxy';

app.get('/run/:script', (req, res) => {
    const script = req.params.script.trim();

    console.log(`[RUN] script="${script}" allowed=${ALLOWED_SCRIPTS.includes(script)}`);

    if (!ALLOWED_SCRIPTS.includes(script)) {
        return res.json({ ok: false, error: `Script "${script}" is not allowed` });
    }

    const fullPath = path.join(SCRIPT_DIR, script);

    exec(`sudo -u neo ${fullPath}`, { timeout: 30000 }, (err, stdout, stderr) => {
        console.log(`[RUN] done ok=${!err} stdout="${stdout}" stderr="${stderr}"`);
        res.json({
            ok:     !err,
            output: stdout || '',
            error:  err ? (stderr || err.message || 'Unknown error') : ''
        });
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
