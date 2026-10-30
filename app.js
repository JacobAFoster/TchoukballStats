// --- App Settings State ---
const appSettings = {
    pointsWin: 3,
    pointsDraw: 1,
    pointsLoss: 0,
    cardOrder: ['browse', 'add', 'edit', 'remove'],
    themeColor: 'indigo', // 'indigo', 'emerald', 'amber', 'rose'
    focusTournamentId: 501
};

// --- In-Memory Database State ---
const db = {
    clubs: [
        { id: 1, name: "Geneva Tchoukball Club" },
        { id: 2, name: "Taipei Titans Club" },
        { id: 3, name: "London Rampage Club" }
    ],
    teams: [
        { id: 101, name: "Geneva Dragons", clubId: 1 },
        { id: 102, name: "Taipei Lightning", clubId: 2 },
        { id: 103, name: "London Knights", clubId: 3 }
    ],
    players: [
        { 
            id: 1, 
            fname: "Alex", 
            lname: "Rivera", 
            teamId: 101, 
            birthdate: "2001-05-14", 
            position: "Shooter / Right Wing",
            appearances: 18,
            wins: 14,
            losses: 3,
            draws: 1,
            totalPoints: 162,
            avgPoints: 9.0,
            highestMatch: { points: 16, opponent: "Taipei Lightning (2026-02-10)" },
            lowestMatch: { points: 4, opponent: "Lausanne Wildcats (2025-11-04)" },
            matches: [
                { matchup: "Geneva Dragons vs Taipei Lightning", date: "2026-02-10", points: 16 },
                { matchup: "Geneva Dragons vs Zurich Falcons", date: "2026-01-22", points: 11 },
                { matchup: "Geneva Dragons vs Lausanne Wildcats", date: "2025-11-04", points: 4 }
            ]
        },
        { 
            id: 2, 
            fname: "Chen", 
            lname: "Wei-Ting", 
            teamId: 102, 
            birthdate: "1999-11-20", 
            position: "Centre Defender",
            appearances: 22,
            wins: 19,
            losses: 2,
            draws: 1,
            totalPoints: 110,
            avgPoints: 5.0,
            highestMatch: { points: 9, opponent: "Geneva Dragons (2026-02-10)" },
            lowestMatch: { points: 2, opponent: "Tokyo Strikers (2025-09-18)" },
            matches: [
                { matchup: "Taipei Lightning vs Geneva Dragons", date: "2026-02-10", points: 9 },
                { matchup: "Taipei Lightning vs Tokyo Strikers", date: "2025-09-18", points: 2 }
            ]
        },
        {
            id: 3,
            fname: "Sarah",
            lname: "Jenkins",
            teamId: 103,
            birthdate: "2003-02-18",
            position: "Left Wing Shooter",
            appearances: 12,
            wins: 8,
            losses: 4,
            draws: 0,
            totalPoints: 96,
            avgPoints: 8.0,
            highestMatch: { points: 14, opponent: "Geneva Dragons (2026-01-05)" },
            lowestMatch: { points: 3, opponent: "Taipei Lightning (2025-12-12)" },
            matches: [
                { matchup: "London Knights vs Geneva Dragons", date: "2026-01-05", points: 14 }
            ]
        }
    ],
    tournaments: [
        { id: 501, name: "World Championship 2026", date: "2026-08-12", location: "Geneva, Switzerland" },
        { id: 502, name: "European Nations Cup", date: "2025-10-15", location: "London, UK" }
    ],
    matches: [
        { id: 1001, homeId: 101, awayId: 102, date: "2026-02-10", tournId: 501, location: "Geneva Arena" },
        { id: 1002, homeId: 103, awayId: 101, date: "2026-01-05", tournId: 502, location: "London Sports Hall" }
    ]
};

