// =====================================================================
//  Tchoukball Stats — client
//  All data lives on the server; this file keeps a read-only mirror of
//  it and re-syncs whenever the server's version number changes.
// =====================================================================

const appSettings = {
    pointsWin: 3, pointsDraw: 1, pointsLoss: 0,
    cardOrder: ['browse', 'add', 'edit', 'remove'],
    themeColor: 'indigo'
};

const VALID_THEMES = ['indigo', 'emerald', 'amber', 'rose'];

let db = { clubs: [], teams: [], players: [], tournaments: [], matches: [] };
let serverVersion = 0;
let currentView = null;

let activePlayerId = null;
let modalDirty = false;            // N11 — tracks unsaved edits in the open form
let afterAddTeamReturnTo = null;   // N13 — where to return after "Add a team" from a match form
let settingsSnapshot = '';         // N6  — JSON of appSettings when Settings opened
let editFormSnapshot = '';         // N7  — JSON of the record when an Edit form opened
let forceStateRefresh = false;     // N9  — re-fetch state on next poll (used after 204s)
let statusTimer = null;
let polling = false;

const PLURAL = {
    player: 'players', team: 'teams', club: 'clubs',
    tournament: 'tournaments', match: 'matches'
};

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// N1 — type-tolerant id comparison. String ids, numeric ids, and mixed
// types all resolve consistently. Replaces every strict `.id === target`.
function idEq(a, b) {
    if (a == null || b == null) return false;
    return String(a) === String(b);
}

function toDateInput(value) {
    if (!value) return '';
    const s = String(value);
    return /^\d{4}-\d{2}-\d{2}/.test(s) ? s.slice(0, 10) : '';
}

function toIdOrNull(value) {
    const n = parseInt(value, 10);
    return Number.isFinite(n) ? n : null;
}

// N1/N2 — build <option> list for a reference select, comparing ids
// type-tolerantly so string/number mismatches don't produce false
// "deleted" warnings.
function refOptions(items, selectedId, noneLabel, missingLabel) {
    const hasSelected = selectedId != null;
    const found = hasSelected ? items.find((x) => idEq(x.id, selectedId)) : null;
    const missing = hasSelected && !found;

    const parts = [];
    if (missing) {
        parts.push(`<option value="__missing__" selected>⚠ ${escapeHtml(missingLabel || 'previous selection')} was deleted — pick a replacement</option>`);
    }
    if (noneLabel !== null) {
        parts.push(`<option value="">${escapeHtml(noneLabel)}</option>`);
    }
    items.forEach((x) => {
        const isSel = !missing && idEq(x.id, selectedId);
        parts.push(`<option value="${escapeHtml(x.id)}"${isSel ? ' selected' : ''}>${escapeHtml(x.name || '—')}</option>`);
    });
    return parts.join('');
}

// N8 — resolve a <select> to id|null, rejecting the missing-sentinel and
// (when `collection` given) verifying the id still exists in `db`.
function resolveReferenceSelect(elementId, label, collection) {
    const raw = document.getElementById(elementId).value;
    if (raw === '__missing__') {
        setStatus(`Please pick a valid ${label} (or choose an explicit replacement).`);
        return undefined;
    }
    const id = toIdOrNull(raw);
    if (id === null) return null;
    if (collection && !collection.some((x) => idEq(x.id, id))) {
        setStatus(`The selected ${label} no longer exists — pick a current one.`);
        return undefined;
    }
    return id;
}

// ---------------------------------------------------------------------
// Icons & header stats
// ---------------------------------------------------------------------
const ICON = {
    browse: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>',
    plus:   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><path d="M12 5v14M5 12h14"/></svg>',
    edit:   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/></svg>',
    trash:  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>',
    settings:'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    user:   '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:18px;height:18px"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
};

function setModalTitle(text, iconKey, tint = 'indigo') {
    const el = document.getElementById('modal-title');
    if (!el) return;
    const colorMap = { indigo: '#818cf8', emerald: '#34d399', amber: '#fbbf24', rose: '#fb7185' };
    const icon = iconKey ? `<span style="color:${colorMap[tint] || colorMap.indigo};display:inline-flex;align-items:center">${ICON[iconKey]}</span>` : '';
    el.innerHTML = `<span style="display:inline-flex;align-items:center;gap:0.5rem">${icon}<span>${escapeHtml(text)}</span></span>`;
}

function updateHeaderStats() {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    set('stat-teams', db.teams.length);
    set('stat-players', db.players.length);
    set('stat-matches', db.matches.length);
}

// ---------------------------------------------------------------------
// API layer
// ---------------------------------------------------------------------
function applyState(state) {
    if (!state) return;
    serverVersion = state.version || 0;

    // N4 / N5 — settings are applied independently of db, and only fields
    // whose value is present and finite override the existing config. A
    // `null` setting no longer coerces to 0 (which would have silently
    // disabled win/draw/loss points).
    if (state.settings && typeof state.settings === 'object') {
        const s = state.settings;
        const finiteOr = (v, fallback) => {
            if (v == null || v === '') return fallback;
            const n = Number(v);
            return Number.isFinite(n) ? n : fallback;
        };
        appSettings.pointsWin  = finiteOr(s.pointsWin,  appSettings.pointsWin);
        appSettings.pointsDraw = finiteOr(s.pointsDraw, appSettings.pointsDraw);
        appSettings.pointsLoss = finiteOr(s.pointsLoss, appSettings.pointsLoss);
        appSettings.cardOrder  = Array.isArray(s.cardOrder) && s.cardOrder.length === 4
                                    ? s.cardOrder
                                    : appSettings.cardOrder;
        appSettings.themeColor = VALID_THEMES.includes(s.themeColor)
                                    ? s.themeColor
                                    : appSettings.themeColor;
    }

    // N5 — db is applied independently; a malformed or missing `settings`
    // block no longer prevents fresh entity data from being loaded.
    if (state.db && typeof state.db === 'object') {
        const src = state.db;
        db = {
            clubs:       Array.isArray(src.clubs)       ? src.clubs       : [],
            teams:       Array.isArray(src.teams)       ? src.teams       : [],
            players:     Array.isArray(src.players)     ? src.players     : [],
            tournaments: Array.isArray(src.tournaments) ? src.tournaments : [],
            matches:     Array.isArray(src.matches)     ? src.matches     : []
        };
    }

    updateHeaderStats();
}

