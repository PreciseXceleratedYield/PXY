const express    = require('express');
const http       = require('http');
const WebSocket  = require('ws');
const { exec }   = require('child_process');
const path       = require('path');

const app    = express();
const server = http.createServer(app);
const wss    = new WebSocket.Server({ server });
const PORT   = 80;

/* =========================
   STATIC ROOT
   ========================= */
app.use(express.static(__dirname));
app.use(express.json());

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
   ========================= */
const ALLOWED_SCRIPTS = [
    'pxyupdate',
    'pxytkovrbuyce',
    'pxytkovrbuype',
    'pxytkovrsqrce'
    'pxytkovrsqrpe'   
];

const SCRIPT_DIR = '/home/neo/pxy';

app.post('/run/:script', (req, res) => {
    const script = req.params.script.trim();
    const pwd    = (req.body.pwd || '').trim();

    console.log(`[RUN] script="${script}" allowed=${ALLOWED_SCRIPTS.includes(script)}`);

    if (!ALLOWED_SCRIPTS.includes(script)) {
        return res.json({ ok: false, error: `Script "${script}" is not allowed` });
    }
    if (!pwd) {
        return res.json({ ok: false, error: 'Password required' });
    }

    const cmd = `bash ./${script}`;

    exec(cmd, {
        timeout: 30000,
        cwd: SCRIPT_DIR,
        env: { ...process.env, HOME: '/home/neo', USER: 'neo', LOGNAME: 'neo' }
    }, (err, stdout, stderr) => {
        console.log(`[RUN] ok=${!err} out="${stdout}" err="${stderr}"`);
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
    console.log('Server running on http://localhost');
});
