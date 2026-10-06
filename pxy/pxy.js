const express = require('express'); 
const http = require('http'); 
const WebSocket = require('ws'); 
const { exec } = require('child_process'); 
const { execFile } = require('child_process');
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

/* ========================= GLOBAL ERROR HANDLING ========================= */
process.on('uncaughtException', (err) => {
    console.error(`[CRITICAL] Uncaught Exception: ${err.message}`, err.stack);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[CRITICAL] Unhandled Rejection at:', promise, 'reason:', reason);
});

/* ========================= WEB FILES & PARSING ========================= */
app.use('/web', (req, res, next) => {
    if (path.extname(req.path).toLowerCase() !== '.html') {
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

/* ========================= PXYCONFIG — syscnfgpxy.py ========================= */
const PXY_CONFIG_TOOL = path.resolve(__dirname, 'sys/pxyconfigwebpxy.py');
const PXY_CONFIG_PASSWORD = process.env.PXY_CONFIG_PASSWORD || '';

app.use('/api/pxy-config', (req, res, next) => {
    res.set('Cache-Control', 'no-store');
    return next();
});

function authorizePxyConfig(req, res, next) {
    if (!PXY_CONFIG_PASSWORD) {
        return res.status(503).json({
            ok: false,
            error: 'PXY_CONFIG_PASSWORD is not configured; config access is disabled.'
        });
    }
    const supplied = Buffer.from(req.get('x-pxy-config-password') || '');
    const expected = Buffer.from(PXY_CONFIG_PASSWORD);
    if (supplied.length !== expected.length || !crypto.timingSafeEqual(supplied, expected)) {
        return res.status(401).json({ ok: false, error: 'Invalid configuration password.' });
    }
    return next();
}

function runPxyConfigTool(action, input, res) {
    const python = process.env.PXY_CONFIG_PYTHON || 'python3';
    const child = execFile(
        python,
        [PXY_CONFIG_TOOL, action],
        { cwd: __dirname, timeout: 15000, maxBuffer: 1024 * 1024 },
        (error, stdout, stderr) => {
            let result;
            try {
                result = JSON.parse(stdout);
            } catch (parseError) {
                console.error('[PXYCONFIG] helper returned invalid output:', stderr || parseError.message);
                return res.status(500).json({ ok: false, error: 'Configuration helper failed.' });
            }
            if (error && result.ok) {
                console.error('[PXYCONFIG] helper process failed:', stderr || error.message);
                return res.status(500).json({ ok: false, error: 'Configuration helper failed.' });
            }
            return res.status(result.ok ? 200 : 400).json(result);
        }
    );
    if (input !== undefined) {
        child.stdin.end(JSON.stringify(input));
    }
}

app.get('/api/pxy-config', authorizePxyConfig, (req, res) => {
    runPxyConfigTool('read', undefined, res);
});

app.post('/api/pxy-config', authorizePxyConfig, (req, res) => {
    if (!req.body || typeof req.body !== 'object' || Array.isArray(req.body)) {
        return res.status(400).json({ ok: false, error: 'A JSON object is required.' });
    }
    runPxyConfigTool('write', req.body, res);
});

/* ========================= MAIN PAGE ========================= */ 
app.get('/', (req, res) => { 
    res.redirect(302, '/web/webpxy.html');
}); 
app.get('/pxy.html', (req, res) => {
    res.redirect(302, '/web/webpxy.html');
});

/* ========================= DASHBOARD DATA API ========================= */
const WEB_DATA_FILES = new Set([
    'webactpxy', 'webavgpxy', 'webchrtpxy', 'webdashpxy', 'webdaypxy',
    'webpnlpxy', 'webpospxy', 'webrinkopxy'
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
const SCRIPT_DIR = '/home/pxy/pxy'; 
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
    
    const runAsUser = process.env.USER === 'root' ? 'sudo -u pxy ' : '';
    const cmd = `${runAsUser}bash --login -c "cd /home/pxy/pxy && [ -f ~/env/bin/activate ] && source ~/env/bin/activate; export PATH=/home/pxy/pxy:\\$PATH; ${script}"`; 
    
    if (IS_DEBUG) console.log(`[DEBUG] Executing system call command: ${cmd}`);

    exec(cmd, { 
        timeout: 30000, 
        cwd: SCRIPT_DIR, 
        env: { 
            PATH: '/home/pxy/env/bin:/home/pxy/pxy:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/pxy/.local/bin',
            HOME: '/home/pxy', 
            USER: 'pxy', 
            LOGNAME: 'pxy',
            VIRTUAL_ENV: '/home/pxy/env'
        } 
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

        exec(captureCmd, (err, stdout, stderr) => { 
            isProcessing = false; 

            if (err) { 
                if (IS_DEBUG) console.log('[DEBUG] tmux has-session query rejected. Engine offline.');
                if (ws.readyState === WebSocket.OPEN && !hasReportedEngineUnavailable) {
                    ws.send(`[SYSTEM STATUS] Engine console session "${TMUX_SESSION_NAME}" is unavailable. Start the engine from the management menu.`);
                    hasReportedEngineUnavailable = true;
                }
                return; 
            } 

            hasReportedEngineUnavailable = false;
            
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
