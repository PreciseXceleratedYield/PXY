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

/* ========================= STATIC ROOT ========================= */ 
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

/* ========================= RUN SCRIPT AS USER pxy ========================= */ 
const ALLOWED_SCRIPTS = [ 
    'pxyupdate', 'pxysqrall', 'pxybuyce', 'pxybuype', 'pxysqrce', 'pxysqrpe' 
]; 
const SCRIPT_DIR = '/home/pxy/pxy'; 

app.post('/run/:script', (req, res) => { 
    const script = req.params.script.trim(); 
    const pwd = (req.body.pwd || '').trim(); 
    
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
        env: { ...process.env, HOME: '/home/pxy', USER: 'pxy', LOGNAME: 'pxy' } 
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
    
    const interval = setInterval(() => { 
        // FIXED: Dynamically target 'pxy' session if it exists, otherwise fall back to current active pane
        const captureCmd = 'tmux has-session -t pxy 2>/dev/null && tmux capture-pane -t pxy -pS -200 -J -e || tmux capture-pane -pS -200 -J -e';
        
        exec(captureCmd, (err, stdout, stderr) => { 
            if (err) { 
                console.error('[WS] tmux exec error:', err.message); 
                return; 
            } 
            if (!stdout) { 
                return; 
            } 
            if (ws.readyState !== WebSocket.OPEN) { 
                return; 
            } 
            ws.send(stdout, (sendErr) => { 
                if (sendErr) console.error('[WS] send error:', sendErr.message); 
            }); 
        }); 
    }, 500); 

    ws.on('close', () => { 
        console.log('[WS] client disconnected'); 
        clearInterval(interval); 
    }); 
    
    ws.on('error', (e) => console.error('[WS] socket error:', e.message)); 
}); 

/* ========================= START ========================= */ 
server.listen(PORT, '0.0.0.0', () => { 
    console.log(`Server running on http://localhost:${PORT}`); 
}).on('error', (err) => {
    if (err.code === 'EACCES') {
        console.error(`[ERROR] Port ${PORT} requires root privileges. Trying port 8080...`);
        server.listen(8080, '0.0.0.0');
    } else {
        console.error('[SERVER ERROR]', err);
    }
});
