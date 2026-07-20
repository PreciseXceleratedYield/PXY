const express = require('express'); 
const http = require('http'); 
const WebSocket = require('ws'); 
const { exec } = require('child_process'); 
const path = require('path'); 
const os = require('os'); 
const fs = require('fs'); // ✅ Added to safely handle file stream arrays

const app = express(); 
const server = http.createServer(app); 
const wss = new WebSocket.Server({ server }); 

const PORT = process.env.PORT || 80; 

/* ========================= GLOBAL ERROR HANDLING ========================= */
process.on('uncaughtException', (err) => {
    console.error(`[CRITICAL] Uncaught Exception: ${err.message}`, err.stack);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[CRITICAL] Unhandled Rejection at:', promise, 'reason:', reason);
});

/* ========================= STATIC ROOT & PARSING ========================= */ 
app.use(express.static(__dirname)); 
app.use(express.json()); 

/* ========================= HOSTNAME ROUTE ========================= */ 
app.get('/hostname', (req, res) => { 
    res.json({ hostname: os.hostname() }); 
}); 

/* ========================= PXYCONFIG — READ/SAVE runscrtpxy.py =========================
   pxy.js runs from pxy/ (this file's dir) → down into sys/exe/run/
   runscrtpxy.py = actual private secrets file (may not exist yet)
   runpxy.py     = template file (structure/comments, always kept in repo)
   ========================= */
const CONFIG_FILE_PATH   = path.resolve(__dirname, 'sys/exe/run/runscrtpxy.py');
const TEMPLATE_FILE_PATH = path.resolve(__dirname, 'sys/exe/run/runpxy.py');
const CONFIG_FIELDS = [
    'CONSUMER_KEY', 'CONSUMER_SECRET', 'MOBILE_NUMBER',
    'UCC', 'MPIN', 'TOTP_SECRET_KEY', 'ENVIRONMENT'
];

function extractFields(content) {
    const values = {};
    CONFIG_FIELDS.forEach(key => {
        const re = new RegExp(`^${key}\\s*=\\s*["']([^"']*)["']`, 'm');
        const match = content.match(re);
        values[key] = match ? match[1] : '';
    });
    return values;
}

app.get('/pxyconfig-read', (req, res) => {
    fs.readFile(CONFIG_FILE_PATH, 'utf8', (err, content) => {
        if (!err) {
            return res.json({ ok: true, values: extractFields(content), path: CONFIG_FILE_PATH });
        }
        if (err.code !== 'ENOENT') {
            return res.json({ ok: false, error: `Cannot read config: ${err.message}` });
        }
        // runscrtpxy.py missing — fall back to template for field structure/placeholders
        fs.readFile(TEMPLATE_FILE_PATH, 'utf8', (tErr, tContent) => {
            if (tErr) {
                const values = {};
                CONFIG_FIELDS.forEach(key => { values[key] = ''; });
                return res.json({ ok: true, values, path: CONFIG_FILE_PATH, notFound: true, noTemplate: true });
            }
            res.json({ ok: true, values: extractFields(tContent), path: CONFIG_FILE_PATH, notFound: true });
        });
    });
});

