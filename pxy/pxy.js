const express = require('express'); 
const http = require('http'); 
const WebSocket = require('ws'); 
const { exec } = require('child_process'); 
const path = require('path'); 
const os = require('os'); 

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

/* ========================= EXPLICIT JSON ROUTE ========================= */ 
app.get('/pxy.json', (req, res) => { 
    res.sendFile(path.join(__dirname, 'pxy.json')); 
}); 

/* ========================= MAIN PAGE ========================= */ 
app.get('/', (req, res) => { 
    res.sendFile(path.join(__dirname, 'pxy.html')); 
}); 

/* ========================= RUN SCRIPT AS USER pxy IN pxy/pxy ========================= */ 
const ALLOWED_SCRIPTS = [ 
    'pxyupdate', 'pxysqrall', 'pxybuyce', 'pxybuype', 'pxysqrce', 'pxysqrpe' 
]; 
const SCRIPT_DIR = '/home/pxy/pxy'; 

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
    const cmd = `${runAsUser}bash --login -c "cd /home/pxy/pxy && ${script}"`; 
    
    exec(cmd, { 
        timeout: 30000, 
        cwd: SCRIPT_DIR, 
        env: { 
            PATH: '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/pxy/.local/bin',
            HOME: '/home/pxy', 
            USER: 'pxy', 
            LOGNAME: 'pxy' 
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


/* ========================= WEBSOCKET (FIXED) ========================= */ 
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

        // FIXED: Force captures the exact base terminal pane (pxy:0.0) without empty fallbacks
        const captureCmd = 'tmux has-session -t pxy 2>/dev/null && tmux capture-pane -t pxy:0.0 -pS -200 -J -e';
        
        exec(captureCmd, (err, stdout, stderr) => { 
            isProcessing = false; 

            if (err) { 
                console.error('[WS] tmux exec error:', err.message); 
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
        console.log(`Server running on http://0.0.0:${port}`); 
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

