const express = require('express'); 
const http = require('http'); 
const WebSocket = require('ws'); 
const { exec } = require('child_process'); 
const { execFile } = require('child_process');
const { spawn } = require('child_process');
const crypto = require('crypto');
const path = require('path'); 
const os = require('os'); 

// Dynamic execution environment tracing flag
const IS_DEBUG = process.argv.includes('--debug');

const app = express(); 
const server = http.createServer(app); 
const wss = new WebSocket.Server({ server }); 

const PORT = process.env.PORT || 80; 
const WEB_DIR = path.resolve(__dirname, 'web');
const WEB_STATIC_ASSETS = new Set([
    '/pxy-theme.css',
    '/pxy-theme.js',
    '/mbl/manifest.json',
    '/mbl/sw.js'
]);

/* ========================= GLOBAL ERROR HANDLING ========================= */
process.on('uncaughtException', (err) => {
    console.error(`[CRITICAL] Uncaught Exception: ${err.message}`, err.stack);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[CRITICAL] Unhandled Rejection at:', promise, 'reason:', reason);
});

/* ========================= WEB FILES & PARSING ========================= */
app.use('/web', (req, res, next) => {
    if (
        path.extname(req.path).toLowerCase() !== '.html'
        && !WEB_STATIC_ASSETS.has(req.path)
    ) {
        return res.sendStatus(404);
    }
    return next();
}, express.static(WEB_DIR, {
    index: false,
    dotfiles: 'deny',
    setHeaders(res) {
        res.setHeader('X-Content-Type-Options', 'nosniff');
    }
}));
app.use(express.json()); 

/* ========================= HOSTNAME ROUTE ========================= */ 
app.get('/hostname', (req, res) => { 
    res.json({ hostname: os.hostname() }); 
}); 

/* ========================= MAIN PAGE ========================= */ 
app.get('/', (req, res) => { 
    res.redirect(302, '/web/webpxy.html');
}); 
app.get('/pxy.html', (req, res) => {
    res.redirect(302, '/web/webpxy.html');
});

