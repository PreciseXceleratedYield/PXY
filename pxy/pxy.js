const express    = require('express');
const http       = require('http');
const WebSocket  = require('ws');
const { exec }   = require('child_process');
const pty        = require('node-pty');
const path       = require('path');
const url        = require('url');

const app    = express();
const server = http.createServer(app);
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
    'pxytkovr',
    'dummy1',
    'dummy2'
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

    const fullPath = path.join(SCRIPT_DIR, script);
    const cmd = `echo '${pwd.replace(/'/g, "'\\''")}' | su -s /bin/bash neo -c "${fullPath}"`;

    exec(cmd, { timeout: 30000 }, (err, stdout, stderr) => {
        console.log(`[RUN] ok=${!err} out="${stdout}" err="${stderr}"`);
        res.json({
            ok:     !err,
            output: stdout || '',
            error:  err ? (stderr || err.message || 'Unknown error') : ''
        });
    });
});

/* =========================
   WEBSOCKET — TMUX (dashboard)
   ========================= */
const wssDash = new WebSocket.Server({ noServer: true });

wssDash.on('connection', (ws) => {
    const interval = setInterval(() => {
        exec('tmux capture-pane -t npxy -pS -200 -J -e', (err, stdout) => {
            if (!err && stdout) ws.send(stdout);
        });
    }, 500);
    ws.on('close', () => clearInterval(interval));
});

/* =========================
   WEBSOCKET — PTY (terminal page)
   ========================= */
const wssPty = new WebSocket.Server({ noServer: true });

wssPty.on('connection', (ws, req) => {
    const params = new url.URL(req.url, `http://${req.headers.host}`).searchParams;
    const pwd    = params.get('pwd') || '';

    console.log(`[PTY] new connection, user=neo`);

    // spawn shell as neo using su
    const shell = pty.spawn('su', ['-s', '/bin/bash', 'neo'], {
        name: 'xterm-color',
        cols: 80, rows: 24,
        cwd:  '/home/neo',
        env:  process.env
    });

    // send password automatically to su prompt
    setTimeout(() => shell.write(pwd + '\n'), 300);

    // stream output to browser
    shell.onData(data => {
        if (ws.readyState === WebSocket.OPEN) ws.send(data);
    });

    // receive input/resize from browser
    ws.on('message', raw => {
        try {
            const msg = JSON.parse(raw);
            if (msg.type === 'input')  shell.write(msg.data);
            if (msg.type === 'resize') shell.resize(msg.cols, msg.rows);
        } catch {
            shell.write(raw);
        }
    });

    shell.onExit(() => {
        console.log(`[PTY] shell exited`);
        if (ws.readyState === WebSocket.OPEN) ws.close();
    });

    ws.on('close', () => {
        console.log(`[PTY] ws closed`);
        try { shell.kill(); } catch {}
    });
});

/* =========================
   ROUTE WS UPGRADES
   ========================= */
server.on('upgrade', (req, socket, head) => {
    const pathname = url.parse(req.url).pathname;
    if (pathname === '/pty') {
        wssPty.handleUpgrade(req, socket, head, ws => wssPty.emit('connection', ws, req));
    } else {
        wssDash.handleUpgrade(req, socket, head, ws => wssDash.emit('connection', ws, req));
    }
});

/* =========================
   START
   ========================= */
server.listen(PORT, '0.0.0.0', () => {
    console.log('Server running on http://localhost');
});
