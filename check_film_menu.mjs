// Browser check of the Watch on YouTube menu on a game's own page, which is sealed and unlocked in the page (so the page's script runs again
// after the unlock). One tap must open the menu, and a tap elsewhere must close it. Run from this folder:
//   node check_film_menu.mjs
// puppeteer-core is looked up in PUPPETEER_CORE_DIR, else the Eagles Nest checkout's node_modules.
import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const puppeteer = (await import((process.env.PUPPETEER_CORE_DIR || path.join(os.homedir(), 'film-room-app/film-room/node_modules')) + '/puppeteer-core/lib/puppeteer/puppeteer-core.js')).default;
const chrome = [process.env.CHROME_PATH, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium'].find((p) => p && fs.existsSync(p));
const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'film-menu-')), 'event.html');
execFileSync('python3', ['-c', `
import sys; sys.path.insert(0, '.')
import generate_event_pages as ep, page_common, team_crypto, test_team_films as t
from datetime import datetime
e = t.game("a", 8, "08:00", "Stoney Creek"); e["uid"] = "u1"; e["home"] = True
now = datetime(2026, 11, 8, 20, 0, tzinfo=page_common.TORONTO)
html = ep.page(team_crypto.Sealer("pw-test").seal(ep.detail(e, [e], now, now.date(), {"u1": "https://youtu.be/AAA"}, {"u1": "https://youtu.be/PANO"})), "x")
open(sys.argv[1], "w").write(html)
`, file]);
let failed = 0;
const ok = (name, cond) => { if (!cond) failed++; console.log((cond ? 'PASS ' : 'FAIL ') + name); };
const b = await puppeteer.launch({ executablePath: chrome, headless: true });
const p = await b.newPage(); await p.setViewport({ width: 390, height: 700 });
await p.evaluateOnNewDocument(() => { try { localStorage.setItem('eagles-team-password', 'pw-test'); } catch (e) {} });
await p.goto('file://' + file);
await p.waitForSelector('.film-pick-btn', { timeout: 8000 });
await p.click('.film-pick-btn');
ok('one tap opens the menu', await p.$eval('.film-pick', (e) => e.classList.contains('is-open') && getComputedStyle(e.querySelector('.film-menu')).display === 'block'));
ok('the menu offers both videos', JSON.stringify(await p.$$eval('.film-menu a', (a) => a.map((x) => x.textContent))) === '["Follows play","Whole ice"]');
await p.click('body');
ok('a tap elsewhere closes it', await p.$eval('.film-pick', (e) => !e.classList.contains('is-open')));
await p.click('.film-pick-btn'); await p.keyboard.press('Escape');
ok('Escape closes it', await p.$eval('.film-pick', (e) => !e.classList.contains('is-open')));
await b.close();
process.exit(failed ? 1 : 0);