// --- Core UI Controller ---
const ui = {
    // --- Application Settings Modal ---
    openSettings() {
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');

        titleEl.innerText = 'Application Settings';

        bodyEl.innerHTML = `
            <form onsubmit="ui.saveSettings(event)" class="flex flex-col gap-5">
                
                <!-- 1. League Points Config -->
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

                <!-- 2. Action Card Order -->
                <div class="border-t border-slate-800 pt-4">
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">2. Action Card Order</h4>
                    <select id="s-card-order" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        <option value="browse,add,edit,remove" ${appSettings.cardOrder.join(',') === 'browse,add,edit,remove' ? 'selected' : ''}>Standard (Browse → Add → Edit → Remove)</option>
                        <option value="add,browse,edit,remove" ${appSettings.cardOrder.join(',') === 'add,browse,edit,remove' ? 'selected' : ''}>Data Entry First (Add → Browse → Edit → Remove)</option>
                        <option value="edit,remove,browse,add" ${appSettings.cardOrder.join(',') === 'edit,remove,browse,add' ? 'selected' : ''}>Management First (Edit → Remove → Browse → Add)</option>
                    </select>
                </div>

                <!-- 3. Theme & Colors -->
                <div class="border-t border-slate-800 pt-4">
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">3. Theme Accent Color</h4>
                    <select id="s-theme-color" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                        <option value="indigo" ${appSettings.themeColor === 'indigo' ? 'selected' : ''}>Indigo Dark Modern (Default)</option>
                        <option value="emerald" ${appSettings.themeColor === 'emerald' ? 'selected' : ''}>Emerald Sports Green</option>
                        <option value="amber" ${appSettings.themeColor === 'amber' ? 'selected' : ''}>Amber Gold Classic</option>
                        <option value="rose" ${appSettings.themeColor === 'rose' ? 'selected' : ''}>Rose Crimson High-Contrast</option>
                    </select>
                </div>

                <!-- 4. Database Backup & Download -->
                <div class="border-t border-slate-800 pt-4">
                    <h4 class="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-2">4. Database Backup & Restore</h4>
                    <div class="flex gap-3">
                        <button type="button" onclick="ui.downloadDatabaseBackup()" class="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">
                            Download Backup (.json)
                        </button>
                        <button type="button" onclick="ui.resetDatabase()" class="flex-1 py-2.5 rounded-xl bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/40 text-xs font-medium transition">
                            Reset Database
                        </button>
                    </div>
                </div>

                <button type="submit" class="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition mt-2">
                    Save Settings
                </button>
            </form>
        `;

        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    saveSettings(e) {
        e.preventDefault();
        
        appSettings.pointsWin = parseInt(document.getElementById('s-pts-win').value) || 3;
        appSettings.pointsDraw = parseInt(document.getElementById('s-pts-draw').value) || 1;
        appSettings.pointsLoss = parseInt(document.getElementById('s-pts-loss').value) || 0;
        
        const cardOrderVal = document.getElementById('s-card-order').value;
        appSettings.cardOrder = cardOrderVal.split(',');
        appSettings.themeColor = document.getElementById('s-theme-color').value;

        ui.applyThemeAndLayout();

        setStatus('Settings applied successfully.');
        ui.closeModal();
    },

    applyThemeAndLayout() {
        document.body.className = `p-4 md:p-8 flex flex-col min-h-screen theme-${appSettings.themeColor}`;

        const grid = document.getElementById('action-cards-grid');
        if (grid) {
            appSettings.cardOrder.forEach(cardKey => {
                const cardEl = grid.querySelector(`[data-card="${cardKey}"]`);
                if (cardEl) {
                    grid.appendChild(cardEl);
                }
            });
        }
    },

    downloadDatabaseBackup() {
        const backupData = {
            settings: appSettings,
            database: db,
            timestamp: new Date().toISOString()
        };
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(backupData, null, 2));
        const dlAnchorElem = document.createElement('a');
        dlAnchorElem.setAttribute("href", dataStr);
        dlAnchorElem.setAttribute("download", `tchoukball_db_backup_${Date.now()}.json`);
        dlAnchorElem.click();
        setStatus('Database backup downloaded.');
    },

    resetDatabase() {
        if (confirm("Reset all database records to initial default values?")) {
            location.reload();
        }
    },

    // --- Browser Tables ---
    openBrowser(type) {
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');

        if (type === 'players') {
            titleEl.innerText = `Browse Players`;
            let rows = db.players.map(p => {
                const team = db.teams.find(t => t.id === p.teamId)?.name || 'No Team';
                return `
                    <tr data-player-id="${p.id}" class="player-row border-b border-slate-800/80 hover:bg-indigo-600/10 cursor-pointer transition">
                        <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${p.id}</td>
                        <td class="py-3 px-4 font-medium text-slate-100">${p.fname} ${p.lname}</td>
                        <td class="py-3 px-4 text-slate-300">${team}</td>
                        <td class="py-3 px-4 text-xs text-slate-400">${p.position || 'Not Set'}</td>
                    </tr>
                `;
            }).join('');

            bodyEl.innerHTML = `
                <p class="text-xs text-amber-300/80 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl mb-4">
                    <strong>Tip:</strong> Right-click on any player row to view their full profile and career stats.
                </p>
                <div class="overflow-x-auto rounded-xl border border-slate-800">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            <tr>
                                <th class="py-3 px-4">ID</th>
                                <th class="py-3 px-4">Player Name</th>
                                <th class="py-3 px-4">Team</th>
                                <th class="py-3 px-4">Position</th>
                            </tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No players found.</td></tr>'}</tbody>
                    </table>
                </div>
            `;

            setTimeout(() => {
                document.querySelectorAll('.player-row').forEach(row => {
                    row.addEventListener('contextmenu', (e) => {
                        e.preventDefault();
                        const pId = parseInt(row.getAttribute('data-player-id'));
                        showContextMenu(e.clientX, e.clientY, pId);
                    });
                });
            }, 50);

        } else if (type === 'teams') {
            titleEl.innerText = `Browse Teams`;
            let rows = db.teams.map(t => {
                const club = db.clubs.find(c => c.id === t.clubId)?.name || 'No Club';
                return `
                    <tr class="border-b border-slate-800/80 hover:bg-slate-800/40">
                        <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${t.id}</td>
                        <td class="py-3 px-4 font-medium text-slate-100">${t.name}</td>
                        <td class="py-3 px-4 text-slate-300">${club}</td>
                    </tr>
                `;
            }).join('');

            bodyEl.innerHTML = `
                <div class="overflow-x-auto rounded-xl border border-slate-800">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase">
                            <tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Team Name</th><th class="py-3 px-4">Club</th></tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="3" class="p-4 text-center text-slate-500">No teams found.</td></tr>'}</tbody>
                    </table>
                </div>
            `;
        } else if (type === 'clubs') {
            titleEl.innerText = `Browse Clubs`;
            let rows = db.clubs.map(c => `
                <tr class="border-b border-slate-800/80 hover:bg-slate-800/40">
                    <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${c.id}</td>
                    <td class="py-3 px-4 font-medium text-slate-100">${c.name}</td>
                </tr>
            `).join('');

            bodyEl.innerHTML = `
                <div class="overflow-x-auto rounded-xl border border-slate-800">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase">
                            <tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Club Name</th></tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="2" class="p-4 text-center text-slate-500">No clubs found.</td></tr>'}</tbody>
                    </table>
                </div>
            `;
        } else if (type === 'matches') {
            titleEl.innerText = `Browse Matches`;
            let rows = db.matches.map(m => {
                const home = db.teams.find(t => t.id === m.homeId)?.name || 'Home';
                const away = db.teams.find(t => t.id === m.awayId)?.name || 'Away';
                const tourn = db.tournaments.find(tr => tr.id === m.tournId)?.name || 'Exhibition';
                return `
                    <tr class="border-b border-slate-800/80 hover:bg-slate-800/40">
                        <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${m.id}</td>
                        <td class="py-3 px-4 font-medium text-slate-100">${home} vs ${away}</td>
                        <td class="py-3 px-4 text-slate-300">${tourn}</td>
                        <td class="py-3 px-4 text-xs text-slate-400">${m.date}</td>
                    </tr>
                `;
            }).join('');

            bodyEl.innerHTML = `
                <div class="overflow-x-auto rounded-xl border border-slate-800">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase">
                            <tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Fixture</th><th class="py-3 px-4">Tournament</th><th class="py-3 px-4">Date</th></tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No matches found.</td></tr>'}</tbody>
                    </table>
                </div>
            `;
        } else if (type === 'tournaments') {
            titleEl.innerText = `Browse Tournaments`;
            let rows = db.tournaments.map(tr => `
                <tr class="border-b border-slate-800/80 hover:bg-slate-800/40">
                    <td class="py-3 px-4 font-mono text-xs text-indigo-300">#${tr.id}</td>
                    <td class="py-3 px-4 font-medium text-slate-100">${tr.name}</td>
                    <td class="py-3 px-4 text-slate-300">${tr.location}</td>
                    <td class="py-3 px-4 text-xs text-slate-400">${tr.date}</td>
                </tr>
            `).join('');

            bodyEl.innerHTML = `
                <div class="overflow-x-auto rounded-xl border border-slate-800">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase">
                            <tr><th class="py-3 px-4">ID</th><th class="py-3 px-4">Tournament Name</th><th class="py-3 px-4">Location</th><th class="py-3 px-4">Date</th></tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="4" class="p-4 text-center text-slate-500">No tournaments found.</td></tr>'}</tbody>
                    </table>
                </div>
            `;
        } else if (type === 'rosters') {
            titleEl.innerText = `Match Rosters`;
            let rows = db.players.map(p => {
                const team = db.teams.find(t => t.id === p.teamId)?.name || 'Unassigned';
                return `
                    <tr class="border-b border-slate-800/80 hover:bg-slate-800/40">
                        <td class="py-3 px-4 font-medium text-slate-100">${p.fname} ${p.lname}</td>
                        <td class="py-3 px-4 text-indigo-300">${team}</td>
                        <td class="py-3 px-4 text-xs text-slate-400">${p.appearances} match appearances</td>
                    </tr>
                `;
            }).join('');

            bodyEl.innerHTML = `
                <div class="overflow-x-auto rounded-xl border border-slate-800">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-900/80 text-xs font-semibold text-slate-400 uppercase">
                            <tr><th class="py-3 px-4">Player</th><th class="py-3 px-4">Assigned Team</th><th class="py-3 px-4">Roster Count</th></tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            `;
        }

        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    // --- Player Profile Modal ---
    openPlayerProfile(playerId) {
        const p = db.players.find(x => x.id === playerId);
        if (!p) return;

        const team = db.teams.find(t => t.id === p.teamId)?.name || 'No Team';
        const club = db.clubs.find(c => c.id === (db.teams.find(t => t.id === p.teamId)?.clubId))?.name || 'No Club';

        document.getElementById('modal-title').innerText = `Player Profile: ${p.fname} ${p.lname}`;
        
        let matchRows = (p.matches || []).map(m => `
            <tr class="border-b border-slate-800/60 hover:bg-slate-800/30">
                <td class="py-2.5 px-3 text-slate-200 font-medium">${m.matchup}</td>
                <td class="py-2.5 px-3 text-slate-400 text-xs">${m.date}</td>
                <td class="py-2.5 px-3 text-indigo-300 font-bold font-mono text-right">${m.points} pts</td>
            </tr>
        `).join('');

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
                    <div class="bg-indigo-950/20 border border-indigo-500/30 p-3.5 rounded-xl">
                        <span class="text-xs text-indigo-300 uppercase font-bold tracking-wider">Total Points</span>
                        <div class="text-2xl font-extrabold text-white mt-1">${p.totalPoints || 0} <span class="text-xs font-normal text-slate-400">pts</span></div>
                    </div>
                    <div class="bg-indigo-950/20 border border-indigo-500/30 p-3.5 rounded-xl">
                        <span class="text-xs text-indigo-300 uppercase font-bold tracking-wider">Avg Points / Match</span>
                        <div class="text-2xl font-extrabold text-white mt-1">${p.avgPoints || 0.0} <span class="text-xs font-normal text-slate-400">pts/gm</span></div>
                    </div>
                </div>

                <div class="bg-slate-900/50 border border-slate-800 p-3.5 rounded-xl flex flex-col gap-2 text-xs">
                    <div class="flex items-center justify-between">
                        <span class="text-slate-400">Highest Scoring Match:</span>
                        <strong class="text-amber-300 font-mono">${p.highestMatch ? p.highestMatch.points + ' pts (' + p.highestMatch.opponent + ')' : 'N/A'}</strong>
                    </div>
                    <div class="flex items-center justify-between border-t border-slate-800/80 pt-2">
                        <span class="text-slate-400">Lowest Scoring Match:</span>
                        <strong class="text-slate-300 font-mono">${p.lowestMatch ? p.lowestMatch.points + ' pts (' + p.lowestMatch.opponent + ')' : 'N/A'}</strong>
                    </div>
                </div>

                <div>
                    <h4 class="text-xs font-bold uppercase text-slate-400 tracking-wider mb-2">Match Roster History</h4>
                    <div class="overflow-x-auto rounded-xl border border-slate-800">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-slate-900/80 text-slate-400 uppercase font-semibold">
                                <tr>
                                    <th class="py-2.5 px-3">Matchup</th>
                                    <th class="py-2.5 px-3">Date</th>
                                    <th class="py-2.5 px-3 text-right">Points Scored</th>
                                </tr>
                            </thead>
                            <tbody>${matchRows || '<tr><td colspan="3" class="p-3 text-center text-slate-500">No match records found.</td></tr>'}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    // --- Form Handlers (ADD) ---
    openForm(action) {
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');

        if (action === 'add-team') {
            titleEl.innerText = 'ADD TEAM';
            const clubOpts = db.clubs.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            bodyEl.innerHTML = `
                <form onsubmit="ui.submitAddTeam(event)" class="flex flex-col gap-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Team Name</label>
                        <input id="f-team-name" type="text" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500" placeholder="e.g. Geneva Dragons">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Club</label>
                        <select id="f-team-club" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
                            <option value="">(None)</option>
                            ${clubOpts}
                        </select>
                    </div>
                    <button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Team</button>
                </form>
            `;
        } else if (action === 'add-club') {
            titleEl.innerText = 'ADD CLUB';
            bodyEl.innerHTML = `
                <form onsubmit="ui.submitAddClub(event)" class="flex flex-col gap-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Club Name</label>
                        <input id="f-club-name" type="text" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500" placeholder="e.g. Lausanne Tchoukball Club">
                    </div>
                    <button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Club</button>
                </form>
            `;
        } else if (action === 'add-player') {
            titleEl.innerText = 'ADD PLAYER';
            const teamOpts = db.teams.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
            bodyEl.innerHTML = `
                <form onsubmit="ui.submitAddPlayer(event)" class="flex flex-col gap-4">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-medium text-slate-300 mb-1">First Name</label>
                            <input id="f-p-fname" type="text" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500" placeholder="First Name">
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-300 mb-1">Surname</label>
                            <input id="f-p-lname" type="text" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500" placeholder="Surname">
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Assigned Team</label>
                        <select id="f-p-team" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
                            <option value="">(None)</option>
                            ${teamOpts}
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Birthdate (YYYY-MM-DD)</label>
                        <input id="f-p-birth" type="date" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
                    </div>
                    <button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Player</button>
                </form>
            `;
        } else if (action === 'add-match') {
            titleEl.innerText = 'ADD MATCH FIXTURE';
            const teamOpts = db.teams.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
            const tournOpts = db.tournaments.map(tr => `<option value="${tr.id}">${tr.name}</option>`).join('');
            bodyEl.innerHTML = `
                <form onsubmit="ui.submitAddMatch(event)" class="flex flex-col gap-4">
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs font-medium text-slate-300 mb-1">Home Team</label>
                            <select id="f-m-home" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">${teamOpts}</select>
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-300 mb-1">Away Team</label>
                            <select id="f-m-away" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">${teamOpts}</select>
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Tournament</label>
                        <select id="f-m-tourn" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
                            <option value="">(None / Friendly)</option>
                            ${tournOpts}
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Date</label>
                        <input id="f-m-date" type="date" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
                    </div>
                    <button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Create Match</button>
                </form>
            `;
        } else if (action === 'add-tournament') {
            titleEl.innerText = 'ADD TOURNAMENT';
            bodyEl.innerHTML = `
                <form onsubmit="ui.submitAddTournament(event)" class="flex flex-col gap-4">
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Tournament Name</label>
                        <input id="f-tr-name" type="text" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500" placeholder="e.g. World Cup 2026">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Location</label>
                        <input id="f-tr-loc" type="text" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500" placeholder="e.g. Geneva, Switzerland">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-slate-300 mb-1">Start Date</label>
                        <input id="f-tr-date" type="date" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
                    </div>
                    <button type="submit" class="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">Add Tournament</button>
                </form>
            `;
        }

        document.getElementById('modal-backdrop').classList.remove('hidden');
    },

    // --- Selector Handlers (EDIT / REMOVE) ---
    openSelector(mode) {
        const titleEl = document.getElementById('modal-title');
        const bodyEl = document.getElementById('modal-body');

        const [action, entity] = mode.split('-');
        titleEl.innerText = `${action.toUpperCase()} ${entity.toUpperCase()}`;

        let options = [];
        if (entity === 'player') options = db.players.map(p => ({ id: p.id, name: `${p.fname} ${p.lname}` }));
        if (entity === 'team') options = db.teams.map(t => ({ id: t.id, name: t.name }));
        if (entity === 'club') options = db.clubs.map(c => ({ id: c.id, name: c.name }));
        if (entity === 'tournament') options = db.tournaments.map(tr => ({ id: tr.id, name: tr.name }));
        if (entity === 'match') options = db.matches.map(m => ({
            id: m.id, 
            name: `${db.teams.find(t=>t.id===m.homeId)?.name || 'Home'} vs ${db.teams.find(t=>t.id===m.awayId)?.name || 'Away'} (${m.date})`
        }));

        const optsHtml = options.map(o => `<option value="${o.id}">${o.name}</option>`).join('');

        bodyEl.innerHTML = `
            <form onsubmit="ui.handleSelectorSubmit(event, '${action}', '${entity}')" class="flex flex-col gap-4">
                <div>
                    <label class="block text-xs font-medium text-slate-300 mb-1">Select ${entity.toUpperCase()}</label>
                    <select id="f-select-id" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500">
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

    handleSelectorSubmit(e, action, entity) {
        e.preventDefault();
        const selectedId = parseInt(document.getElementById('f-select-id').value);
        if (!selectedId) return;

        if (action === 'remove') {
            if (entity === 'player') db.players = db.players.filter(p => p.id !== selectedId);
            if (entity === 'team') db.teams = db.teams.filter(t => t.id !== selectedId);
            if (entity === 'club') db.clubs = db.clubs.filter(c => c.id !== selectedId);
            if (entity === 'tournament') db.tournaments = db.tournaments.filter(tr => tr.id !== selectedId);
            if (entity === 'match') db.matches = db.matches.filter(m => m.id !== selectedId);

            setStatus(`${entity.toUpperCase()} deleted successfully.`);
            ui.closeModal();
        } else if (action === 'edit') {
            if (entity === 'player') {
                const p = db.players.find(x => x.id === selectedId);
                const titleEl = document.getElementById('modal-title');
                titleEl.innerText = `EDIT PLAYER: ${p.fname} ${p.lname}`;
                
                const teamOpts = db.teams.map(t => `<option value="${t.id}" ${t.id === p.teamId ? 'selected' : ''}>${t.name}</option>`).join('');

                document.getElementById('modal-body').innerHTML = `
                    <form onsubmit="ui.submitEditPlayer(event, ${p.id})" class="flex flex-col gap-4">
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-xs font-medium text-slate-300 mb-1">First Name</label>
                                <input id="f-ep-fname" type="text" value="${p.fname}" required class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-slate-300 mb-1">Surname</label>
                                <input id="f-ep-lname" type="text" value="${p.lname}" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">
                            </div>
                        </div>
                        <div>
                            <label class="block text-xs font-medium text-slate-300 mb-1">Team</label>
                            <select id="f-ep-team" class="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm">${teamOpts}</select>
                        </div>
                        <button type="submit" class="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm transition">Save Changes</button>
                    </form>
                `;
            } else {
                setStatus(`Editing ${entity} saved.`);
                ui.closeModal();
            }
        }
    },

    submitAddTeam(e) {
        e.preventDefault();
        const name = document.getElementById('f-team-name').value;
        const clubId = parseInt(document.getElementById('f-team-club').value) || null;
        db.teams.push({ id: Date.now(), name, clubId });
        setStatus(`Team "${name}" created.`);
        ui.closeModal();
    },

    submitAddClub(e) {
        e.preventDefault();
        const name = document.getElementById('f-club-name').value;
        db.clubs.push({ id: Date.now(), name });
        setStatus(`Club "${name}" created.`);
        ui.closeModal();
    },

    submitAddPlayer(e) {
        e.preventDefault();
        const fname = document.getElementById('f-p-fname').value;
        const lname = document.getElementById('f-p-lname').value;
        const teamId = parseInt(document.getElementById('f-p-team').value) || null;
        const birthdate = document.getElementById('f-p-birth').value;

        db.players.push({
            id: Date.now(),
            fname, lname, teamId, birthdate,
            position: "Shooter / Wing",
            appearances: 0, wins: 0, losses: 0, draws: 0, totalPoints: 0, avgPoints: 0.0,
            matches: []
        });

        setStatus(`Player "${fname} ${lname}" added successfully.`);
        ui.closeModal();
    },

    submitAddMatch(e) {
        e.preventDefault();
        const homeId = parseInt(document.getElementById('f-m-home').value);
        const awayId = parseInt(document.getElementById('f-m-away').value);
        const tournId = parseInt(document.getElementById('f-m-tourn').value) || null;
        const date = document.getElementById('f-m-date').value || 'TBD';

        db.matches.push({ id: Date.now(), homeId, awayId, tournId, date });
        setStatus("Match fixture created.");
        ui.closeModal();
    },

    submitAddTournament(e) {
        e.preventDefault();
        const name = document.getElementById('f-tr-name').value;
        const location = document.getElementById('f-tr-loc').value || 'Unspecified';
        const date = document.getElementById('f-tr-date').value || 'TBD';

        db.tournaments.push({ id: Date.now(), name, location, date });
        setStatus(`Tournament "${name}" created.`);
        ui.closeModal();
    },

    submitEditPlayer(e, id) {
        e.preventDefault();
        const p = db.players.find(x => x.id === id);
        if (p) {
            p.fname = document.getElementById('f-ep-fname').value;
            p.lname = document.getElementById('f-ep-lname').value;
            p.teamId = parseInt(document.getElementById('f-ep-team').value) || null;
            setStatus(`Player "${p.fname} ${p.lname}" updated.`);
        }
        ui.closeModal();
    },

    closeModal() {
        document.getElementById('modal-backdrop').classList.add('hidden');
    }
};

// --- Context Menu Handlers ---
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
    if (activePlayerId) ui.openSelector('edit-player');
});

document.addEventListener('click', () => ctxMenu.classList.add('hidden'));

// --- Status Message Bar & Initializer ---
function setStatus(msg) {
    const bar = document.getElementById('status-bar');
    if (bar) {
        bar.innerText = msg;
        setTimeout(() => { bar.innerText = 'Ready.'; }, 4000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    ui.applyThemeAndLayout();
});