/* ========================= READ-ONLY ENGINE LOG VIEWER ========================= */
app.get('/api/engine-log', (req, res) => {
    res.set('Cache-Control', 'no-store');
    execFile('tmux', ['capture-pane', '-p', '-t', 'pxy-engine', '-S', '-500', '-J'], { timeout: 3000, maxBuffer: 1024 * 1024 }, (error, stdout) => {
        if (error) return res.status(503).json({ ok: false, error: 'Engine console unavailable.' });
        res.json({ ok: true, log: stdout });
    });
});
app.get('/engine-log', (req, res) => {
    res.set('Cache-Control', 'no-store');
    res.type('html').send(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PXY Engine Log</title><style>body{margin:0;background:#111;color:#eee;font:14px monospace}header{position:sticky;top:0;background:#222;padding:12px;display:flex;gap:12px;align-items:center}button{padding:8px 14px;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:14px;user-select:text}#status{margin-left:auto}</style></head><body><header><strong>PXY ENGINE LOG</strong><button id="copy">Copy text</button><button id="refresh">Refresh</button><label><input type="checkbox" id="auto" checked> Auto refresh</label><span id="status"></span></header><pre id="log">Loading...</pre><script>async function load(){try{const r=await fetch('/api/engine-log',{cache:'no-store'});const d=await r.json();document.getElementById('log').textContent=d.ok?d.log:(d.error||'Unavailable');document.getElementById('status').textContent=d.ok?'Live':'Unavailable';}catch(e){document.getElementById('status').textContent='Fetch failed';}}document.getElementById('refresh').onclick=load;document.getElementById('copy').onclick=async()=>{const t=document.getElementById('log').textContent;try{await navigator.clipboard.writeText(t);document.getElementById('status').textContent='Copied';}catch(e){const range=document.createRange();range.selectNodeContents(document.getElementById('log'));getSelection().removeAllRanges();getSelection().addRange(range);document.getElementById('status').textContent='Selected: press Ctrl+C';}};setInterval(()=>{if(document.getElementById('auto').checked&&!getSelection().toString())load();},3000);load();</script></body></html>`);
});

/* ========================= DASHBOARD DATA API ========================= */
const WEB_DATA_FILES = new Set([
    'webactpxy', 'webavgpxy', 'webchrtpxy', 'webdashpxy', 'webdaypxy',
    'webpnlpxy', 'webpospxy', 'webprcpxy', 'webrinkopxy'
]);
app.get('/api/web-data/:name', (req, res) => {
    const name = req.params.name;
    if (!WEB_DATA_FILES.has(name)) {
        return res.sendStatus(404);
    }
    res.set('Cache-Control', 'no-store');
    return res.sendFile(path.join(WEB_DIR, `${name}.json`), (error) => {
        if (error && !res.headersSent) {
            res.status(error.statusCode || 500).json({ ok: false, error: 'Dashboard data is unavailable.' });
        }
    });
});

/* ========================= RUN SCRIPT WITH PYTHON ENV ACTIVATED ========================= */ 
const ALLOWED_SCRIPTS = [ 
    'pxyupdate', 'pxysqrall', 'pxybuyce', 'pxybuype', 'pxysqrce', 'pxysqrpe',
    'pxyldgr'
]; 
const SCRIPT_DIR = path.resolve(__dirname);
const PXY_HOME = process.env.PXY_HOME || '/home/pxy';

function shellQuote(value) {
    return `'${String(value).replace(/'/g, "'\\''")}'`;
}

const ACTION_PASSWORD = '1';

function hasValidActionPassword(value) {
    const supplied = Buffer.from(value, 'utf8');
    const expected = Buffer.from(ACTION_PASSWORD, 'utf8');
    return supplied.length === expected.length && crypto.timingSafeEqual(supplied, expected);
}

app.post('/run/:script', (req, res) => { 
    const script = req.params.script.trim();
    const pwd = typeof req.body?.pwd === 'string' ? req.body.pwd.trim() : '';
    
    console.log(`[RUN] script="${script}" allowed=${ALLOWED_SCRIPTS.includes(script)}`); 
    
    if (!ALLOWED_SCRIPTS.includes(script)) {
        return res.status(403).json({ ok: false, error: `Script "${script}" is not allowed` }); 
    } 
    if (!hasValidActionPassword(pwd)) {
        return res.status(401).json({ ok: false, error: 'Invalid action password.' });
    } 
    
    const runAsRoot = process.env.USER === 'root';
    const runAsUser = runAsRoot ? 'sudo -u pxy ' : '';
    const updateEnvironment = script === 'pxyupdate' ? 'export PXY_UPDATE_FROM_WEB=1; ' : '';
    const scriptCommand = `cd ${shellQuote(SCRIPT_DIR)} && if [ -f "$HOME/env/bin/activate" ]; then source "$HOME/env/bin/activate"; fi; export PATH=${shellQuote(SCRIPT_DIR)}:"$PATH"; ${updateEnvironment}exec ${script}`;
    const executionEnv = {
        PATH: `${PXY_HOME}/env/bin:${SCRIPT_DIR}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PXY_HOME}/.local/bin`,
        HOME: PXY_HOME,
        USER: 'pxy',
        LOGNAME: 'pxy',
        VIRTUAL_ENV: `${PXY_HOME}/env`
    };

    if (script === 'pxyupdate') {
        // Return the real update output. The update script never restarts services.
        const cmd = `${runAsUser}bash --login -c ${shellQuote(scriptCommand.replace('export PXY_UPDATE_FROM_WEB=1; ', ''))}`;
        return exec(cmd, {
            timeout: 120000,
            maxBuffer: 2 * 1024 * 1024,
            cwd: SCRIPT_DIR,
            env: executionEnv
        }, (err, stdout, stderr) => {
            console.log(`[RUN] pxyupdate ok=${!err}`);
            if (!res.headersSent) {
                res.json({
                    ok: !err,
                    output: stdout || '',
                    error: err ? (stderr || err.message || 'Update failed') : (stderr || '')
                });
            }
        });
    }

    const cmd = `${runAsUser}bash --login -c ${shellQuote(scriptCommand)}`;

    if (IS_DEBUG) console.log(`[DEBUG] Executing system call command: ${cmd}`);

    exec(cmd, {
        timeout: 30000,
        cwd: SCRIPT_DIR,
        env: executionEnv
    }, (err, stdout, stderr) => {
        console.log(`[RUN] ok=${!err} out="${stdout}" err="${stderr}"`);
        res.json({
            ok: !err,
            output: stdout || '',
            error: err ? (stderr || err.message || 'Unknown error') : ''
        });
    });
}); 

/* ========================= WEBSOCKET (500-LINE TMUX BUFFER ONLY) =========================
   Session name matches your console script's tmux session: pxy-engine
   -e flag is REQUIRED to preserve ANSI color escape codes — without it,
   capture-pane strips all color and the terminal renders as flat gray.
   ========================= */
const TMUX_SESSION_NAME = 'pxy-engine';

wss.on('connection', (ws) => { 
    console.log('[WS] client connected. total clients:', wss.clients.size); 
    
    let isProcessing = false;
    let hasReportedEngineUnavailable = false;
    let hasReportedPollingTimeout = false;

    const interval = setInterval(() => { 
        if (ws.readyState !== WebSocket.OPEN) {
            clearInterval(interval);
            return;
        }

        if (isProcessing) return; 
        isProcessing = true;

        // Pulls up to 500 lines directly out of active tmux terminal pane memory
        // -e preserves color/attribute escape sequences, -J joins wrapped lines
        const captureCmd = `pane_id=$(tmux list-panes -t ${TMUX_SESSION_NAME} -F '#{pane_id}' 2>/dev/null | head -n 1) && [ -n "$pane_id" ] && tmux capture-pane -pt "$pane_id" -S -500 -e -J`;
        
        if (IS_DEBUG) console.log('[DEBUG] WebSocket polling tmux screen buffer memory...');

        exec(captureCmd, { timeout: 5000 }, (err, stdout, stderr) => {
            isProcessing = false;

            if (err && err.killed) {
                if (ws.readyState === WebSocket.OPEN && !hasReportedPollingTimeout) {
                    ws.send('[SYSTEM STATUS] Terminal polling timed out; retrying.');
                    hasReportedPollingTimeout = true;
                }
                return;
            }

            if (err) {
                hasReportedPollingTimeout = false;
                if (IS_DEBUG) console.log('[DEBUG] tmux has-session query rejected. Engine offline.');
                if (ws.readyState === WebSocket.OPEN && !hasReportedEngineUnavailable) {
                    ws.send(`[SYSTEM STATUS] Engine console session "${TMUX_SESSION_NAME}" is unavailable. Start the engine from the management menu.`);
                    hasReportedEngineUnavailable = true;
                }
                return; 
            } 

            hasReportedEngineUnavailable = false;
            hasReportedPollingTimeout = false;

            if (!stdout) return; 
            
            if (ws.readyState === WebSocket.OPEN) { 
                ws.send(stdout, (sendErr) => { 
                    if (sendErr) console.error('[WS] send error:', sendErr.message); 
                }); 
            } else {
                clearInterval(interval);
            }
        }); 
    }, 500); 

    const cleanup = () => {
        console.log('[WS] client connection cleanup'); 
        clearInterval(interval);
    };

    ws.on('close', cleanup); 
    ws.on('error', (e) => {
        console.error('[WS] socket error:', e.message);
        cleanup();
    }); 
}); 

/* ========================= START ========================= */ 
const listenServer = (port) => {
    server.listen(port, '0.0.0.0', () => { 
        console.log(`Server running on http://0.0.0.0:${port}`); 
        if (IS_DEBUG) console.log('[DEBUG] Server tracking operations with debug flag enabled.');
    });
};

server.on('error', (err) => {
    if (err.code === 'EACCES' && PORT === 80) {
        console.error(`[ERROR] Port ${PORT} requires root privileges (sudo). Falling back to port 8080...`);
        listenServer(8080);
    } else {
        console.error('[SERVER ERROR]', err);
    }
});

listenServer(PORT);