app.post('/pxyconfig-save', (req, res) => {
    const pwd = (req.body.pwd || '').trim();
    if (!pwd) {
        return res.status(400).json({ ok: false, error: 'Password required' });
    }
    const updates = req.body.values || {};

    fs.readFile(CONFIG_FILE_PATH, 'utf8', (err, content) => {
        const isMissing = err && err.code === 'ENOENT';
        if (err && !isMissing) {
            return res.json({ ok: false, error: `Cannot read config: ${err.message}` });
        }

        const proceedWithBase = (base) => {
            let updated = base;
            CONFIG_FIELDS.forEach(key => {
                if (Object.prototype.hasOwnProperty.call(updates, key)) {
                    const val = String(updates[key] ?? '').replace(/"/g, '\\"');
                    const re = new RegExp(`^(${key}\\s*=\\s*)["'][^"']*["']`, 'm');
                    if (re.test(updated)) {
                        updated = updated.replace(re, `$1"${val}"`);
                    } else {
                        updated += `\n${key} = "${val}"\n`;
                    }
                }
            });

            fs.mkdir(path.dirname(CONFIG_FILE_PATH), { recursive: true }, (mkdirErr) => {
                if (mkdirErr) {
                    return res.json({ ok: false, error: `Cannot create directory: ${mkdirErr.message}` });
                }
                fs.writeFile(CONFIG_FILE_PATH, updated, 'utf8', (writeErr) => {
                    if (writeErr) {
                        return res.json({ ok: false, error: `Cannot write config: ${writeErr.message}` });
                    }
                    console.log(`[PXYCONFIG] config file ${isMissing ? 'created from template' : 'updated'} by request`);
                    res.json({ ok: true, created: isMissing });
                });
            });
        };

        if (!isMissing) {
            return proceedWithBase(content);
        }

        // runscrtpxy.py missing — build it from runpxy.py's structure instead of a generic header
        fs.readFile(TEMPLATE_FILE_PATH, 'utf8', (tErr, tContent) => {
            const base = tErr
                ? '# Kotak Neo API Credentials\n# Auto-created by PXYCONFIG editor\n'
                : tContent;
            proceedWithBase(base);
        });
    });
});

/* ========================= EXPLICIT JSON ROUTE ========================= */ 
app.get('/pxy.json', (req, res) => { 
    res.sendFile(path.join(__dirname, 'pxy.json')); 
}); 

/* ========================= MAIN PAGE ========================= */ 
app.get('/', (req, res) => { 
    res.sendFile(path.join(__dirname, 'pxy.html')); 
}); 

/* ========================= RUN SCRIPT WITH PYTHON ENV ACTIVATED ========================= */ 
const ALLOWED_SCRIPTS = [ 
    'pxyupdate', 'pxysqrall', 'pxybuyce', 'pxybuype', 'pxysqrce', 'pxysqrpe' 
]; 
const SCRIPT_DIR = '/home/pxy/pxy'; 
const ENGINE_LOG = '/home/pxy/pxy/engine_boot.log'; // ✅ Registered Engine Log Path

app.post('/run/:script', (req, res) => { 
    const script = req.params.script.trim(); 
    const pwd = (req.body.pwd || '').trim(); 
    
    console.log(`[RUN] script="${script}" allowed=${ALLOWED_SCRIPTS.includes(script)}`); 
    
    if (!ALLOWED_SCRIPTS.includes(script)) {
        return res.status(403).json({ ok: false, error: `Script "${script}" is not allowed` }); 
    } 
    if (!pwd) { 
        return res.status(400).json({ ok: false, error: 'Password required' }); 
    } 
    
    const runAsUser = process.env.USER === 'root' ? 'sudo -u pxy ' : '';
    
    const cmd = `${runAsUser}bash --login -c "cd /home/pxy/pxy && [ -f ~/env/bin/activate ] && source ~/env/bin/activate; export PATH=/home/pxy/pxy:\\$PATH; ${script}"`; 
    
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


/* ========================= WEBSOCKET ========================= */ 
wss.on('connection', (ws) => { 
    console.log('[WS] client connected. total clients:', wss.clients.size); 
    
    let isProcessing = false; 

    const interval = setInterval(() => { 
        if (ws.readyState !== WebSocket.OPEN) {
            clearInterval(interval);
            return;
        }

        if (isProcessing) return; 
        isProcessing = true;

        // FIXED: Checked if the nohup script is running. If yes, read the last 100 log file lines instead of using tmux capture
        const captureCmd = `pgrep -f "sysexepxy.py" >/dev/null && [ -f ${ENGINE_LOG} ] && tail -n 100 ${ENGINE_LOG}`;
        
        exec(captureCmd, (err, stdout, stderr) => { 
            isProcessing = false; 

            if (err) { 
                // If engine process isn't running, send an explicit notice to the dashboard console
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send("[SYSTEM STATUS] Engine offline. Please use option 2 in Console to start background modules.");
                }
                return; 
            } 
            
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
