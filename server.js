'use strict';

const express = require('express');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const DATA_FILE = path.join(__dirname, 'data.json');
const PUBLIC_DIR = path.join(__dirname, 'public');

const DEFAULT_SETTINGS = {
    pointsWin: 3, pointsDraw: 1, pointsLoss: 0,
    cardOrder: ['browse', 'add', 'edit', 'remove'],
    themeColor: 'indigo', focusTournamentId: 501
};

const DEFAULT_DB = {
    clubs: [{ id: 1, name: 'Geneva Tchoukball Club' }, { id: 2, name: 'Taipei Titans Club' }, { id: 3, name: 'London Rampage Club' }],
    teams: [{ id: 101, name: 'Geneva Dragons', clubId: 1 }, { id: 102, name: 'Taipei Lightning', clubId: 2 }, { id: 103, name: 'London Knights', clubId: 3 }],
    players: [], tournaments: [], matches: []
};

const COLLECTIONS = ['clubs', 'teams', 'players', 'tournaments', 'matches'];
const THEMES = ['indigo', 'emerald', 'amber', 'rose'];
const clone = (v) => JSON.parse(JSON.stringify(v));

function freshState() {
    return { version: 1, settings: clone(DEFAULT_SETTINGS), db: clone(DEFAULT_DB) };
}

let state;

// Safely write to disk (retries if OneDrive has locked the file for a second)
function persist(next) {
    const dataStr = JSON.stringify(next, null, 2);
    let retries = 5;
    while (retries > 0) {
        try {
            fs.writeFileSync(DATA_FILE, dataStr);
            return;
        } catch (err) {
            if (err.code === 'EBUSY' || err.code === 'EPERM') {
                retries--;
                if (retries === 0) throw new Error('File is locked by OneDrive/antivirus.');
                const ms = 100;
                Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms); // wait 100ms
            } else {
                throw err;
            }
        }
    }
}

function loadState() {
    try {
        const parsed = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
        if (parsed && parsed.settings && parsed.db) {
            return {
                version: Number(parsed.version) || 1,
                settings: { ...clone(DEFAULT_SETTINGS), ...parsed.settings },
                db: { ...clone(DEFAULT_DB), ...parsed.db }
            };
        }
    } catch (err) {}
    const fresh = freshState();
    persist(fresh);
    return fresh;
}

function commit() {
    const snapshot = clone(state);
    state.version += 1;
    try {
        persist(state);
    } catch (err) {
        state = snapshot; // Rollback if save fails
        throw new Error('Could not save to data.json. Is OneDrive locking the file?');
    }
}

state = loadState();

function nextId() {
    const used = new Set();
    for (const list of Object.values(state.db)) for (const item of list) used.add(item.id);
    let id = Date.now();
    while (used.has(id)) id += 1;
    return id;
}

function sanitize(value) {
    if (typeof value === 'string') return value.replace(/[<>"]/g, '').slice(0, 200);
    if (Array.isArray(value)) return value.map(sanitize);
    if (value && typeof value === 'object') {
        const out = {};
        for (const [k, v] of Object.entries(value)) out[k] = sanitize(v);
        return out;
    }
    return value;
}

const app = express();
app.use(express.json({ limit: '1mb' }));

app.get('/api/state', (req, res) => res.json(state));
app.get('/api/version', (req, res) => res.json({ version: state.version }));
app.get('/api/backup', (req, res) => {
    res.setHeader('Content-Disposition', `attachment; filename="tchoukball_backup.json"`);
    res.json({ settings: state.settings, database: state.db, timestamp: new Date().toISOString() });
});

app.put('/api/settings', (req, res) => {
    const b = sanitize(req.body || {});
    const s = state.settings;
    const num = (v, f) => (Number.isFinite(Number(v)) ? Number(v) : f);
    s.pointsWin = num(b.pointsWin, s.pointsWin);
    s.pointsDraw = num(b.pointsDraw, s.pointsDraw);
    s.pointsLoss = num(b.pointsLoss, s.pointsLoss);
    if (Array.isArray(b.cardOrder) && b.cardOrder.length === 4) s.cardOrder = b.cardOrder.map(String);
    if (THEMES.includes(b.themeColor)) s.themeColor = b.themeColor;
    try { commit(); res.json(state); } catch (err) { res.status(500).json({ error: err.message }); }
});

app.post('/api/reset', (req, res) => {
    const next = freshState();
    next.version = state.version + 1;
    state = next;
    try { persist(state); res.json(state); } catch (err) { res.status(500).json({ error: err.message }); }
});

for (const coll of COLLECTIONS) {
    app.post(`/api/${coll}`, (req, res) => {
        const body = sanitize(req.body || {});
        const item = { ...body, id: nextId() };
        const snapshot = clone(state.db[coll]);
        state.db[coll].push(item);
        try { commit(); res.status(201).json(state); } 
        catch (err) { state.db[coll] = snapshot; res.status(500).json({ error: err.message }); }
    });

    app.put(`/api/${coll}/:id`, (req, res) => {
        const id = String(req.params.id);
        const list = state.db[coll];
        const index = list.findIndex((x) => String(x.id) === id);
        if (index === -1) return res.status(404).json({ error: 'Not found' });
        const snapshot = clone(list[index]);
        list[index] = { ...list[index], ...sanitize(req.body || {}), id: list[index].id };
        try { commit(); res.json(state); } 
        catch (err) { list[index] = snapshot; res.status(500).json({ error: err.message }); }
    });

    app.delete(`/api/${coll}/:id`, (req, res) => {
        const id = String(req.params.id);
        const before = state.db[coll].length;
        const snapshot = clone(state.db[coll]);
        
        // Convert both to strings so "1" matches 1
        state.db[coll] = state.db[coll].filter((x) => String(x.id) !== id);
        
        if (state.db[coll].length === before) return res.status(404).json({ error: 'Not found' });
        
        try { commit(); res.json(state); } 
        catch (err) { state.db[coll] = snapshot; res.status(500).json({ error: err.message }); }
    });
}

app.use(express.static(PUBLIC_DIR));
app.use((err, req, res, next) => res.status(500).json({ error: err.message }));
app.listen(PORT, () => console.log(`Server running at http://localhost:${PORT}`));