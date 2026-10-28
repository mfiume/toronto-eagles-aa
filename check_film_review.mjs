// Browser check of the film review against a fixture game page (made-up video id, the video player's script stubbed, no real
// network call to the video host). Run from this folder:
//   node check_film_review.mjs [outdir for screenshots]
// puppeteer-core is looked up in PUPPETEER_CORE_DIR, else the Film Room checkout's node_modules.
import { createRequire } from 'module';
import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';

const require = createRequire(import.meta.url);
const puppeteer = require((process.env.PUPPETEER_CORE_DIR || path.join(os.homedir(), 'Development/film-room/node_modules')) + '/puppeteer-core');
const shots = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'film-review-'));
fs.mkdirSync(shots, { recursive: true });
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'film-fixture-'));
const info = JSON.parse(execFileSync('python3', ['test_film_review.py', '--fixture', dir], { encoding: 'utf8' }).trim().split('\n').pop());

let failed = 0;
const ok = (name, cond, extra = '') => { if (!cond) failed++; console.log((cond ? 'PASS ' : 'FAIL ') + name + (extra ? '  ' + extra : '')); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// Stands in for the video player's script. Records what the page asks of it.
const STUB = `
window.__yt = { created: 0, seeks: [], plays: 0, destroyed: 0, opts: null, ct: 0 };
window.YT = { Player: function (mount, opts) {
  var d = document.createElement('div'); d.id = 'stub-player'; d.style.background = '#101820'; d.style.color = '#9ab'; d.textContent = 'player';
  mount.parentNode.replaceChild(d, mount);
  window.__yt.created++; window.__yt.opts = opts;
  this.seekTo = function (s, a) { window.__yt.seeks.push([s, a]); window.__yt.ct = s; };
  this.playVideo = function () { window.__yt.plays++; };
  this.getCurrentTime = function () { return window.__yt.ct; };
  this.destroy = function () { window.__yt.destroyed++; };
  setTimeout(function () { opts.events.onReady({}); }, 0);
} };
setTimeout(function () { window.onYouTubeIframeAPIReady && window.onYouTubeIframeAPIReady(); }, 0);
`;

const b = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new' });

async function newPage(w, h, signedIn) {
  const p = await b.newPage();
  await p.setViewport({ width: w, height: h, deviceScaleFactor: 2 });
  p.hostRequests = [];
  await p.setRequestInterception(true);
  p.on('request', (r) => {
    const u = r.url();
    if (/youtu/i.test(u)) {
      p.hostRequests.push(u);
      if (u === 'https://www.youtube.com/iframe_api') return r.respond({ status: 200, contentType: 'application/javascript', body: STUB });
      return r.abort();
    }
    if (u.startsWith('file:')) return r.continue();
    return r.abort();
  });
  const url = (f) => 'file://' + path.join(dir, f);
  p.open = async (f) => {
    await p.goto(url(f));
    await p.evaluate((pw) => { if (pw) localStorage.setItem('eagles-team-password', pw); else localStorage.removeItem('eagles-team-password'); }, signedIn ? info.password : null);
    await p.reload();
  };
  return p;
}

const rowTexts = (p) => p.$$eval('.rv-row', (e) => e.map((x) => x.textContent.replace(/\s+/g, ' ').trim()));
const nowIndex = (p) => p.$$eval('.rv-row', (e) => e.findIndex((x) => x.classList.contains('is-now')));

// Logged out: nothing of the review, and no mention of the video anywhere.
{
  const p = await newPage(1100, 900, false);
  await p.open(info.moments); await wait(800);
  ok('logged out: no review layer', (await p.$('.rv')) === null);
  ok('logged out: no film links or button', (await p.$$('a.is-film, .match-actions a.film')).length === 0);
  ok('logged out: page source has no "youtu"', !(await p.content()).includes('youtu') && !(await p.content()).includes(info.id));
  ok('logged out: no request to the video host', p.hostRequests.length === 0);
  await p.close();
}

// Signed in, game with moments.
for (const [name, w, h] of [['desktop', 1100, 800], ['phone', 390, 800]]) {
  const p = await newPage(w, h, true);
  await p.open(info.moments);
  await p.waitForSelector('a.is-film', { timeout: 8000 });
  ok(name + ': nothing fetched from the video host before opening', p.hostRequests.length === 0);
  const mark = '.tl-dot[data-m="goal|1|3:16"]';
  await p.$eval(mark, (e) => e.focus());
  await p.click(mark);
  await p.waitForSelector('.rv #stub-player', { timeout: 5000 });
  ok(name + ': only the player script was requested, once', p.hostRequests.length === 1 && p.hostRequests[0] === 'https://www.youtube.com/iframe_api', JSON.stringify(p.hostRequests));
  const rows = await rowTexts(p);
  console.log('  rows:', JSON.stringify(rows));
  ok(name + ': nine rows, none for the unplaced penalty', rows.length === 9 && !rows.some((r) => r.includes('1:53')));
  const whens = await p.$$eval('.rv-row .sheet-when', (e) => e.map((x) => x.textContent.trim()));
  ok(name + ': game order by period then clock', JSON.stringify(whens) === JSON.stringify(['1st · 11:45', '1st · 7:10', '1st · 3:16', '2nd · 11:46', '2nd · 4:33', '2nd · 4:02', '3rd · 9:35', '3rd · 7:28', '3rd · 4:16']), whens.join(', '));
  ok(name + ': rows read goal score and penalty minutes', rows[0].includes('Goal') && /Goal.*\d.\d/.test(rows[0]) && /min/.test(rows[1]), rows[0] + ' | ' + rows[1]);
  ok(name + ': rows carry a team logo', (await p.$$eval('.rv-row .team-logo', (e) => e.length)) === 9);
  ok(name + ': opened at the mark (row 3 current, start=755)', (await nowIndex(p)) === 2 && (await p.evaluate(() => window.__yt.opts.playerVars.start)) === 755);
  const pv = await p.evaluate(() => window.__yt.opts.playerVars);
  ok(name + ': player settings', pv.rel === 0 && pv.modestbranding === 1 && pv.playsinline === 1 && pv.autoplay === 1, JSON.stringify(pv));
  ok(name + ': focus is inside the dialog', await p.evaluate(() => document.querySelector('.rv').contains(document.activeElement)));
  ok(name + ': page scroll locked and page inert', await p.evaluate(() => getComputedStyle(document.documentElement).overflow === 'hidden' && document.querySelector('.container').hasAttribute('inert')));
  const geo = await p.evaluate(() => { const f = document.querySelector('.rv-frame').getBoundingClientRect(), l = document.querySelector('.rv-list').getBoundingClientRect(), o = document.querySelector('.rv-open').getBoundingClientRect(); return { fw: f.width, fh: f.height, fx: f.x, fy: f.y, lx: l.x, ly: l.y, lh: l.height, lw: l.width, oy: o.y, sw: document.documentElement.scrollWidth, iw: innerWidth }; });
  console.log('  geometry', JSON.stringify(geo));
  ok(name + ': video is 16:9', Math.abs(geo.fw / geo.fh - 16 / 9) < 0.02);
  ok(name + ': no horizontal overflow', geo.sw <= geo.iw);
  if (w > 760) ok(name + ': list left of the video', geo.lx < geo.fx); else ok(name + ': video above the list', geo.fy < geo.ly && geo.lh > 150, 'list height ' + geo.lh);
  await wait(400);
  await p.screenshot({ path: path.join(shots, `review_${name}.png`) });

  // Click a row: the existing player seeks; no second player is built.
  const btns = await p.$$('.rv-row');
  await btns[4].click();
  const st = await p.evaluate(() => ({ seeks: window.__yt.seeks, plays: window.__yt.plays, created: window.__yt.created, href: document.querySelector('.rv-open').href }));
  ok(name + ': row click seeks the existing player to its second', JSON.stringify(st.seeks.slice(-1)) === '[[1400,true]]' && st.plays >= 1 && st.created === 1, JSON.stringify(st));
  ok(name + ': Open on YouTube link follows', st.href.endsWith('?t=1400'), st.href);
  ok(name + ': clicked row is current', (await nowIndex(p)) === 4);

  // Playback: the latest event at or before the current time is highlighted.
  await p.evaluate(() => { window.__yt.ct = 2100; window.__yt.opts.events.onStateChange({ data: 1 }); });
  await wait(900);
  ok(name + ': playing at 2100 s highlights the 2000 s goal', (await nowIndex(p)) === 6, 'index ' + await nowIndex(p));
  await p.evaluate(() => { window.__yt.ct = 50; });
  await wait(700);
  ok(name + ': before the first event nothing is highlighted', (await nowIndex(p)) === -1);
  await p.evaluate(() => { window.__yt.ct = 3000; });
  await wait(700);
  ok(name + ': after the last event the last row is highlighted', (await nowIndex(p)) === 8);
  await p.screenshot({ path: path.join(shots, `review_${name}_playing.png`) });
  await p.evaluate(() => window.__yt.opts.events.onStateChange({ data: 2 }));

  // Keyboard: Tab stays inside, Esc closes and returns focus to the mark.
  for (let i = 0; i < 14; i++) await p.keyboard.press('Tab');
  ok(name + ': Tab stays inside the dialog', await p.evaluate(() => document.querySelector('.rv').contains(document.activeElement)));
  await p.keyboard.press('Escape');
  ok(name + ': Esc closes the layer', (await p.$('.rv')) === null);
  ok(name + ': player destroyed, scroll and page restored', await p.evaluate(() => window.__yt.destroyed === 1 && getComputedStyle(document.documentElement).overflow !== 'hidden' && !document.querySelector('.container').hasAttribute('inert')));
  ok(name + ': focus returns to the mark', await p.evaluate((m) => document.activeElement === document.querySelector(m), mark));

  // Reopen from a list row on the sheet and from the film button; close button works.
  await p.$eval('li[data-m="penalty|2|4:02"] a.sheet-what', (e) => e.click());
  await p.waitForSelector('.rv');
  ok(name + ': a sheet row opens at its moment', (await nowIndex(p)) === 5 && (await p.evaluate(() => window.__yt.opts.playerVars.start)) === 1450);
  await p.click('.rv-close');
  ok(name + ': close button closes', (await p.$('.rv')) === null);
  await p.$eval('.match-actions a.film', (e) => e.click());
  await p.waitForSelector('.rv');
  ok(name + ': film button opens with the full list and nothing current', (await rowTexts(p)).length === 9 && (await nowIndex(p)) === -1 && (await p.evaluate(() => !('start' in window.__yt.opts.playerVars))));
  await wait(400);
  await p.screenshot({ path: path.join(shots, `review_${name}_button.png`) });
  await p.keyboard.press('Escape');
  ok(name + ': video host was asked for the player script once in total', p.hostRequests.filter((u) => u.includes('iframe_api')).length === 1);
  await p.close();
}

// Signed in, a film with no placed moments: the player alone.
for (const [name, w, h] of [['desktop', 1100, 800], ['phone', 390, 800]]) {
  const p = await newPage(w, h, true);
  await p.open(info.plain);
  await p.waitForSelector('.match-actions a.film', { timeout: 8000 });
  await p.click('.match-actions a.film');
  await p.waitForSelector('.rv #stub-player');
  ok('plain ' + name + ': player only, no list', (await p.$('.rv-list')) === null && (await p.$('.rv-solo')) !== null);
  const g = await p.evaluate(() => { const f = document.querySelector('.rv-frame').getBoundingClientRect(); return f.width / f.height; });
  ok('plain ' + name + ': 16:9', Math.abs(g - 16 / 9) < 0.02);
  await wait(400);
  await p.screenshot({ path: path.join(shots, `review_plain_${name}.png`) });
  await p.keyboard.press('Escape');
  await p.close();
}

await b.close();
fs.rmSync(dir, { recursive: true, force: true });
console.log(failed ? `${failed} FAILED` : 'ALL PASSED', '  screenshots:', shots);
process.exit(failed ? 1 : 0);
