// Draws the pictures a link shows when a page of the site is shared (iMessage, Slack, email, social): assets/share/<name>.png, 1200 x 630.
// They are committed; run this after changing the look or the words:
//   node make_share_cards.mjs
// Drawn in Chrome, light, with the club's crest and the Eagles Nest red. puppeteer-core is looked up in PUPPETEER_CORE_DIR, else the Film Room checkout's node_modules.
import fs from 'fs';
import os from 'os';
import path from 'path';

const puppeteer = (await import((process.env.PUPPETEER_CORE_DIR || path.join(os.homedir(), 'film-room-app/film-room/node_modules')) + '/puppeteer-core/lib/puppeteer/puppeteer-core.js')).default;
const chrome = [process.env.CHROME_PATH, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium'].find((p) => p && fs.existsSync(p));
if (!chrome) throw new Error('Chrome was not found. Set CHROME_PATH.');

const INK = '#080808', CRIMSON = '#e11d48';
const crest = 'data:image/svg+xml;base64,' + fs.readFileSync('assets/eagles-crest-red.svg').toString('base64');
const CARDS = {
  site: ['Toronto Eagles U11 AA', 'Eagles', 'Schedule, scores and standings'],
  schedule: ['Toronto Eagles U11 AA', 'Schedule', 'Games, rinks and results'],
  standings: ['Toronto Eagles U11 AA', 'Standings', 'Where every team sits'],
  playoffs: ['Toronto Eagles U11 AA', 'Playoffs', 'The path to the final'],
  statistics: ['Toronto Eagles U11 AA', 'Statistics', 'Goals, shots and special teams'],
  game: ['Toronto Eagles U11 AA', 'Game Day', 'Teams, time, rink and result'],
  team: ['Toronto Eagles U11 AA', 'Teams', 'Record, results and what is next'],
};
const html = ([eyebrow, title, line]) => `<!doctype html><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500&family=Oswald:wght@600;700&display=swap" rel="stylesheet"><style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;overflow:hidden;background:#faf9f7;font-family:"Oswald","Arial Narrow","Helvetica Neue",Arial,sans-serif;color:${INK};position:relative}
.glow{position:absolute;inset:0;background:radial-gradient(760px 480px at 22% 50%,rgba(225,29,72,.10),transparent 64%),radial-gradient(700px 400px at 100% 100%,rgba(225,29,72,.06),transparent 60%)}
.stripe{position:absolute;left:0;right:0;top:0;height:12px;background:${CRIMSON}}
.tile{position:absolute;left:88px;top:150px;width:330px;height:330px;border-radius:64px;background:#fff;box-shadow:0 24px 60px rgba(8,8,8,.16),0 0 0 1px rgba(8,8,8,.07)}
.crest{position:absolute;inset:44px;background:url(${crest}) center/contain no-repeat}
.text{position:absolute;left:480px;right:70px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center}
.eyebrow{font-weight:600;font-size:30px;letter-spacing:.22em;text-transform:uppercase;color:${CRIMSON};margin-bottom:22px}
h1{font-weight:700;font-size:${title.length > 8 ? 128 : 150}px;line-height:.95;letter-spacing:.015em;text-transform:uppercase;white-space:nowrap}
.rule{width:132px;height:8px;border-radius:4px;background:${CRIMSON};margin:34px 0 28px}
.line{font-family:"Barlow","Helvetica Neue",Arial,sans-serif;font-weight:400;font-size:40px;letter-spacing:.01em;color:#555a63}
</style><body><div class="glow"></div><div class="stripe"></div><div class="tile"><div class="crest"></div></div>
<div class="text"><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><div class="rule"></div><div class="line">${line}</div></div></body>`;

const b = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] });
for (const [name, c] of Object.entries(CARDS)) {
  const p = await b.newPage(); await p.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
  await p.setContent(html(c), { waitUntil: 'networkidle0', timeout: 20000 }).catch(() => {});
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: `assets/share/${name}.png` });
  await p.close();
}
await b.close();
console.log('wrote ' + Object.keys(CARDS).map((n) => `assets/share/${n}.png`).join(', '));