async function request(method, url, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }

    const res = await fetch(url, options);
    let data = null;
    try { data = await res.json(); } catch {}

    if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status})`);

    // N9 — a 204 / non-JSON success used to leave client state stale for
    // up to 4 s. Force the next poll to fetch state immediately, unless
    // the request itself was /api/state (which would loop).
    if (data === null) {
        if (!url.includes('/api/state')) {
            forceStateRefresh = true;
            setTimeout(pollForUpdates, 100);
        }
        return null;
    }

    applyState(data);
    return data;
}

const api = {
    get: (url) => request('GET', url),
    post: (url, body) => request('POST', url, body),
    put: (url, body) => request('PUT', url, body),
    del: (url) => request('DELETE', url)
};

// ---------------------------------------------------------------------
// UI controller
// ---------------------------------------------------------------------
const ui = {
    openSettings() {
        modalDirty = false;
        // N6 — snapshot the settings so we can detect changes made by
        // another user while this form is open.
        settingsSnapshot = JSON.stringify(appSettings);
        // N6 — `kind: 'settings'` so the Escape dirty check and the poll
        // refresh (see refreshCurrentView) can recognise this view.
        currentView = { kind: 'settings' };

        const bodyEl = document.getElementById('modal-body');
        setModalTitle('Application Settings', 'settings', 'indigo');

        bodyEl.innerHTML = `
            <form onsubmit="ui.saveSettings(event)" class="flex flex-col gap-5">
                <div>
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">1. League Points Configuration</h4>
                    <div class="grid grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs text-slate-300 mb-1">Win Points</label>
                            <input id="s-pts-win" type="number" value="${Number(appSettings.pointsWin) || 0}" class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-300 mb-1">Draw Points</label>
                            <input id="s-pts-draw" type="number" value="${Number(appSettings.pointsDraw) || 0}" class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-300 mb-1">Loss Points</label>
                            <input id="s-pts-loss" type="number" value="${Number(appSettings.pointsLoss) || 0}" class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        </div>
                    </div>
                </div>
                <div class="border-t border-slate-800 pt-4">
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">2. Action Card Order</h4>
                    <select id="s-card-order" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        <option value="browse,add,edit,remove" ${appSettings.cardOrder.join(',') === 'browse,add,edit,remove' ? 'selected' : ''}>Standard (Browse → Add → Edit → Remove)</option>
                        <option value="add,browse,edit,remove" ${appSettings.cardOrder.join(',') === 'add,browse,edit,remove' ? 'selected' : ''}>Data Entry First (Add → Browse → Edit → Remove)</option>
                        <option value="edit,remove,browse,add" ${appSettings.cardOrder.join(',') === 'edit,remove,browse,add' ? 'selected' : ''}>Management First (Edit → Remove → Browse → Add)</option>
                    </select>
                </div>
                <div class="border-t border-slate-800 pt-4">
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">3. Theme Accent Color</h4>
                    <select id="s-theme-color" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        <option value="indigo" ${appSettings.themeColor === 'indigo' ? 'selected' : ''}>Indigo Dark Modern (Default)</option>
                        <option value="emerald" ${appSettings.themeColor === 'emerald' ? 'selected' : ''}>Emerald Sports Green</option>
                        <option value="amber" ${appSettings.themeColor === 'amber' ? 'selected' : ''}>Amber Gold Classic</option>
                        <option value="rose" ${appSettings.themeColor === 'rose' ? 'selected' : ''}>Rose Crimson High-Contrast</option>
                    </select>
                </div>
                <div class="border-t border-slate-800 pt-4">
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">4. Database Backup & Restore</h4>
                    <div class="flex gap-3">
                        <button type="button" onclick="ui.downloadDatabaseBackup()" class="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">Download Backup (.json)</button>
                        <button type="button" onclick="ui.resetDatabase()" class="flex-1 py-2.5 rounded-xl bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/40 text-xs font-medium transition">Reset Database</button>
                    </div>
                </div>
                <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition mt-2">Save Settings</button>
            </form>
        `;
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    async saveSettings(e) {
        e.preventDefault();

        // N6 — if another user changed settings since this form was opened,
        // make the overwrite explicit.
        if (JSON.stringify(appSettings) !== settingsSnapshot) {
            if (!confirm('Settings were changed by another user since you opened this form. Overwrite their changes?')) return;
        }

        const num = (id, fallback) => {
            const value = parseInt(document.getElementById(id).value, 10);
            return Number.isFinite(value) ? value : fallback;
        };

        const payload = {
            pointsWin: num('s-pts-win', appSettings.pointsWin),
            pointsDraw: num('s-pts-draw', appSettings.pointsDraw),
            pointsLoss: num('s-pts-loss', appSettings.pointsLoss),
            cardOrder: document.getElementById('s-card-order').value.split(','),
            themeColor: document.getElementById('s-theme-color').value
        };

        try {
            await api.put('/api/settings', payload);
            ui.applyThemeAndLayout();
            setStatus('Settings applied for all users.');
            ui.closeModal();
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    applyThemeAndLayout() {
        const themes = ['theme-indigo', 'theme-emerald', 'theme-amber', 'theme-rose'];
        const desired = `theme-${appSettings.themeColor}`;
        const currentTheme = themes.find((t) => document.body.classList.contains(t));
        if (currentTheme !== desired) {
            themes.forEach((t) => document.body.classList.remove(t));
            document.body.classList.add(desired);
        }
        const grid = document.getElementById('action-cards-grid');
        if (!grid) return;
        const currentOrder = Array.from(grid.children).map((c) => c.dataset.card);
        if (currentOrder.join(',') !== appSettings.cardOrder.join(',')) {
            appSettings.cardOrder.forEach((cardKey) => {
                const cardEl = grid.querySelector(`[data-card="${cardKey}"]`);
                if (cardEl) grid.appendChild(cardEl);
            });
        }
    },

    async downloadDatabaseBackup() {
        try {
            const res = await fetch('/api/backup');
            if (!res.ok) throw new Error(`Request failed (${res.status})`);
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = `tchoukball_db_backup_${Date.now()}.json`;
            document.body.appendChild(anchor);
            anchor.click();
            setTimeout(() => {
                URL.revokeObjectURL(url);
                anchor.remove();
            }, 1000);
            setStatus('Database backup downloaded.');
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    async resetDatabase() {
        if (!confirm('Reset ALL shared records for every user back to the default values?')) return;
        try {
            await api.post('/api/reset');
            ui.applyThemeAndLayout();
            updateHeaderStats();
            ui.closeModal();
            setStatus('Shared database reset to defaults.');
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    openBrowser(type) {
        modalDirty = false;
        currentView = { kind: 'browse', type };
        const bodyEl = document.getElementById('modal-body');

        if (type === 'players') {
            setModalTitle('Browse Players', 'browse', 'indigo');
            const rows = db.players.map((p) => {
                const team = db.teams.find((t) => idEq(t.id, p.teamId))?.name || 'No Team';
                const name = `${p.fname || ''} ${p.lname || ''}`.trim();
                return `<tr data-player-id="${escapeHtml(p.id)}" class="player-row border-b border-slate-800/80 hover:bg-indigo-600/10 cursor-pointer transition">
                    <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${escapeHtml(p.id)}</td>
                    <td class="py-3 px-4 font-medium text-slate-100">${escapeHtml(name)}</td>
                    <td class="py-3 px-4 text-slate-300">${escapeHtml(team)}</td>
                    <td class="py-3 px-4 text-xs text-slate-400">${escapeHtml(p.position || 'Not Set')}</td>
                    <td class="py-2 px-3 text-right">
                        <button type="button" data-player-id="${escapeHtml(p.id)}" title="Player actions" aria-label="Actions for ${escapeHtml(name)}" class="player-actions-btn w-8 h-8 rounded-lg bg-slate-800/60 hover:bg-indigo-600/30 text-slate-300 hover:text-indigo-200 inline-flex items-center justify-center transition text-base leading-none">⋯</button>
                    </td>
                </tr>`;
            }).join('');

            bodyEl.innerHTML = `
                <p class="text-xs text-amber-300/80 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl mb-4"><strong>Tip:</strong> Click a row to open the player profile, or use the ⋯ button for more actions.</p>
                <div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse">
                    <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase tracking-wider"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Player Name</th><th class="py-3 px-4">Team</th><th class="py-3 px-4">Position</th><th class="py-3 px-4 text-right">Actions</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="5" class="p-4 text-center text-slate-500">No players found.</td></tr>'}</tbody>
                </table></div>`;

            const tbody = bodyEl.querySelector('tbody');
            if (tbody) {
                tbody.addEventListener('contextmenu', (e) => {
                    const row = e.target.closest('tr[data-player-id]');
                    if (!row) return;
                    e.preventDefault();
                    showContextMenu(e.clientX, e.clientY, row.dataset.playerId);
                });
                tbody.addEventListener('click', (e) => {
                    const btn = e.target.closest('.player-actions-btn');
                    if (btn) {
                        e.stopPropagation();
                        const rect = btn.getBoundingClientRect();
                        showContextMenu(rect.left, rect.bottom + 4, btn.dataset.playerId);
                        return;
                    }
                    const row = e.target.closest('tr[data-player-id]');
                    if (row) ui.openPlayerProfile(row.dataset.playerId);
                });
            }
        } else if (type === 'teams') {
            setModalTitle('Browse Teams', 'browse', 'indigo');
            const rows = db.teams.map((t) => {
                const club = db.clubs.find((c) => idEq(c.id, t.clubId))?.name || 'No Club';
                return `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${escapeHtml(t.id)}</td><td class="py-3 px-4 font-medium text-slate-100">${escapeHtml(t.name)}</td><td class="py-3 px-4 text-slate-300">${escapeHtml(club)}</td></tr>`;
            }).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Team Name</th><th class="py-3 px-4">Club</th></tr></thead><tbody>${rows || '<tr><td colspan="3" class="p-4 text-center text-slate-500">No teams found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'clubs') {
            setModalTitle('Browse Clubs', 'browse', 'indigo');
            const rows = db.clubs.map((c) => `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${escapeHtml(c.id)}</td><td class="py-3 px-4 font-medium text-slate-100">${escapeHtml(c.name)}</td></tr>`).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Club Name</th></tr></thead><tbody>${rows || '<tr><td colspan="2" class="p-4 text-center text-slate-500">No clubs found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'matches') {
            setModalTitle('Browse Matches', 'browse', 'indigo');
            const rows = db.matches.map((m) => {
                const home = db.teams.find((t) => idEq(t.id, m.homeId))?.name || 'Home';
                const away = db.teams.find((t) => idEq(t.id, m.awayId))?.name || 'Away';
                const tourn = db.tournaments.find((tr) => idEq(tr.id, m.tournId))?.name || 'Exhibition';
                return `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${escapeHtml(m.id)}</td><td class="py-3 px-4 font-medium text-slate-100">${escapeHtml(home)} vs ${escapeHtml(away)}</td><td class="py-3 px-4 text-slate-300">${escapeHtml(tourn)}</td><td class="py-3 px-4 text-xs text-slate-400">${escapeHtml(m.date || 'TBD')}</td></tr>`;
            }).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Fixture</th><th class="py-3 px-4">Tournament</th><th class="py-3 px-4">Date</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No matches found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'tournaments') {
            setModalTitle('Browse Tournaments', 'browse', 'indigo');
            const rows = db.tournaments.map((tr) => `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${escapeHtml(tr.id)}</td><td class="py-3 px-4 font-medium text-slate-100">${escapeHtml(tr.name)}</td><td class="py-3 px-4 text-slate-300">${escapeHtml(tr.location || '—')}</td><td class="py-3 px-4 text-xs text-slate-400">${escapeHtml(tr.date || 'TBD')}</td></tr>`).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Tournament Name</th><th class="py-3 px-4">Location</th><th class="py-3 px-4">Date</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No tournaments found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'rosters') {
            setModalTitle('Match Rosters', 'browse', 'indigo');
            const rows = db.players.map((p) => {
                const team = db.teams.find((t) => idEq(t.id, p.teamId))?.name || 'Unassigned';
                const name = `${p.fname || ''} ${p.lname || ''}`.trim();
                return `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-medium text-slate-100">${escapeHtml(name)}</td><td class="py-3 px-4 text-indigo-300">${escapeHtml(team)}</td><td class="py-3 px-4 text-xs text-slate-400">${Number(p.appearances) || 0} match appearances</td></tr>`;
            }).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">Player</th><th class="py-3 px-4">Assigned Team</th><th class="py-3 px-4">Roster Count</th></tr></thead><tbody>${rows || '<tr><td colspan="3" class="p-4 text-center text-slate-500">No players found.</td></tr>'}</tbody></table></div>`;
        }
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    openPlayerProfile(playerId) {
        // N1 — id-tolerant lookup so string/number mismatches don't close the modal.
        const p = db.players.find((x) => idEq(x.id, playerId));
        if (!p) {
            ui.closeModal();
            setStatus('That player no longer exists — profile closed.');
            return;
        }
        modalDirty = false;
        currentView = { kind: 'profile', id: playerId };

        const playerTeam = db.teams.find((t) => idEq(t.id, p.teamId));
        const teamName = playerTeam?.name || 'No Team';
        const clubName = db.clubs.find((c) => idEq(c.id, playerTeam?.clubId))?.name || 'No Club';
        const fullName = `${p.fname || ''} ${p.lname || ''}`.trim();
        const birthDisplay = p.birthdate ? (toDateInput(p.birthdate) || 'N/A') : 'N/A';

        setModalTitle(`Player Profile — ${fullName}`, 'user', 'indigo');
        const matchRows = (p.matches || []).map((m) => `<tr class="border-b border-slate-800/60 hover:bg-slate-800/30"><td class="py-2.5 px-3 text-slate-200 font-medium">${escapeHtml(m.matchup || '—')}</td><td class="py-2.5 px-3 text-slate-400 text-xs">${escapeHtml(m.date || '—')}</td><td class="py-2.5 px-3 text-indigo-300 font-bold font-mono text-right">${Number(m.points) || 0} pts</td></tr>`).join('');
        // N3 — number-parse before fallback so `"abc"` or `NaN` renders "0.0".
        const avg = (Number(p.avgPoints) || 0).toFixed(1);
        const position = p.position || 'Not Set';

        document.getElementById('modal-body').innerHTML = `
            <div class="flex flex-col gap-5">
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-slate-900/70 p-4 rounded-xl border border-slate-800 text-xs">
                    <div><span class="text-slate-500 block">Club</span><strong class="text-slate-200 text-sm">${escapeHtml(clubName)}</strong></div>
                    <div><span class="text-slate-500 block">Team</span><strong class="text-slate-200 text-sm">${escapeHtml(teamName)}</strong></div>
                    <div><span class="text-slate-500 block">Birthdate</span><strong class="text-slate-200 text-sm">${escapeHtml(birthDisplay)}</strong></div>
                    <div><span class="text-slate-500 block">Primary Position</span><strong class="text-indigo-300 text-sm">${escapeHtml(position)}</strong></div>
                    <div><span class="text-slate-500 block">Appearances</span><strong class="text-slate-200 text-sm">${Number(p.appearances) || 0} matches</strong></div>
                    <div><span class="text-slate-500 block">Win/Loss Record</span><strong class="text-emerald-400 text-sm">${Number(p.wins) || 0}W - ${Number(p.losses) || 0}L - ${Number(p.draws) || 0}D</strong></div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div class="bg-indigo-950/20 border border-indigo-500/30 p-3.5 rounded-xl"><span class="text-xs text-indigo-300 uppercase font-bold tracking-wider">Total Points</span><div class="text-2xl font-extrabold text-white mt-1">${Number(p.totalPoints) || 0} <span class="text-xs font-normal text-slate-400">pts</span></div></div>
                    <div class="bg-indigo-950/20 border border-indigo-500/30 p-3.5 rounded-xl"><span class="text-xs text-indigo-300 uppercase font-bold tracking-wider">Avg Points / Match</span><div class="text-2xl font-extrabold text-white mt-1">${avg} <span class="text-xs font-normal text-slate-400">pts/gm</span></div></div>
                </div>
                <div class="bg-slate-900/50 border border-slate-800 p-3.5 rounded-xl flex flex-col gap-2 text-xs">
                    <div class="flex items-center justify-between"><span class="text-slate-400">Highest Scoring Match:</span><strong class="text-amber-300 font-mono">${p.highestMatch ? `${Number(p.highestMatch.points) || 0} pts (${escapeHtml(p.highestMatch.opponent || '—')})` : 'N/A'}</strong></div>
                    <div class="flex items-center justify-between border-t border-slate-800/80 pt-2"><span class="text-slate-400">Lowest Scoring Match:</span><strong class="text-slate-300 font-mono">${p.lowestMatch ? `${Number(p.lowestMatch.points) || 0} pts (${escapeHtml(p.lowestMatch.opponent || '—')})` : 'N/A'}</strong></div>
                </div>
                <div><h4 class="text-xs font-bold uppercase text-slate-400 tracking-wider mb-2">Match Roster History</h4><div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left text-xs"><thead class="bg-slate-900/80 text-slate-400 uppercase font-semibold"><tr><th class="py-2.5 px-3">Matchup</th><th class="py-2.5 px-3">Date</th><th class="py-2.5 px-3 text-right">Points Scored</th></tr></thead><tbody>${matchRows || '<tr><td colspan="3" class="p-3 text-center text-slate-500">No match records found.</td></tr>'}</tbody></table></div></div>
            </div>`;
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    // N13 — `returnTo` (optional) tells the form where to return after
    // the team is created, so the match-creation flow doesn't dead-end.
    openForm(action, returnTo) {
        modalDirty = false;
        currentView = null;
        const bodyEl = document.getElementById('modal-body');
        const inputClass = 'w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500';

        if (action === 'add-team') {
            afterAddTeamReturnTo = returnTo || null;
            setModalTitle('Add Team', 'plus', 'emerald');
            const clubOpts = db.clubs.map((c) => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddTeam(event)" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Team Name</label><input id="f-team-name" type="text" required class="${inputClass}" placeholder="e.g. Geneva Dragons"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Club</label><select id="f-team-club" class="${inputClass}"><option value="">(None)</option>${clubOpts}</select></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Team</button></form>`;
        } else if (action === 'add-club') {
            setModalTitle('Add Club', 'plus', 'emerald');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddClub(event)" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Club Name</label><input id="f-club-name" type="text" required class="${inputClass}" placeholder="e.g. Lausanne Tchoukball Club"></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Club</button></form>`;
        } else if (action === 'add-player') {
            setModalTitle('Add Player', 'plus', 'emerald');
            const teamOpts = db.teams.map((t) => `<option value="${escapeHtml(t.id)}">${escapeHtml(t.name)}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddPlayer(event)" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">First Name</label><input id="f-p-fname" type="text" required class="${inputClass}" placeholder="First Name"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Surname</label><input id="f-p-lname" type="text" class="${inputClass}" placeholder="Surname"></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Assigned Team</label><select id="f-p-team" class="${inputClass}"><option value="">(None)</option>${teamOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Birthdate</label><input id="f-p-birth" type="date" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Position</label><input id="f-p-pos" type="text" class="${inputClass}" placeholder="e.g. Wing Shooter"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Player</button></form>`;
        } else if (action === 'add-match') {
            setModalTitle('Add Match Fixture', 'plus', 'emerald');
            if (db.teams.length < 2) {
                bodyEl.innerHTML = `<div class="text-sm text-amber-300 bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl">You need at least two teams to create a match. <button type="button" onclick="ui.openForm('add-team', { kind: 'add-match' })" class="text-emerald-400 hover:underline font-medium">Add a team</button></div>`;
                document.getElementById('modal-backdrop').classList.remove('hidden');
                return;
            }
            const teamOpts = db.teams.map((t) => `<option value="${escapeHtml(t.id)}">${escapeHtml(t.name)}</option>`).join('');
            const tournOpts = db.tournaments.map((tr) => `<option value="${escapeHtml(tr.id)}">${escapeHtml(tr.name)}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddMatch(event)" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Home Team</label><select id="f-m-home" required class="${inputClass}">${teamOpts}</select></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Away Team</label><select id="f-m-away" required class="${inputClass}">${teamOpts}</select></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament</label><select id="f-m-tourn" class="${inputClass}"><option value="">(None / Friendly)</option>${tournOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Date</label><input id="f-m-date" type="date" class="${inputClass}"><p class="text-[10px] text-slate-500 mt-1">Leave empty for TBD</p></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-m-loc" type="text" class="${inputClass}" placeholder="e.g. Geneva Arena"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Create Match</button></form>`;
        } else if (action === 'add-tournament') {
            setModalTitle('Add Tournament', 'plus', 'emerald');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddTournament(event)" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament Name</label><input id="f-tr-name" type="text" required class="${inputClass}" placeholder="e.g. World Cup 2026"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-tr-loc" type="text" class="${inputClass}" placeholder="e.g. Geneva, Switzerland"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Start Date</label><input id="f-tr-date" type="date" class="${inputClass}"><p class="text-[10px] text-slate-500 mt-1">Leave empty for TBD</p></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Tournament</button></form>`;
        }
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    openSelector(mode) {
        modalDirty = false;
        currentView = null;
        const bodyEl = document.getElementById('modal-body');
        const [action, entity] = mode.split('-');

        setModalTitle(
            `${action === 'remove' ? 'Remove' : 'Edit'} ${entity[0].toUpperCase() + entity.slice(1)}`,
            action === 'remove' ? 'trash' : 'edit',
            action === 'remove' ? 'rose' : 'amber'
        );

        const inputClass = 'w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500';

        let options = [];
        if (entity === 'player') options = db.players.map((p) => ({ id: p.id, name: `${p.fname || ''} ${p.lname || ''}`.trim() }));
        if (entity === 'team') options = db.teams.map((t) => ({ id: t.id, name: t.name }));
        if (entity === 'club') options = db.clubs.map((c) => ({ id: c.id, name: c.name }));
        if (entity === 'tournament') options = db.tournaments.map((tr) => ({ id: tr.id, name: tr.name }));
        if (entity === 'match') options = db.matches.map((m) => ({ id: m.id, name: ui.describeRecord('match', m.id) }));

        if (options.length === 0) {
            const plural = PLURAL[entity] || (entity + 's');
            bodyEl.innerHTML = `<div class="text-center py-8 text-slate-400 text-sm">No ${escapeHtml(plural)} to ${escapeHtml(action)}.</div>`;
            document.getElementById('modal-backdrop').classList.remove('hidden');
            return;
        }

        const optsHtml = options.map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name || '—')}</option>`).join('');

        bodyEl.innerHTML = `
            <form onsubmit="ui.handleSelectorSubmit(event, '${escapeHtml(action)}', '${escapeHtml(entity)}')" class="flex flex-col gap-4">
                <div>
                    <label class="block text-xs font-medium text-slate-300 mb-1">Select ${escapeHtml(entity.toUpperCase())}</label>
                    <select id="f-select-id" required class="${inputClass}">
                        ${optsHtml}
                    </select>
                </div>
                <button type="submit" class="w-full py-2.5 rounded-xl ${action === 'remove' ? 'bg-rose-600 hover:bg-rose-500' : 'bg-amber-600 hover:bg-amber-500'} text-white font-medium text-sm transition">
                    ${escapeHtml(action.toUpperCase())} ${escapeHtml(entity.toUpperCase())}
                </button>
            </form>
        `;

        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    handleSelectorSubmit(e, action, entity) {
        e.preventDefault();
        const selectedId = document.getElementById('f-select-id').value;
        if (!selectedId) return setStatus('Please select a record.');

        if (action === 'remove') {
            ui.confirmRemove(entity, selectedId);
        } else {
            ui.openEditForm(entity, selectedId);
        }
    },

    describeRecord(entity, id) {
        const find = (collection, recordId) =>
            (db[collection] || []).find((x) => idEq(x.id, recordId));

        if (entity === 'player') { const p = find('players', id); return p ? `${p.fname || ''} ${p.lname || ''}`.trim() : ''; }
        if (entity === 'team') { const t = find('teams', id); return t ? t.name : ''; }
        if (entity === 'club') { const c = find('clubs', id); return c ? c.name : ''; }
        if (entity === 'tournament') { const tr = find('tournaments', id); return tr ? tr.name : ''; }
        if (entity === 'match') {
            const m = find('matches', id);
            if (!m) return '';
            const home = find('teams', m.homeId)?.name || 'Home';
            const away = find('teams', m.awayId)?.name || 'Away';
            return `${home} vs ${away} (${m.date || 'TBD'})`;
        }
        return '';
    },

    confirmRemove(entity, id) {
        modalDirty = false;
        const label = ui.describeRecord(entity, id) || `#${id}`;
        const Entity = entity[0].toUpperCase() + entity.slice(1);

        setModalTitle('Confirm Removal', 'trash', 'rose');
        const bodyEl = document.getElementById('modal-body');
        bodyEl.innerHTML = `
            <div class="flex flex-col gap-4">
                <div class="bg-rose-950/30 border border-rose-800/40 p-4 rounded-xl">
                    <p class="text-sm font-semibold text-rose-100">Delete ${escapeHtml(entity)} “${escapeHtml(label)}”?</p>
                    <p class="text-xs text-rose-300/80 mt-1">This removes the record for <strong>every</strong> user and cannot be undone.</p>
                </div>
                <div class="flex gap-3">
                    <button type="button" data-action="cancel" class="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition">Cancel</button>
                    <button type="button" data-action="delete" class="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-medium transition">Delete ${escapeHtml(Entity)}</button>
                </div>
            </div>`;

        bodyEl.querySelector('[data-action="cancel"]').addEventListener('click', () => {
            ui.openSelector(`remove-${entity}`);
        });
        bodyEl.querySelector('[data-action="delete"]').addEventListener('click', () => {
            ui.performRemove(entity, String(id));
        });

        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    async performRemove(entity, id) {
        const Entity = entity[0].toUpperCase() + entity.slice(1);
        const label = ui.describeRecord(entity, id) || `#${id}`;

        const exists = (db[PLURAL[entity]] || []).some((x) => idEq(x.id, id));
        if (!exists) {
            setStatus(`${Entity} “${label}” no longer exists — it may have already been removed.`);
            ui.closeModal();
            return;
        }

        try {
            await api.del(`/api/${PLURAL[entity]}/${id}`);
            setStatus(`${Entity} “${label}” deleted for everyone.`);
            ui.closeModal();
        } catch (err) {
            setStatus(`Error: ${err.message}`);
        }
    },

    openEditForm(entity, id) {
        modalDirty = false;
        const targetId = id;                // N1 — keep original type; idEq handles comparison
        currentView = { kind: 'form', entity, id: targetId };
        const bodyEl = document.getElementById('modal-body');
        const inputClass = 'w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500';

        if (entity === 'player') {
            const p = db.players.find((x) => idEq(x.id, targetId));
            if (!p) { ui.closeModal(); return setStatus('Player not found.'); }
            // N7 — snapshot so we can detect concurrent edits on save.
            editFormSnapshot = JSON.stringify(p);
            setModalTitle(`Edit Player — ${p.fname || ''} ${p.lname || ''}`.trim(), 'edit', 'amber');
            const teamOpts = refOptions(
                db.teams.map((t) => ({ id: t.id, name: t.name })),
                p.teamId,
                '(None)',
                'previous team'
            );
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'player', ${escapeHtml(p.id)})" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">First Name</label><input id="f-ep-fname" type="text" required value="${escapeHtml(p.fname || '')}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Surname</label><input id="f-ep-lname" type="text" value="${escapeHtml(p.lname || '')}" class="${inputClass}"></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Team</label><select id="f-ep-team" class="${inputClass}">${teamOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Birthdate</label><input id="f-ep-birth" type="date" value="${escapeHtml(toDateInput(p.birthdate))}" class="${inputClass}"><p class="text-[10px] text-slate-500 mt-1">Leave empty to clear</p></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Position</label><input id="f-ep-pos" type="text" value="${escapeHtml(p.position || '')}" class="${inputClass}"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'team') {
            const t = db.teams.find((x) => idEq(x.id, targetId));
            if (!t) { ui.closeModal(); return setStatus('Team not found.'); }
            editFormSnapshot = JSON.stringify(t);
            setModalTitle(`Edit Team — ${t.name}`, 'edit', 'amber');
            const clubOpts = refOptions(
                db.clubs.map((c) => ({ id: c.id, name: c.name })),
                t.clubId,
                '(None)',
                'previous club'
            );
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'team', ${escapeHtml(t.id)})" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Team Name</label><input id="f-et-name" type="text" required value="${escapeHtml(t.name || '')}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Club</label><select id="f-et-club" class="${inputClass}">${clubOpts}</select></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'club') {
            const c = db.clubs.find((x) => idEq(x.id, targetId));
            if (!c) { ui.closeModal(); return setStatus('Club not found.'); }
            editFormSnapshot = JSON.stringify(c);
            setModalTitle(`Edit Club — ${c.name}`, 'edit', 'amber');
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'club', ${escapeHtml(c.id)})" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Club Name</label><input id="f-ec-name" type="text" required value="${escapeHtml(c.name || '')}" class="${inputClass}"></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'tournament') {
            const tr = db.tournaments.find((x) => idEq(x.id, targetId));
            if (!tr) { ui.closeModal(); return setStatus('Tournament not found.'); }
            editFormSnapshot = JSON.stringify(tr);
            setModalTitle(`Edit Tournament — ${tr.name}`, 'edit', 'amber');
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'tournament', ${escapeHtml(tr.id)})" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament Name</label><input id="f-etr-name" type="text" required value="${escapeHtml(tr.name || '')}" class="${inputClass}"></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-etr-loc" type="text" value="${escapeHtml(tr.location || '')}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Date</label><input id="f-etr-date" type="date" value="${escapeHtml(toDateInput(tr.date))}" class="${inputClass}"><p class="text-[10px] text-slate-500 mt-1">Leave empty for TBD</p></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'match') {
            if (db.teams.length < 2) {
                currentView = null;
                bodyEl.innerHTML = `<div class="text-sm text-amber-300 bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl">This match can't be edited until at least two teams exist. <button type="button" onclick="ui.openForm('add-team', { kind: 'edit-match', id: ${JSON.stringify(String(targetId))} })" class="text-emerald-400 hover:underline font-medium">Add a team</button></div>`;
                document.getElementById('modal-backdrop').classList.remove('hidden');
                return;
            }
            const m = db.matches.find((x) => idEq(x.id, targetId));
            if (!m) { ui.closeModal(); return setStatus('Match not found.'); }
            editFormSnapshot = JSON.stringify(m);
            setModalTitle('Edit Match Fixture', 'edit', 'amber');
            const teamList = db.teams.map((t) => ({ id: t.id, name: t.name }));
            const homeOpts = refOptions(teamList, m.homeId, null, 'previous home team');
            const awayOpts = refOptions(teamList, m.awayId, null, 'previous away team');
            const tournOpts = refOptions(
                db.tournaments.map((tr) => ({ id: tr.id, name: tr.name })),
                m.tournId,
                '(None / Friendly)',
                'previous tournament'
            );
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'match', ${escapeHtml(m.id)})" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Home Team</label><select id="f-em-home" required class="${inputClass}">${homeOpts}</select></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Away Team</label><select id="f-em-away" required class="${inputClass}">${awayOpts}</select></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament</label><select id="f-em-tourn" class="${inputClass}">${tournOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Date</label><input id="f-em-date" type="date" value="${escapeHtml(toDateInput(m.date))}" class="${inputClass}"><p class="text-[10px] text-slate-500 mt-1">Leave empty for TBD</p></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-em-loc" type="text" value="${escapeHtml(m.location || '')}" class="${inputClass}"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        }
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    async submitAddTeam(e) {
        e.preventDefault();
        const name = document.getElementById('f-team-name').value.trim();
        if (!name) return setStatus('Team name is required.');
        const clubId = toIdOrNull(document.getElementById('f-team-club').value);
        try {
            await api.post('/api/teams', { name, clubId });
            setStatus(`Team "${name}" created.`);
            // N13 — return to the match form that sent us here, if any.
            const returnTo = afterAddTeamReturnTo;
            afterAddTeamReturnTo = null;
            if (returnTo && returnTo.kind === 'add-match') {
                ui.openForm('add-match');
            } else if (returnTo && returnTo.kind === 'edit-match') {
                ui.openEditForm('match', returnTo.id);
            } else {
                ui.closeModal();
            }
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddClub(e) {
        e.preventDefault();
        const name = document.getElementById('f-club-name').value.trim();
        if (!name) return setStatus('Club name is required.');
        try { await api.post('/api/clubs', { name }); setStatus(`Club "${name}" created.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddPlayer(e) {
        e.preventDefault();
        const fname = document.getElementById('f-p-fname').value.trim();
        const lname = document.getElementById('f-p-lname').value.trim();
        const birthdate = document.getElementById('f-p-birth').value;
        // N10 — send what the user entered; let display render "Not Set".
        const position = document.getElementById('f-p-pos').value.trim();
        if (!fname) return setStatus('First name is required.');
        const teamId = toIdOrNull(document.getElementById('f-p-team').value);
        try {
            await api.post('/api/players', { fname, lname, teamId, birthdate, position, appearances: 0, wins: 0, losses: 0, draws: 0, totalPoints: 0, avgPoints: 0, highestMatch: null, lowestMatch: null, matches: [] });
            setStatus(`Player "${fname} ${lname}" added successfully.`); ui.closeModal();
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddMatch(e) {
        e.preventDefault();
        const homeId = toIdOrNull(document.getElementById('f-m-home').value);
        const awayId = toIdOrNull(document.getElementById('f-m-away').value);
        if (homeId === null || awayId === null) return setStatus('Please select both a home and away team.');
        if (idEq(homeId, awayId)) return setStatus('Home and away teams must be different.');
        const tournId = toIdOrNull(document.getElementById('f-m-tourn').value);
        const date = document.getElementById('f-m-date').value || 'TBD';
        const location = document.getElementById('f-m-loc').value.trim() || 'Unspecified';
        try { await api.post('/api/matches', { homeId, awayId, tournId, date, location }); setStatus('Match fixture created.'); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddTournament(e) {
        e.preventDefault();
        const name = document.getElementById('f-tr-name').value.trim();
        if (!name) return setStatus('Tournament name is required.');
        const location = document.getElementById('f-tr-loc').value.trim() || 'Unspecified';
        const date = document.getElementById('f-tr-date').value || 'TBD';
        try { await api.post('/api/tournaments', { name, location, date }); setStatus(`Tournament "${name}" created.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitEdit(e, entity, id) {
        e.preventDefault();

        // N7 — if the underlying record changed since the form was opened,
        // let the user decide whether to overwrite.
        const current = (db[PLURAL[entity]] || []).find((x) => idEq(x.id, id));
        if (current && JSON.stringify(current) !== editFormSnapshot) {
            if (!confirm('This record was changed by another user since you opened it. Overwrite their changes?')) return;
        }

        const value = (elId) => document.getElementById(elId).value;
        const payload = {};

        if (entity === 'player') {
            const fname = value('f-ep-fname').trim();
            if (!fname) return setStatus('First name is required.');
            payload.fname = fname;
            payload.lname = value('f-ep-lname').trim();
            // N8 — validate against db.teams in case the team was deleted after render.
            const teamId = resolveReferenceSelect('f-ep-team', 'team', db.teams);
            if (teamId === undefined) return;
            payload.teamId = teamId;
            payload.birthdate = value('f-ep-birth');
            payload.position = value('f-ep-pos').trim();
        } else if (entity === 'team') {
            const name = value('f-et-name').trim();
            if (!name) return setStatus('Team name is required.');
            payload.name = name;
            const clubId = resolveReferenceSelect('f-et-club', 'club', db.clubs);
            if (clubId === undefined) return;
            payload.clubId = clubId;
        } else if (entity === 'club') {
            const name = value('f-ec-name').trim();
            if (!name) return setStatus('Club name is required.');
            payload.name = name;
        } else if (entity === 'tournament') {
            const name = value('f-etr-name').trim();
            if (!name) return setStatus('Tournament name is required.');
            payload.name = name;
            payload.location = value('f-etr-loc').trim() || 'Unspecified';
            payload.date = value('f-etr-date') || 'TBD';
        } else if (entity === 'match') {
            const homeId = resolveReferenceSelect('f-em-home', 'home team', db.teams);
            if (homeId === undefined) return;
            const awayId = resolveReferenceSelect('f-em-away', 'away team', db.teams);
            if (awayId === undefined) return;
            if (homeId === null || awayId === null) return setStatus('Please select both a home and away team.');
            if (idEq(homeId, awayId)) return setStatus('Home and away teams must be different.');
            payload.homeId = homeId;
            payload.awayId = awayId;
            const tournId = resolveReferenceSelect('f-em-tourn', 'tournament', db.tournaments);
            if (tournId === undefined) return;
            payload.tournId = tournId;
            payload.date = value('f-em-date') || 'TBD';
            payload.location = value('f-em-loc').trim() || 'Unspecified';
        }

        try { await api.put(`/api/${PLURAL[entity]}/${id}`, payload); setStatus(`${entity.toUpperCase()} updated for everyone.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    refreshCurrentView() {
        if (!currentView) return;
        const bodyEl = document.getElementById('modal-body');
        const prevScroll = bodyEl ? bodyEl.scrollTop : 0;

        if (currentView.kind === 'browse') {
            this.openBrowser(currentView.type);
        } else if (currentView.kind === 'profile') {
            this.openPlayerProfile(currentView.id);
        } else if (currentView.kind === 'settings') {
            // N6 — refresh the settings form with the new values only when
            // the user hasn't touched any field. A dirty form keeps its
            // values and warns on save instead.
            if (!modalDirty) this.openSettings();
            return;
        } else if (currentView.kind === 'form') {
            const { entity, id } = currentView;
            if (!PLURAL[entity]) { ui.closeModal(); return; }
            const exists = (db[PLURAL[entity]] || []).some((x) => idEq(x.id, id));
            if (!exists) {
                ui.closeModal();
                setStatus(`The ${entity} you were editing was removed by another user — changes discarded.`);
                return;
            }
        }

        if (bodyEl && currentView && currentView.kind !== 'form') {
            requestAnimationFrame(() => { bodyEl.scrollTop = prevScroll; });
        }
    },
    closeModal() {
        currentView = null;
        activePlayerId = null;
        modalDirty = false;
        afterAddTeamReturnTo = null;
        document.getElementById('modal-backdrop').classList.add('hidden');
    }
};

// ---------------------------------------------------------------------
// Right-click context menu
// ---------------------------------------------------------------------
function showContextMenu(x, y, playerId) {
    activePlayerId = playerId;
    const menu = document.getElementById('context-menu');
    if (!menu) return;
    // N12 — clamp to viewport with a 4px floor so tiny windows still show the menu.
    menu.style.left = `${Math.max(4, Math.min(x, window.innerWidth - 220))}px`;
    menu.style.top = `${Math.max(4, Math.min(y, window.innerHeight - 120))}px`;
    menu.classList.remove('hidden');
    menu.classList.remove('context-menu-animate');
    void menu.offsetWidth;
    menu.classList.add('context-menu-animate');
}

// ---------------------------------------------------------------------
// Status bar + live sync
// ---------------------------------------------------------------------
function setStatus(msg) {
    const bar = document.getElementById('status-bar');
    if (!bar) return;
    clearTimeout(statusTimer);
    bar.innerText = msg;
    statusTimer = setTimeout(() => { bar.innerText = 'Ready.'; }, 4000);
}

async function pollForUpdates() {
    if (polling || document.hidden) return;
    polling = true;
    try {
        const res = await fetch('/api/version', { cache: 'no-store' });
        if (!res.ok) return;
        const { version } = await res.json();
        // N9 — force a state fetch when a mutation completed without a JSON body.
        if (!forceStateRefresh && version === serverVersion) return;
        forceStateRefresh = false;
        await api.get('/api/state');
        ui.applyThemeAndLayout();
        ui.refreshCurrentView();
    } catch {} finally {
        polling = false;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('ctx-btn-profile')?.addEventListener('click', () => {
        const menu = document.getElementById('context-menu');
        if (menu) menu.classList.add('hidden');
        if (activePlayerId) ui.openPlayerProfile(activePlayerId);
    });
    document.getElementById('ctx-btn-edit')?.addEventListener('click', () => {
        const menu = document.getElementById('context-menu');
        if (menu) menu.classList.add('hidden');
        if (activePlayerId) ui.openEditForm('player', activePlayerId);
    });

    document.addEventListener('click', () => {
        const menu = document.getElementById('context-menu');
        if (menu) menu.classList.add('hidden');
    });

    // N11 — track whether the open form has unsaved edits.
    const modalBody = document.getElementById('modal-body');
    if (modalBody) {
        modalBody.addEventListener('input', () => { modalDirty = true; });
        modalBody.addEventListener('change', () => { modalDirty = true; });
    }

    // N11 — Escape closes the modal, but prompts if a form has unsaved edits.
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        const backdrop = document.getElementById('modal-backdrop');
        if (!backdrop || backdrop.classList.contains('hidden')) return;
        if (modalDirty && ['form', 'settings'].includes(currentView?.kind)) {
            if (!confirm('You have unsaved changes. Discard them?')) return;
        }
        ui.closeModal();
    });

    // N11 — same guard for backdrop clicks.
    document.getElementById('modal-backdrop')?.addEventListener('click', (e) => {
        if (e.target !== e.currentTarget) return;
        if (modalDirty && ['form', 'settings'].includes(currentView?.kind)) {
            if (!confirm('You have unsaved changes. Discard them?')) return;
        }
        ui.closeModal();
    });

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) pollForUpdates();
    });

    setStatus('Connecting to server…');
    try {
        await api.get('/api/state');
        ui.applyThemeAndLayout();
        setStatus('Connected — shared data loaded.');
    } catch (err) {
        setStatus(`Cannot reach server: ${err.message} — retrying…`);
    }
    setInterval(pollForUpdates, 4000);
});