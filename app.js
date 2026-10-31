// =====================================================================
//  Tchoukball Stats — client
//  All data lives on the server; this file keeps a read-only mirror of
//  it and re-syncs whenever the server's version number changes.
// =====================================================================

const appSettings = {
    pointsWin: 3, pointsDraw: 1, pointsLoss: 0,
    cardOrder: ['browse', 'add', 'edit', 'remove'],
    themeColor: 'indigo', focusTournamentId: 501
};

let db = { clubs: [], teams: [], players: [], tournaments: [], matches: [] };
let serverVersion = 0;
let currentView = null;

const PLURAL = {
    player: 'players', team: 'teams', club: 'clubs',
    tournament: 'tournaments', match: 'matches'
};

// ---------------------------------------------------------------------
// API layer
// ---------------------------------------------------------------------
function applyState(state) {
    if (!state || !state.db || !state.settings) return;
    serverVersion = state.version || 0;
    Object.assign(appSettings, state.settings);
    db = state.db;
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
        currentView = null;
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');
        titleEl.innerText = 'Application Settings';

        bodyEl.innerHTML = `
            <form onsubmit="ui.saveSettings(event)" class="flex flex-col gap-5">
                <div>
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">1. League Points Configuration</h4>
                    <div class="grid grid-cols-3 gap-3">
                        <div>
                            <label class="block text-xs text-slate-300 mb-1">Win Points</label>
                            <input id="s-pts-win" type="number" value="${appSettings.pointsWin}" class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-300 mb-1">Draw Points</label>
                            <input id="s-pts-draw" type="number" value="${appSettings.pointsDraw}" class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        </div>
                        <div>
                            <label class="block text-xs text-slate-300 mb-1">Loss Points</label>
                            <input id="s-pts-loss" type="number" value="${appSettings.pointsLoss}" class="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
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
        document.body.className = `p-4 md:p-8 flex flex-col min-h-screen theme-${appSettings.themeColor}`;
        const grid = document.getElementById('action-cards-grid');
        if (grid) {
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
            anchor.click();
            URL.revokeObjectURL(url);
            setStatus('Database backup downloaded.');
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    async resetDatabase() {
        if (!confirm('Reset ALL shared records for every user back to the default values?')) return;
        try {
            await api.post('/api/reset');
            ui.applyThemeAndLayout();
            ui.closeModal();
            setStatus('Shared database reset to defaults.');
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    openBrowser(type) {
        currentView = { kind: 'browse', type };
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');

        if (type === 'players') {
            titleEl.innerText = 'Browse Players';
            const rows = db.players.map((p) => {
                const team = db.teams.find((t) => t.id === p.teamId)?.name || 'No Team';
                return `<tr data-player-id="${p.id}" class="player-row border-b border-slate-800/80 hover:bg-indigo-600/10 cursor-pointer transition">
                    <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${p.id}</td>
                    <td class="py-3 px-4 font-medium text-slate-100">${p.fname} ${p.lname}</td>
                    <td class="py-3 px-4 text-slate-300">${team}</td>
                    <td class="py-3 px-4 text-xs text-slate-400">${p.position || 'Not Set'}</td>
                </tr>`;
            }).join('');

            bodyEl.innerHTML = `
                <p class="text-xs text-amber-300/80 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl mb-4"><strong>Tip:</strong> Right-click on any player row to view their full profile.</p>
                <div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse">
                    <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase tracking-wider"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Player Name</th><th class="py-3 px-4">Team</th><th class="py-3 px-4">Position</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No players found.</td></tr>'}</tbody>
                </table></div>`;
            setTimeout(() => {
                document.querySelectorAll('.player-row').forEach((row) => {
                    row.addEventListener('contextmenu', (e) => {
                        e.preventDefault();
                        const playerId = parseInt(row.getAttribute('data-player-id'), 10);
                        showContextMenu(e.clientX, e.clientY, playerId);
                    });
                });
            }, 50);
        } else if (type === 'teams') {
            titleEl.innerText = 'Browse Teams';
            const rows = db.teams.map((t) => {
                const club = db.clubs.find((c) => c.id === t.clubId)?.name || 'No Club';
                return `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${t.id}</td><td class="py-3 px-4 font-medium text-slate-100">${t.name}</td><td class="py-3 px-4 text-slate-300">${club}</td></tr>`;
            }).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Team Name</th><th class="py-3 px-4">Club</th></tr></thead><tbody>${rows || '<tr><td colspan="3" class="p-4 text-center text-slate-500">No teams found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'clubs') {
            titleEl.innerText = 'Browse Clubs';
            const rows = db.clubs.map((c) => `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${c.id}</td><td class="py-3 px-4 font-medium text-slate-100">${c.name}</td></tr>`).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Club Name</th></tr></thead><tbody>${rows || '<tr><td colspan="2" class="p-4 text-center text-slate-500">No clubs found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'matches') {
            titleEl.innerText = 'Browse Matches';
            const rows = db.matches.map((m) => {
                const home = db.teams.find((t) => t.id === m.homeId)?.name || 'Home';
                const away = db.teams.find((t) => t.id === m.awayId)?.name || 'Away';
                const tourn = db.tournaments.find((tr) => tr.id === m.tournId)?.name || 'Exhibition';
                return `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${m.id}</td><td class="py-3 px-4 font-medium text-slate-100">${home} vs ${away}</td><td class="py-3 px-4 text-slate-300">${tourn}</td><td class="py-3 px-4 text-xs text-slate-400">${m.date}</td></tr>`;
            }).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Fixture</th><th class="py-3 px-4">Tournament</th><th class="py-3 px-4">Date</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No matches found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'tournaments') {
            titleEl.innerText = 'Browse Tournaments';
            const rows = db.tournaments.map((tr) => `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-mono text-xs text-indigo-300">#${tr.id}</td><td class="py-3 px-4 font-medium text-slate-100">${tr.name}</td><td class="py-3 px-4 text-slate-300">${tr.location}</td><td class="py-3 px-4 text-xs text-slate-400">${tr.date}</td></tr>`).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Tournament Name</th><th class="py-3 px-4">Location</th><th class="py-3 px-4">Date</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No tournaments found.</td></tr>'}</tbody></table></div>`;
        } else if (type === 'rosters') {
            titleEl.innerText = 'Match Rosters';
            const rows = db.players.map((p) => {
                const team = db.teams.find((t) => t.id === p.teamId)?.name || 'Unassigned';
                return `<tr class="border-b border-slate-800/80 hover:bg-slate-800/40"><td class="py-3 px-4 font-medium text-slate-100">${p.fname} ${p.lname}</td><td class="py-3 px-4 text-indigo-300">${team}</td><td class="py-3 px-4 text-xs text-slate-400">${p.appearances || 0} match appearances</td></tr>`;
            }).join('');
            bodyEl.innerHTML = `<div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left border-collapse"><thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase"><tr><th class="py-3 px-4">Player</th><th class="py-3 px-4">Assigned Team</th><th class="py-3 px-4">Roster Count</th></tr></thead><tbody>${rows || '<tr><td colspan="3" class="p-4 text-center text-slate-500">No players found.</td></tr>'}</tbody></table></div>`;
        }
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    openPlayerProfile(playerId) {
        const p = db.players.find((x) => x.id === playerId);
        if (!p) { ui.closeModal(); return; }
        currentView = { kind: 'profile', id: playerId };
        const team = db.teams.find((t) => t.id === p.teamId)?.name || 'No Team';
        const club = db.clubs.find((c) => c.id === db.teams.find((t) => t.id === p.teamId)?.clubId)?.name || 'No Club';

        document.getElementById('modal-title').innerText = `Player Profile: ${p.fname} ${p.lname}`;
        const matchRows = (p.matches || []).map((m) => `<tr class="border-b border-slate-800/60 hover:bg-slate-800/30"><td class="py-2.5 px-3 text-slate-200 font-medium">${m.matchup}</td><td class="py-2.5 px-3 text-slate-400 text-xs">${m.date}</td><td class="py-2.5 px-3 text-indigo-300 font-bold font-mono text-right">${m.points} pts</td></tr>`).join('');

        document.getElementById('modal-body').innerHTML = `
            <div class="flex flex-col gap-5">
                <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-slate-900/70 p-4 rounded-xl border border-slate-800 text-xs">
                    <div><span class="text-slate-500 block">Club</span><strong class="text-slate-200 text-sm">${club}</strong></div>
                    <div><span class="text-slate-500 block">Team</span><strong class="text-slate-200 text-sm">${team}</strong></div>
                    <div><span class="text-slate-500 block">Birthdate</span><strong class="text-slate-200 text-sm">${p.birthdate || 'N/A'}</strong></div>
                    <div><span class="text-slate-500 block">Primary Position</span><strong class="text-indigo-300 text-sm">${p.position || 'Wing Shooter'}</strong></div>
                    <div><span class="text-slate-500 block">Appearances</span><strong class="text-slate-200 text-sm">${p.appearances || 0} matches</strong></div>
                    <div><span class="text-slate-500 block">Win/Loss Record</span><strong class="text-emerald-400 text-sm">${p.wins || 0}W - ${p.losses || 0}L - ${p.draws || 0}D</strong></div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div class="bg-indigo-950/20 border border-indigo-500/30 p-3.5 rounded-xl"><span class="text-xs text-indigo-300 uppercase font-bold tracking-wider">Total Points</span><div class="text-2xl font-extrabold text-white mt-1">${p.totalPoints || 0} <span class="text-xs font-normal text-slate-400">pts</span></div></div>
                    <div class="bg-indigo-950/20 border border-indigo-500/30 p-3.5 rounded-xl"><span class="text-xs text-indigo-300 uppercase font-bold tracking-wider">Avg Points / Match</span><div class="text-2xl font-extrabold text-white mt-1">${p.avgPoints || 0.0} <span class="text-xs font-normal text-slate-400">pts/gm</span></div></div>
                </div>
                <div class="bg-slate-900/50 border border-slate-800 p-3.5 rounded-xl flex flex-col gap-2 text-xs">
                    <div class="flex items-center justify-between"><span class="text-slate-400">Highest Scoring Match:</span><strong class="text-amber-300 font-mono">${p.highestMatch ? `${p.highestMatch.points} pts (${p.highestMatch.opponent})` : 'N/A'}</strong></div>
                    <div class="flex items-center justify-between border-t border-slate-800/80 pt-2"><span class="text-slate-400">Lowest Scoring Match:</span><strong class="text-slate-300 font-mono">${p.lowestMatch ? `${p.lowestMatch.points} pts (${p.lowestMatch.opponent})` : 'N/A'}</strong></div>
                </div>
                <div><h4 class="text-xs font-bold uppercase text-slate-400 tracking-wider mb-2">Match Roster History</h4><div class="overflow-x-auto rounded-xl border border-slate-800"><table class="w-full text-left text-xs"><thead class="bg-slate-900/80 text-slate-400 uppercase font-semibold"><tr><th class="py-2.5 px-3">Matchup</th><th class="py-2.5 px-3">Date</th><th class="py-2.5 px-3 text-right">Points Scored</th></tr></thead><tbody>${matchRows || '<tr><td colspan="3" class="p-3 text-center text-slate-500">No match records found.</td></tr>'}</tbody></table></div></div>
            </div>`;
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    openForm(action) {
        currentView = null;
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');
        const inputClass = 'w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500';

        if (action === 'add-team') {
            titleEl.innerText = 'ADD TEAM';
            const clubOpts = db.clubs.map((c) => `<option value="${c.id}">${c.name}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddTeam(event)" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Team Name</label><input id="f-team-name" type="text" required class="${inputClass}" placeholder="e.g. Geneva Dragons"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Club</label><select id="f-team-club" class="${inputClass}"><option value="">(None)</option>${clubOpts}</select></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Team</button></form>`;
        } else if (action === 'add-club') {
            titleEl.innerText = 'ADD CLUB';
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddClub(event)" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Club Name</label><input id="f-club-name" type="text" required class="${inputClass}" placeholder="e.g. Lausanne Tchoukball Club"></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Club</button></form>`;
        } else if (action === 'add-player') {
            titleEl.innerText = 'ADD PLAYER';
            const teamOpts = db.teams.map((t) => `<option value="${t.id}">${t.name}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddPlayer(event)" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">First Name</label><input id="f-p-fname" type="text" required class="${inputClass}" placeholder="First Name"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Surname</label><input id="f-p-lname" type="text" class="${inputClass}" placeholder="Surname"></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Assigned Team</label><select id="f-p-team" class="${inputClass}"><option value="">(None)</option>${teamOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Birthdate</label><input id="f-p-birth" type="date" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Position</label><input id="f-p-pos" type="text" class="${inputClass}" placeholder="e.g. Wing Shooter"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Player</button></form>`;
        } else if (action === 'add-match') {
            titleEl.innerText = 'ADD MATCH FIXTURE';
            const teamOpts = db.teams.map((t) => `<option value="${t.id}">${t.name}</option>`).join('');
            const tournOpts = db.tournaments.map((tr) => `<option value="${tr.id}">${tr.name}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddMatch(event)" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Home Team</label><select id="f-m-home" required class="${inputClass}">${teamOpts}</select></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Away Team</label><select id="f-m-away" required class="${inputClass}">${teamOpts}</select></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament</label><select id="f-m-tourn" class="${inputClass}"><option value="">(None / Friendly)</option>${tournOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Date</label><input id="f-m-date" type="date" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-m-loc" type="text" class="${inputClass}" placeholder="e.g. Geneva Arena"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Create Match</button></form>`;
        } else if (action === 'add-tournament') {
            titleEl.innerText = 'ADD TOURNAMENT';
            bodyEl.innerHTML = `<form onsubmit="ui.submitAddTournament(event)" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament Name</label><input id="f-tr-name" type="text" required class="${inputClass}" placeholder="e.g. World Cup 2026"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-tr-loc" type="text" class="${inputClass}" placeholder="e.g. Geneva, Switzerland"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Start Date</label><input id="f-tr-date" type="date" class="${inputClass}"></div><button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Tournament</button></form>`;
        }
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    openSelector(mode) {
        currentView = null;
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');
        const [action, entity] = mode.split('-');
        titleEl.innerText = `${action.toUpperCase()} ${entity.toUpperCase()}`;

        // THIS WAS THE MISSING LINE:
        const inputClass = 'w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500';

        let options = [];
        if (entity === 'player') options = db.players.map((p) => ({ id: p.id, name: `${p.fname} ${p.lname}` }));
        if (entity === 'team') options = db.teams.map((t) => ({ id: t.id, name: t.name }));
        if (entity === 'club') options = db.clubs.map((c) => ({ id: c.id, name: c.name }));
        if (entity === 'tournament') options = db.tournaments.map((tr) => ({ id: tr.id, name: tr.name }));
        if (entity === 'match') options = db.matches.map((m) => ({ id: m.id, name: `${db.teams.find((t) => t.id === m.homeId)?.name || 'Home'} vs ${db.teams.find((t) => t.id === m.awayId)?.name || 'Away'} (${m.date})` }));

        const optsHtml = options.map((o) => `<option value="${o.id}">${o.name}</option>`).join('');
        
        bodyEl.innerHTML = `
            <form onsubmit="ui.handleSelectorSubmit(event, '${action}', '${entity}')" class="flex flex-col gap-4">
                <div>
                    <label class="block text-xs font-medium text-slate-300 mb-1">Select ${entity.toUpperCase()}</label>
                    <select id="f-select-id" required class="${inputClass}">
                        ${optsHtml || '<option value="">None Available</option>'}
                    </select>
                </div>
                <button type="submit" class="w-full py-2.5 rounded-xl ${action === 'remove' ? 'bg-rose-600 hover:bg-rose-500' : 'bg-amber-600 hover:bg-amber-500'} text-white font-medium text-sm transition">
                    ${action.toUpperCase()} ${entity.toUpperCase()}
                </button>
            </form>
        `;
        
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    async handleSelectorSubmit(e, action, entity) {
        e.preventDefault();
        const selectedId = document.getElementById('f-select-id').value;
        if (!selectedId) return;

        if (action === 'remove') {
            try {
                await api.del(`/api/${PLURAL[entity]}/${selectedId}`);
                setStatus(`${entity.toUpperCase()} deleted for everyone.`);
                ui.closeModal();
            } catch (err) {
                alert(`Failed to save: ${err.message}`);
                setStatus(`Error: ${err.message}`);
            }
        } else {
            ui.openEditForm(entity, selectedId);
        }
    },

    openEditForm(entity, id) {
        currentView = null;
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');
        const inputClass = 'w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500';

        if (entity === 'player') {
            const p = db.players.find((x) => x.id === id);
            if (!p) return setStatus('Player not found.');
            titleEl.innerText = `EDIT PLAYER: ${p.fname} ${p.lname}`;
            const teamOpts = db.teams.map((t) => `<option value="${t.id}" ${t.id === p.teamId ? 'selected' : ''}>${t.name}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'player', ${p.id})" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">First Name</label><input id="f-ep-fname" type="text" required value="${p.fname}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Surname</label><input id="f-ep-lname" type="text" value="${p.lname}" class="${inputClass}"></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Team</label><select id="f-ep-team" class="${inputClass}"><option value="">(None)</option>${teamOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Birthdate</label><input id="f-ep-birth" type="date" value="${p.birthdate || ''}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Position</label><input id="f-ep-pos" type="text" value="${p.position || ''}" class="${inputClass}"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'team') {
            const t = db.teams.find((x) => x.id === id);
            if (!t) return setStatus('Team not found.');
            titleEl.innerText = `EDIT TEAM: ${t.name}`;
            const clubOpts = db.clubs.map((c) => `<option value="${c.id}" ${c.id === t.clubId ? 'selected' : ''}>${c.name}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'team', ${t.id})" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Team Name</label><input id="f-et-name" type="text" required value="${t.name}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Club</label><select id="f-et-club" class="${inputClass}"><option value="">(None)</option>${clubOpts}</select></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'club') {
            const c = db.clubs.find((x) => x.id === id);
            if (!c) return setStatus('Club not found.');
            titleEl.innerText = `EDIT CLUB: ${c.name}`;
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'club', ${c.id})" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Club Name</label><input id="f-ec-name" type="text" required value="${c.name}" class="${inputClass}"></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'tournament') {
            const tr = db.tournaments.find((x) => x.id === id);
            if (!tr) return setStatus('Tournament not found.');
            titleEl.innerText = `EDIT TOURNAMENT: ${tr.name}`;
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'tournament', ${tr.id})" class="flex flex-col gap-4"><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament Name</label><input id="f-etr-name" type="text" required value="${tr.name}" class="${inputClass}"></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-etr-loc" type="text" value="${tr.location || ''}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Date</label><input id="f-etr-date" type="date" value="${tr.date || ''}" class="${inputClass}"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        } else if (entity === 'match') {
            const m = db.matches.find((x) => x.id === id);
            if (!m) return setStatus('Match not found.');
            titleEl.innerText = 'EDIT MATCH FIXTURE';
            const teamOpts = (selected) => db.teams.map((t) => `<option value="${t.id}" ${t.id === selected ? 'selected' : ''}>${t.name}</option>`).join('');
            const tournOpts = db.tournaments.map((tr) => `<option value="${tr.id}" ${tr.id === m.tournId ? 'selected' : ''}>${tr.name}</option>`).join('');
            bodyEl.innerHTML = `<form onsubmit="ui.submitEdit(event, 'match', ${m.id})" class="flex flex-col gap-4"><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Home Team</label><select id="f-em-home" required class="${inputClass}">${teamOpts(m.homeId)}</select></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Away Team</label><select id="f-em-away" required class="${inputClass}">${teamOpts(m.awayId)}</select></div></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Tournament</label><select id="f-em-tourn" class="${inputClass}"><option value="">(None / Friendly)</option>${tournOpts}</select></div><div class="grid grid-cols-2 gap-3"><div><label class="block text-xs font-medium text-slate-300 mb-1">Date</label><input id="f-em-date" type="date" value="${m.date || ''}" class="${inputClass}"></div><div><label class="block text-xs font-medium text-slate-300 mb-1">Location</label><input id="f-em-loc" type="text" value="${m.location || ''}" class="${inputClass}"></div></div><button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button></form>`;
        }
        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    async submitAddTeam(e) {
        e.preventDefault();
        const name = document.getElementById('f-team-name').value.trim();
        const clubId = parseInt(document.getElementById('f-team-club').value, 10) || null;
        if (!name) return;
        try { await api.post('/api/teams', { name, clubId }); setStatus(`Team "${name}" created.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddClub(e) {
        e.preventDefault();
        const name = document.getElementById('f-club-name').value.trim();
        if (!name) return;
        try { await api.post('/api/clubs', { name }); setStatus(`Club "${name}" created.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddPlayer(e) {
        e.preventDefault();
        const fname = document.getElementById('f-p-fname').value.trim();
        const lname = document.getElementById('f-p-lname').value.trim();
        const teamId = parseInt(document.getElementById('f-p-team').value, 10) || null;
        const birthdate = document.getElementById('f-p-birth').value;
        const position = document.getElementById('f-p-pos').value.trim() || 'Shooter / Wing';
        if (!fname) return;
        try {
            await api.post('/api/players', { fname, lname, teamId, birthdate, position, appearances: 0, wins: 0, losses: 0, draws: 0, totalPoints: 0, avgPoints: 0, highestMatch: null, lowestMatch: null, matches: [] });
            setStatus(`Player "${fname} ${lname}" added successfully.`); ui.closeModal();
        } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddMatch(e) {
        e.preventDefault();
        const homeId = parseInt(document.getElementById('f-m-home').value, 10);
        const awayId = parseInt(document.getElementById('f-m-away').value, 10);
        const tournId = parseInt(document.getElementById('f-m-tourn').value, 10) || null;
        const date = document.getElementById('f-m-date').value || 'TBD';
        const location = document.getElementById('f-m-loc').value.trim() || 'Unspecified';
        if (!Number.isFinite(homeId) || !Number.isFinite(awayId)) return;
        try { await api.post('/api/matches', { homeId, awayId, tournId, date, location }); setStatus('Match fixture created.'); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitAddTournament(e) {
        e.preventDefault();
        const name = document.getElementById('f-tr-name').value.trim();
        const location = document.getElementById('f-tr-loc').value.trim() || 'Unspecified';
        const date = document.getElementById('f-tr-date').value || 'TBD';
        if (!name) return;
        try { await api.post('/api/tournaments', { name, location, date }); setStatus(`Tournament "${name}" created.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },
    async submitEdit(e, entity, id) {
        e.preventDefault();
        const value = (elId) => document.getElementById(elId).value;
        const payload = {};
        if (entity === 'player') { payload.fname = value('f-ep-fname').trim(); payload.lname = value('f-ep-lname').trim(); payload.teamId = parseInt(value('f-ep-team'), 10) || null; payload.birthdate = value('f-ep-birth'); payload.position = value('f-ep-pos').trim(); }
        else if (entity === 'team') { payload.name = value('f-et-name').trim(); payload.clubId = parseInt(value('f-et-club'), 10) || null; }
        else if (entity === 'club') { payload.name = value('f-ec-name').trim(); }
        else if (entity === 'tournament') { payload.name = value('f-etr-name').trim(); payload.location = value('f-etr-loc').trim() || 'Unspecified'; payload.date = value('f-etr-date') || 'TBD'; }
        else if (entity === 'match') { payload.homeId = parseInt(value('f-em-home'), 10); payload.awayId = parseInt(value('f-em-away'), 10); payload.tournId = parseInt(value('f-em-tourn'), 10) || null; payload.date = value('f-em-date') || 'TBD'; payload.location = value('f-em-loc').trim() || 'Unspecified'; }

        try { await api.put(`/api/${PLURAL[entity]}/${id}`, payload); setStatus(`${entity.toUpperCase()} updated for everyone.`); ui.closeModal(); } catch (err) { setStatus(`Error: ${err.message}`); }
    },

    refreshCurrentView() {
        if (!currentView) return;
        if (currentView.kind === 'browse') this.openBrowser(currentView.type);
        else if (currentView.kind === 'profile') this.openPlayerProfile(currentView.id);
    },
    closeModal() {
        currentView = null;
        document.getElementById('modal-backdrop').classList.add('hidden');
    }
};

// ---------------------------------------------------------------------
// Right-click context menu
// ---------------------------------------------------------------------
let activePlayerId = null;
const ctxMenu = document.getElementById('context-menu');

function showContextMenu(x, y, playerId) {
    activePlayerId = playerId;
    ctxMenu.style.left = `${Math.min(x, window.innerWidth - 220)}px`;
    ctxMenu.style.top = `${Math.min(y, window.innerHeight - 120)}px`;
    ctxMenu.classList.remove('hidden');
}

document.getElementById('ctx-btn-profile').addEventListener('click', () => {
    ctxMenu.classList.add('hidden');
    if (activePlayerId) ui.openPlayerProfile(activePlayerId);
});

document.getElementById('ctx-btn-edit').addEventListener('click', () => {
    ctxMenu.classList.add('hidden');
    if (activePlayerId) ui.openEditForm('player', activePlayerId);
});

document.addEventListener('click', () => ctxMenu.classList.add('hidden'));

// ---------------------------------------------------------------------
// Status bar + live sync
// ---------------------------------------------------------------------
function setStatus(msg) {
    const bar = document.getElementById('status-bar');
    if (!bar) return;
    bar.innerText = msg;
    setTimeout(() => { bar.innerText = 'Ready.'; }, 4000);
}

async function pollForUpdates() {
    try {
        const res = await fetch('/api/version', { cache: 'no-store' });
        if (!res.ok) return;
        const { version } = await res.json();
        if (version === serverVersion) return;
        await api.get('/api/state');
        ui.applyThemeAndLayout();
        ui.refreshCurrentView();
    } catch {}
}

document.addEventListener('DOMContentLoaded', async () => {
    setStatus('Connecting to server…');
    try {
        await api.get('/api/state');
        ui.applyThemeAndLayout();
        setStatus('Connected — shared data loaded.');
    } catch (err) {
        setStatus(`Cannot reach server: ${err.message}`);
        return;
    }
    setInterval(pollForUpdates, 4000);
});