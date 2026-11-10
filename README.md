
🐍 Phase 1: Python (Desktop) Release

Optimize the existing desktop core for stability, cross-platform compatibility, and easy deployment.
• Performance Optimization: Refactor local query logic (database.py, models.py) to reduce UI blocking during intense data-heavy entry.
• Asset Bundling: Convert scripts (main.py, tchoukball stats.py) into standalone executable binaries (.exe for Windows, .app for macOS).
• Installer Automation: Build an integrated native installer (using tools like PyInstaller combined with Inno Setup or Nullsoft) to handle configuration files automatically.

🌐 Phase 2: HTML/JS (Web) Release

Transform the platform into a decoupled web asset capable of running on local network servers or hosted on public cloud providers.
• Stateless Frontend: Migrate static files (index.html, style.css, app.js) to interact exclusively with unified JSON payloads.
• Backend Server Port: Finalize server.js or package.json configurations to cleanly run a local Node/Express backend that handles parallel file updates without conflicts.
• Local-First Option: Implement browser-based fallback storage so users can manage entire tournaments right from their browser when internet access is unavailable at the courts.

🛠️ Project Structure

The codebase is split into two logical targets to serve different distribution environments:
text

```text
├── 🐍 PYTHON ENVIRONMENT
│   ├── main.py                # Main application entrance
│   ├── tchoukball stats.py    # Legacy / core algorithmic processing
│   ├── config.py              # Local path variables & configurations
│   ├── database.py            # Local relational engine definitions
│   ├── models.py              # Data structures for players, teams, games
│   ├── dialogs.py             # Custom window prompts & user inputs
│   └── ui_components.py       # Custom visual layout templates
│
├── 🌐 WEB ENVIRONMENT
│   ├── index.html             # Main statistics dashboard layout
│   ├── style.css              # Dashboard theme & responsive designs
│   ├── app.js                 # Event tracking & state coordination
│   ├── server.js              # Node.js backend integration layer
│   ├── package.json           # Server dependencies
│   └── package-lock.json      # Dependency lockfile
│
└── 💾 DATA RESIDENCY
    └── data.json              # Shared structured flat-file database
```
