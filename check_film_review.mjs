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
  var self = this, fire = function (d) { if (window.__yt.auto) setTimeout(function () { opts.events.onStateChange({ data: d }); }, 0); };
  this.playVideo = function () { window.__yt.plays++; fire(1); };
  this.pauseVideo = function () { window.__yt.pauses = (window.__yt.pauses || 0) + 1; fire(2); };
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
  ok(name + ': a sheet row opens at its moment', (await nowIndex(p)) === 5 && (await p.evaluate(() => window.__yt.opts.playerVars.start)) === 1420);
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


// Filters and highlights. The fixture game: nine placed events (five goals, four penalties); seconds are the sealed moments' t.
// Seconds: 100 755 1400 2000 2500 (goals), 300 1000 1420 2200 (penalties). The goal at 1400 runs into the penalty at 1420.
const chipTexts = (p) => p.$$eval('.rv-chip', (e) => e.map((x) => x.textContent.replace(/\s+/g, ' ').trim()));
const visTimes = (p) => p.$$eval('.rv-list li:not([hidden]) .sheet-when', (e) => e.map((x) => x.textContent.trim()));
const chip = (p, f) => p.$eval(`.rv-chip[data-f="${f}"]`, (e) => e.click());
const seeks = (p) => p.evaluate(() => window.__yt.seeks.map((x) => x[0]));
const hlText = (p) => p.$eval('.rv-hl-n', (e) => e.textContent);
for (const [name, w, h] of [['desktop', 1100, 800], ['phone', 390, 800]]) {
  const p = await newPage(w, h, true);
  await p.open(info.moments);
  await p.waitForSelector('a.is-film', { timeout: 8000 });
  await p.click('.tl-dot[data-m="goal|1|3:16"]');
  await p.waitForSelector('.rv #stub-player');
  const counts = await chipTexts(p);
  console.log('  chips', JSON.stringify(counts));
  ok(name + ': filters in order with counts', counts[0] === 'All9' && counts.length === 5 && counts[1] === 'Goals5' && counts[2].startsWith('Goals for') && counts[3].startsWith('Goals against') && counts[4] === 'Penalties4', JSON.stringify(counts));
  const n = counts.map((c) => +c.match(/(\d+)$/)[1]);
  ok(name + ': goals for + goals against = goals; goals + penalties = all', n[2] + n[3] === n[1] && n[1] + n[4] === n[0] && n[1] === 5, JSON.stringify(n));
  ok(name + ': All is selected at first and the list is whole', (await p.$eval('.rv-chip[data-f="all"]', (e) => e.getAttribute('aria-checked'))) === 'true' && (await visTimes(p)).length === 9);
  const seekBefore = (await seeks(p)).length, createdBefore = await p.evaluate(() => window.__yt.created);
  for (const [f, cnt] of [['goals', n[1]], ['goals-for', n[2]], ['goals-against', n[3]], ['penalties', n[4]], ['all', 9]]) {
    await chip(p, f);
    const labels = await p.$$eval('.rv-list li:not([hidden]) .rv-row', (e) => e.map((x) => x.getAttribute('aria-label')));
    const kinds = labels.map((l) => (/Goal/.test(l) ? 'goal' : 'penalty'));
    ok(name + ': filter ' + f + ' lists ' + cnt, labels.length === cnt && (f === 'penalties' ? kinds.every((k) => k === 'penalty') : f === 'all' || kinds.every((k) => k === 'goal')), labels.length + ' rows');
    if (f === 'goals-for' || f === 'goals-against') {
      const want = f === 'goals-for' ? 'us' : 'them';
      const got = await p.$$eval('.rv-list li:not([hidden])', (e) => e.length);
      const sheet = await p.evaluate(() => Array.from(document.querySelectorAll('li[data-m^="goal"]')).map((l) => l.getAttribute('data-m') + '=' + l.getAttribute('data-side')));
      ok(name + ': ' + f + ' matches the sheet side', sheet.filter((x) => x.endsWith('=' + want)).length === got, JSON.stringify(sheet));
    }
  }
  ok(name + ': filtering does not touch the video', (await seeks(p)).length === seekBefore && (await p.evaluate(() => window.__yt.created)) === createdBefore && (await p.evaluate(() => window.__yt.destroyed)) === 0);
  // Keyboard: arrows move the selection, only the selected chip is a tab stop.
  await p.$eval('.rv-chip[data-f="all"]', (e) => e.focus());
  await p.keyboard.press('ArrowRight');
  ok(name + ': ArrowRight selects the next filter', (await p.$eval('.rv-chip.is-on', (e) => e.getAttribute('data-f'))) === 'goals' && (await visTimes(p)).length === 5);
  ok(name + ': one chip is a tab stop', (await p.$$eval('.rv-chip', (e) => e.filter((x) => x.tabIndex === 0).length)) === 1);
  await p.keyboard.press('End');
  ok(name + ': End selects Penalties', (await p.$eval('.rv-chip.is-on', (e) => e.getAttribute('data-f'))) === 'penalties');
  await p.keyboard.press('Home');
  ok(name + ': address carries the filter, then drops it for All', (await p.evaluate(() => location.hash)).indexOf('filter') < 0);
  await chip(p, 'goals-for');
  ok(name + ': #review=<moment>&filter=goals-for', /^#review(=(goal|penalty)-\d-\d+:\d\d)?&filter=goals-for$/.test(await p.evaluate(() => location.hash)), await p.evaluate(() => location.hash));
  // Playback highlight is restricted to the visible rows.
  await p.evaluate((ts) => { window.__yt.ct = ts; window.__yt.opts.events.onStateChange({ data: 1 }); }, 2500);
  await wait(700);
  const cur = await p.$$eval('.rv-list li:not([hidden]) .rv-row', (e) => e.map((x) => x.classList.contains('is-now')));
  ok(name + ': current row is among the visible rows (exactly one)', cur.filter(Boolean).length === 1 && (await p.$$eval('.rv-row.is-now', (e) => e.every((x) => !x.closest('li').hidden))));
  await p.evaluate(() => window.__yt.opts.events.onStateChange({ data: 2 }));
  await chip(p, 'all');
  // The bar stays at the top of the pane while the list scrolls.
  const stick = await p.evaluate(() => { const b = document.querySelector('.rv-bar').getBoundingClientRect(), l = document.querySelector('.rv-list'); l.scrollTop = 9999; const b2 = document.querySelector('.rv-bar').getBoundingClientRect(); return [b.top, b2.top, document.querySelector('.rv-side').scrollHeight <= document.querySelector('.rv-side').clientHeight + 1]; });
  ok(name + ': filter bar stays put while the list scrolls', stick[0] === stick[1] && stick[2], JSON.stringify(stick));
  await wait(200);
  await p.screenshot({ path: path.join(shots, `review_${name}_filters.png`) });

  // Highlights over everything.
  await p.evaluate(() => { window.__yt.auto = true; window.__yt.seeks = []; window.__yt.ct = 0; });
  await p.click('.rv-hlbtn');
  await wait(300);
  const S = async () => (await seeks(p));
  ok(name + ': Highlights starts at the first clip', JSON.stringify(await S()) === '[100]' && (await hlText(p)) === '1 of 9' && (await nowIndex(p)) === 0);
  ok(name + ': controls shown, button pressed, address is #review=highlights', (await p.$eval('.rv-hl', (e) => !e.hidden)) && (await p.$eval('.rv-hlbtn', (e) => e.getAttribute('aria-pressed'))) === 'true' && (await p.evaluate(() => location.hash)) === '#review=highlights');
  await p.screenshot({ path: path.join(shots, `review_${name}_highlights.png`) });
  const drive = async (ct) => { await p.evaluate((c) => { window.__yt.ct = c; }, ct); await wait(450); };
  await drive(120);
  ok(name + ': mid-clip nothing changes', (await hlText(p)) === '1 of 9' && (await S()).length === 1);
  await drive(132);
  ok(name + ': after 32 s (goal, 20 s lead-in and 12 s after) the penalty clip is sought', JSON.stringify(await S()) === '[100,300]' && (await hlText(p)) === '2 of 9' && (await nowIndex(p)) === 1);
  await drive(328);
  ok(name + ': after 28 s (penalty, 20 and 8) the next goal clip is sought', JSON.stringify(await S()) === '[100,300,755]' && (await hlText(p)) === '3 of 9');
  // Pause by the viewer: the bar shows Resume and the sequence holds.
  await p.evaluate(() => window.__yt.opts.events.onStateChange({ data: 2 }));
  ok(name + ': viewer pause shows Resume', (await p.$eval('.rv-ctl-main', (e) => e.getAttribute('aria-label'))) === 'Resume');
  await drive(770);
  ok(name + ': paused, the clip does not advance', (await hlText(p)) === '3 of 9');
  await p.$eval('.rv-ctl-main', (e) => e.click());
  await wait(100);
  ok(name + ': Resume plays the video and shows Pause', (await p.$eval('.rv-ctl-main', (e) => e.getAttribute('aria-label'))) === 'Pause' && (await hlText(p)) === '3 of 9');
  await p.$eval('.rv-ctl-main', (e) => e.click());
  await wait(100);
  ok(name + ': Pause pauses the video', (await p.evaluate(() => window.__yt.pauses)) >= 1 && (await p.$eval('.rv-ctl-main', (e) => e.getAttribute('aria-label'))) === 'Resume');
  await p.$eval('.rv-ctl-main', (e) => e.click());
  await wait(100);
  await drive(787);
  ok(name + ': next clip', JSON.stringify(await S()) === '[100,300,755,1000]' && (await hlText(p)) === '4 of 9');
  // Skip and previous.
  await p.$eval('.rv-ctl[data-tip="Next clip"]', (e) => e.click());
  await wait(100);
  ok(name + ': Next jumps to clip 5', (await S()).slice(-1)[0] === 1400 && (await hlText(p)) === '5 of 9' && (await nowIndex(p)) === 4);
  await p.$eval('.rv-ctl[data-tip="Previous clip"]', (e) => e.click());
  await wait(100);
  ok(name + ': Previous returns to clip 4', (await S()).slice(-1)[0] === 1000 && (await hlText(p)) === '4 of 9');
  await p.$eval('.rv-ctl[data-tip="Next clip"]', (e) => e.click()); await wait(100);
  // Clip 5 (goal at 1400) is cut where the penalty at 1420 starts: that advance does not seek again.
  const before = (await S()).length;
  await drive(1420);
  ok(name + ': a clip that runs into the next one carries on without a seek', (await hlText(p)) === '6 of 9' && (await S()).length === before, (await hlText(p)) + ' ' + before + ' ' + JSON.stringify(await S()));
  await drive(1448);
  ok(name + ': then the goal at 2000', (await S()).slice(-1)[0] === 2000 && (await hlText(p)) === '7 of 9');
  // The viewer seeks: highlights end, normal review follows.
  await drive(100);
  ok(name + ': a viewer seek leaves highlights', (await p.$('.rv-hl:not([hidden])')) === null && (await p.$eval('.rv-hlbtn', (e) => e.getAttribute('aria-pressed'))) === 'false' && !(await p.evaluate(() => location.hash)).includes('highlights'));
  ok(name + ': and the current row follows the video', (await nowIndex(p)) === 0, 'index ' + await nowIndex(p));
  // Filter change restarts on the new list; stop leaves the video where it is.
  await p.click('.rv-hlbtn');
  await wait(300);
  await chip(p, 'penalties');
  await wait(300);
  ok(name + ': a filter change restarts highlights on the new list', (await hlText(p)) === '1 of 4' && (await S()).slice(-1)[0] === 300 && (await p.evaluate(() => location.hash)) === '#review=highlights&filter=penalties');
  await drive(328); await drive(1028);
  ok(name + ': penalties only: 300, 1000, 1420, 2200', JSON.stringify((await S()).slice(-3)) === '[300,1000,1420]' && (await hlText(p)) === '3 of 4', JSON.stringify(await S()));
  const seekN = (await S()).length;
  await p.evaluate(() => { window.__yt.ct = 1425; });
  await p.click('.rv-hl-stop');
  await wait(300);
  ok(name + ': Stop returns to normal review and leaves the video alone', (await p.$('.rv-hl:not([hidden])')) === null && (await S()).length === seekN && (await p.$eval('.rv-chip.is-on', (e) => e.getAttribute('data-f'))) === 'penalties');
  // The end of the sequence.
  await chip(p, 'goals-for');
  await p.click('.rv-hlbtn'); await wait(300);
  const last = (await visTimes(p)).length;
  ok(name + ': goals for highlights count', (await hlText(p)) === '1 of ' + last);
  for (let i = 1; i < last; i++) { await p.$eval('.rv-ctl[data-tip="Next clip"]', (e) => e.click()); await wait(60); }
  ok(name + ': Next reaches the last clip', (await hlText(p)) === last + ' of ' + last);
  const pa = await p.evaluate(() => window.__yt.pauses || 0);
  await p.evaluate(() => { const l = window.__yt; window.__yt.ct = l.seeks[l.seeks.length - 1][0] + 32; });
  await wait(450);
  ok(name + ': the end says so', (await hlText(p)) === 'End of highlights' && (await p.evaluate(() => window.__yt.pauses || 0)) === pa + 1, (await hlText(p)) + ' ' + pa + ' ' + (await p.evaluate(() => window.__yt.pauses || 0)) + ' ' + JSON.stringify(await S()));
  await p.screenshot({ path: path.join(shots, `review_${name}_end.png`) });
  await wait(2800);
  ok(name + ': then returns to normal', (await p.$('.rv-hl:not([hidden])')) === null && (await p.$eval('.rv-hlbtn', (e) => e.getAttribute('aria-pressed'))) === 'false');
  // Esc during highlights closes everything.
  await chip(p, 'all'); await p.click('.rv-hlbtn'); await wait(200);
  await p.keyboard.press('Escape');
  ok(name + ': Esc closes the review during highlights', (await p.$('.rv')) === null);
  await p.close();
}
// The score above the player, from the player's own time. The fixture's Eagles are the away team: the Jets score first (play at 120 s), then the Eagles
// score four; the goal whose moment is at 755 s (play at 775 s) is approximate (40 s either way); the 2nd period starts at 1000 s, the 3rd at 1900 s, the game ends at 3000 s.
const sbState = (p) => p.evaluate(() => {
  const b = document.querySelector('.rv-sb'); if (!b) return null;
  const us = b.querySelector('.rv-sb-us'), them = b.querySelector('.rv-sb-them');
  return { us: us.textContent, them: them.textContent, per: b.querySelector('.rv-sb-per').textContent, usColor: getComputedStyle(us).color, themColor: getComputedStyle(them).color,
    usW: getComputedStyle(us).fontWeight, themW: getComputedStyle(them).fontWeight, tied: b.classList.contains('is-tied'), final: b.classList.contains('is-final'),
    newUs: us.classList.contains('is-new'), newThem: them.classList.contains('is-new'), aria: b.getAttribute('aria-label'), logos: b.querySelectorAll('.team-logo').length,
    names: [...b.querySelectorAll('.rv-sb-name')].map((n) => n.textContent), namesShown: getComputedStyle(b.querySelector('.rv-sb-name')).display !== 'none' };
});
for (const [name, w, h] of [['desktop', 1100, 800], ['phone', 390, 800]]) {
  const p = await newPage(w, h, true);
  await p.open(info.moments);
  await p.waitForSelector('a.is-film', { timeout: 8000 });
  await p.click('.match-actions a.film');
  await p.waitForSelector('.rv #stub-player');
  await p.evaluate(() => { window.__yt.auto = true; });
  const setCt = async (c, ms = 450) => { await p.evaluate((x) => { window.__yt.ct = x; window.__yt.opts.events.onStateChange({ data: 1 }); }, c); await wait(ms); };
  const at = async (c) => { await setCt(c, 60); const x = await sbState(p); return `${x.us}-${x.them} ${x.per}`; };
  let s = await sbState(p);
  ok(name + ': score strip is there with both logos and the teams named', !!s && s.logos === 2 && s.names.join('|') === 'Toronto Eagles|Mississauga Jets', JSON.stringify(s));
  ok(name + ': before the game it reads 0-0 in the 1st', s.us === '0' && s.them === '0' && s.per === '1st' && s.tied && !s.final, JSON.stringify(s));
  const g = await p.evaluate(() => { const r = (q) => document.querySelector(q).getBoundingClientRect(), sb = r('.rv-sb'), f = r('.rv-frame'); return { sbBottom: sb.bottom, fy: f.top, sw: sb.width, fw: f.width, sx: sb.x, fx: f.x, sh: sb.height, over: document.documentElement.scrollWidth > innerWidth, head: r('.rv-head').bottom, inStage: document.querySelector('.rv-stage').contains(document.querySelector('.rv-sb')), fh: f.height }; });
  ok(name + ': strip sits above the video, outside it, as wide as the video', g.inStage && g.sbBottom <= g.fy + 0.5 && Math.abs(g.sw - g.fw) < 1.5 && Math.abs(g.sx - g.fx) < 1.5 && g.head <= g.sbBottom && !g.over, JSON.stringify(g));
  ok(name + ': video still 16:9 and strip compact', Math.abs(g.fw / g.fh - 16 / 9) < 0.02 && g.sh <= 64, 'strip height ' + g.sh);
  if (w > 760) ok(name + ': names shown beside the logos', s.namesShown); else ok(name + ': names left out on a phone, logos stay', !s.namesShown && s.logos === 2);
  await p.screenshot({ path: path.join(shots, `score_${name}_start.png`) });
  const readings = [[0, '0-0 1st'], [119.9, '0-0 1st'], [120, '0-1 1st'], [734, '0-1 1st'], [774.9, '0-1 1st'], [775, '1-1 1st'], [999, '1-1 1st'], [1000, '1-1 2nd'], [1419.9, '1-1 2nd'],
    [1420, '2-1 2nd'], [1899, '2-1 2nd'], [1900, '2-1 3rd'], [2020, '3-1 3rd'], [2519, '3-1 3rd'], [2520, '4-1 3rd'], [2999, '4-1 3rd'], [3000, '4-1 Final'], [3600, '4-1 Final']];
  for (const [ct, want] of readings) { const got = await at(ct); ok(`${name}: at ${ct} s the strip reads ${want}`, got === want, got); }
  // Going back shows the earlier score again; the approximate goal is held back until its time and not before its lower limit (735 s).
  ok(name + ': back to 700 s reads 0-1 1st', (await at(700)) === '0-1 1st');
  ok(name + ': back to 5 s reads 0-0 1st', (await at(5)) === '0-0 1st');
  // Colours and weight: red for the Eagles, black for the opponent, the team ahead in heavier type, level scores equal.
  await at(2100); s = await sbState(p);
  ok(name + ': Eagles in red, opponent in black', s.usColor === 'rgb(196, 21, 32)' && s.themColor === 'rgb(17, 18, 20)', s.usColor + ' ' + s.themColor);
  ok(name + ': the Eagles ahead (3-1): heavier type for them', +s.usW > +s.themW && !s.tied, s.usW + ' ' + s.themW);
  await at(300); s = await sbState(p);
  ok(name + ': the opponent ahead (0-1): heavier type for them', +s.themW > +s.usW, s.usW + ' ' + s.themW);
  await at(800); s = await sbState(p);
  ok(name + ': level (1-1): equal weight', s.usW === s.themW && s.tied, s.usW + ' ' + s.themW);
  await at(1500); s = await sbState(p);
  ok(name + ': read out as the teams, score and period', s.aria === 'Toronto Eagles 2, Mississauga Jets 1, 2nd period', s.aria);
  await at(3100); s = await sbState(p);
  ok(name + ': read out as final at the end', s.aria === 'Toronto Eagles 4, Mississauga Jets 1, final' && s.final, s.aria);
  // A goal that lands while the game plays on is emphasised for a moment, on the scorer's number; a jump changes the score quietly.
  await at(1419.5); await wait(500);
  await setCt(1420.6, 120);
  s = await sbState(p);
  ok(name + ': a goal while playing emphasises the Eagles number', s.newUs && !s.newThem && s.us === '2', JSON.stringify(s));
  await p.screenshot({ path: path.join(shots, `score_${name}_goal.png`) });
  await wait(1900);
  s = await sbState(p);
  ok(name + ': the emphasis is short', !s.newUs && !s.newThem);
  await at(119.5); await wait(500);
  await setCt(120.4, 120);
  s = await sbState(p);
  ok(name + ': an opponent goal emphasises their number', s.newThem && !s.newUs && s.them === '1', JSON.stringify(s));
  await wait(1900);
  await at(1000); await setCt(2600, 120);
  s = await sbState(p);
  ok(name + ': a jump forward changes the score without emphasis', s.us === '4' && !s.newUs && !s.newThem, JSON.stringify(s));
  await (await p.$$('.rv-row'))[4].click();   // the goal at 1400: the film is taken to the lead-in, 20 s before the play
  await wait(200);
  s = await sbState(p);
  ok(name + ': a clicked row shows the score of that time, without emphasis', s.us === '1' && s.them === '1' && s.per === '2nd' && !s.newUs, JSON.stringify(s));
  await setCt(1419.5, 60); await setCt(1420.5, 120);
  ok(name + ': then the goal lands with emphasis', (await sbState(p)).newUs, JSON.stringify(await sbState(p)));
  // Paused: it holds. Filters and highlights leave it alone.
  await p.evaluate(() => window.__yt.opts.events.onStateChange({ data: 2 }));
  await wait(300);
  const before = await sbState(p);
  await chip(p, 'goals-for'); await wait(100);
  const after = await sbState(p);
  ok(name + ': a filter does not change it', before.us === after.us && before.them === after.them && before.per === after.per, JSON.stringify(after));
  await p.evaluate(() => { window.__yt.ct = 3200; window.__yt.opts.events.onStateChange({ data: 1 }); });
  await wait(700);
  await p.screenshot({ path: path.join(shots, `score_${name}_final.png`) });
  const tipFocus = await p.evaluate(() => document.querySelector('.rv').contains(document.activeElement));
  ok(name + ': focus stays in the dialog and the strip takes no focus', tipFocus );
  await p.close();
}
// The countdown to the play, from the player's own time.
const cdState = (p) => p.evaluate(() => { const c = document.querySelector('.rv-cd'); return { on: c.classList.contains('is-on'), here: c.classList.contains('is-here'), text: c.querySelector('.rv-cd-label').textContent, w: Math.round((1 - parseFloat(c.querySelector('.rv-cd-arc').style.strokeDashoffset) / (2 * Math.PI * 21)) * 100) + '%', logo: !!c.querySelector('.team-logo'), live: document.querySelector('.rv-sr').textContent, vis: getComputedStyle(c).visibility }; });
for (const [name, w, h] of [['desktop', 1100, 800], ['phone', 390, 800]]) {
  const p = await newPage(w, h, true);
  await p.open(info.moments);
  await p.waitForSelector('a.is-film', { timeout: 8000 });
  await p.click('.match-actions a.film');
  await p.waitForSelector('.rv #stub-player');
  await p.evaluate(() => { window.__yt.auto = true; });
  const setCt = async (c, ms = 450) => { await p.evaluate((x) => { window.__yt.ct = x; window.__yt.opts.events.onStateChange({ data: 1 }); }, c); await wait(ms); };
  let c = await cdState(p);
  ok(name + ': countdown hidden at the start of the film', !c.on && c.vis === 'hidden');
  await (await p.$$('.rv-row'))[6].click();   // goal at 2000, the play is at 2020
  await wait(200);
  c = await cdState(p);
  ok(name + ': clicking a goal row starts the countdown at 20 s', c.on && !c.here && c.text === 'Goal in 20 s' && c.w === '0%' && c.logo && c.vis === 'visible' && c.live === 'Goal in 20 seconds', JSON.stringify(c));
  await setCt(2008);
  c = await cdState(p);
  ok(name + ': at 2008 s: Goal in 12 s, ring 40%', c.text === 'Goal in 12 s' && c.w === '40%' && c.live === 'Goal in 20 seconds', JSON.stringify(c));
  await setCt(2011.5);
  c = await cdState(p);
  ok(name + ': at 2011.5 s: 9 s left (rounded up)', c.text === 'Goal in 9 s', c.text);
  await p.screenshot({ path: path.join(shots, `review_${name}_countdown.png`) });
  await p.evaluate(() => window.__yt.opts.events.onStateChange({ data: 2 }));
  await wait(300);
  c = await cdState(p);
  ok(name + ': paused, it holds', c.on && c.text === 'Goal in 9 s');
  await setCt(2020.2);
  c = await cdState(p);
  ok(name + ': at the play it names the event and is emphasised', c.here && /^Goal \d.\d$/.test(c.text) && c.w === '100%', JSON.stringify(c));
  await p.screenshot({ path: path.join(shots, `review_${name}_countdown_here.png`) });
  await setCt(2023);
  ok(name + ': still shown 3 s after', (await cdState(p)).here);
  await setCt(2025);
  c = await cdState(p);
  ok(name + ': settles (hidden) after the play', !c.on && c.vis === 'hidden');
  // A new row resets it; a penalty reads its own word.
  await (await p.$$('.rv-row'))[3].click();   // penalty at 1000, play at 1020
  await wait(300);
  c = await cdState(p);
  ok(name + ': another row resets to its own countdown', c.text === 'Penalty in 20 s' && c.w === '0%' && c.live === 'Penalty in 20 seconds', JSON.stringify(c));
  await setCt(1020.1);
  c = await cdState(p);
  ok(name + ': a penalty names itself at the play', c.here && /^Slashing|^Hooking|^[A-Z]/.test(c.text) && /min/.test(c.text), c.text);
  // A viewer seek away hides it; filtered-out events are not counted down.
  await setCt(600);
  ok(name + ': seeking elsewhere hides it', !(await cdState(p)).on);
  await chip(p, 'goals');
  await setCt(1010);
  ok(name + ': with Goals only, a penalty is not counted down', !(await cdState(p)).on);
  await chip(p, 'all');
  // The live region is not rewritten every second.
  await setCt(1400); await setCt(1405); await setCt(1410);
  ok(name + ': announced once per event', (await cdState(p)).live === 'Goal in 20 seconds');
  // Highlights: the countdown follows each clip.
  await chip(p, 'all');
  await p.click('.rv-hlbtn'); await wait(300);
  ok(name + ': highlights clip 1 starts with Goal in 20 s', (await cdState(p)).text === 'Goal in 20 s');
  await p.$eval('.rv-ctl[data-tip="Next clip"]', (e) => e.click()); await wait(200);
  ok(name + ': next clip resets to Penalty in 20 s', (await cdState(p)).text === 'Penalty in 20 s' && (await hlText(p)) === '2 of 9');
  await p.screenshot({ path: path.join(shots, `review_${name}_highlights_countdown.png`) });
  await p.close();
}

// Shared links: filter, highlights, and a signed-out visitor who then signs in.
{
  const p = await newPage(1100, 800, true);
  await p.open(info.moments);
  await p.goto('file://' + path.join(dir, info.moments) + '#review=goal-2-4:33&filter=goals'); await p.reload();
  await p.waitForSelector('.rv #stub-player', { timeout: 8000 });
  ok('link with a moment and a filter', (await visTimes(p)).length === 5 && (await p.$eval('.rv-chip.is-on', (e) => e.getAttribute('data-f'))) === 'goals' && (await p.evaluate(() => window.__yt.opts.playerVars.start)) === 1400 && (await p.evaluate(() => location.hash)) === '#review=goal-2-4:33&filter=goals', await p.evaluate(() => location.hash));
  await p.close();
  const q = await newPage(1100, 800, true);
  await q.open(info.moments);
  await q.goto('file://' + path.join(dir, info.moments) + '#review&filter=nonsense'); await q.reload();
  await q.waitForSelector('.rv #stub-player', { timeout: 8000 });
  ok('an unknown filter shows everything', (await visTimes(q)).length === 9 && (await q.evaluate(() => location.hash)) === '#review');
  await q.close();
  const r = await newPage(1100, 800, true);
  await r.evaluateOnNewDocument(() => { window.__yt_auto = 1; });
  await r.open(info.moments);
  await r.goto('file://' + path.join(dir, info.moments) + '#review=highlights&filter=penalties'); await r.reload();
  await r.waitForSelector('.rv #stub-player', { timeout: 8000 });
  await wait(300);
  ok('#review=highlights&filter=penalties starts highlights on penalties', (await hlText(r)) === '1 of 4' && (await r.evaluate(() => window.__yt.opts.playerVars.start)) === 300 && (await r.evaluate(() => location.hash)) === '#review=highlights&filter=penalties', await r.evaluate(() => location.hash + ' ' + JSON.stringify(window.__yt.opts.playerVars)));
  await r.close();
  const o = await newPage(390, 800, false);
  await o.goto('file://' + path.join(dir, info.moments));
  await o.evaluate(() => localStorage.clear());
  await o.goto('file://' + path.join(dir, info.moments) + '#review=highlights'); await o.reload();
  await o.waitForSelector('dialog.login-dialog[open]', { timeout: 8000 });
  await o.type('#login-password', info.password); await o.keyboard.press('Enter');
  await o.waitForSelector('.rv #stub-player', { timeout: 8000 });
  await wait(300);
  ok('signed-out #review=highlights: sign in, then highlights', (await hlText(o)) === '1 of 9');
  await o.close();
}

// Header, shared link, sign-in.
for (const [name, w, h] of [['desktop', 1100, 800], ['phone', 390, 800]]) {
  const p = await newPage(w, h, true);
  await p.evaluateOnNewDocument(() => {
    window.__copied = [];
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__copied.push(t); return Promise.resolve(); } }, configurable: true });
    window.__hist = 0; const rs = history.replaceState.bind(history), ps = history.pushState.bind(history);
    history.pushState = function () { window.__hist++; return ps.apply(this, arguments); };
  });
  await p.open(info.moments);
  await p.waitForSelector('a.is-film', { timeout: 8000 });
  ok(name + ': rows on the sheet carry no play icon', (await p.$$('li[data-m] a.sheet-what .film-icon')).length === 0);
  await p.goto('file://' + path.join(dir, info.moments) + '#review=goal-2-4:33');
  await p.reload();
  await p.waitForSelector('.rv #stub-player', { timeout: 8000 });
  const head = await p.evaluate(() => ({ title: document.querySelector('.rv-title').textContent, score: document.querySelector('.rv-score') && document.querySelector('.rv-score').textContent, sub: document.querySelector('.rv-sub').textContent, label: document.querySelector('.rv').getAttribute('aria-label'), h: document.querySelector('.rv-head').getBoundingClientRect().height, sw: document.documentElement.scrollWidth, iw: innerWidth }));
  console.log('  header', JSON.stringify(head));
  ok(name + ': header shows teams, score and the date line', / at /.test(head.title) && /^\d.\d\s*Final$/.test(head.score) && /^\w+day, \w+ \d+ · .* · .+/.test(head.sub), JSON.stringify(head));
  ok(name + ': dialog label names the game', head.label === 'Video review, ' + head.title, head.label);
  ok(name + ': header compact, no overflow', head.h < 80 && head.sw <= head.iw, 'height ' + head.h);
  ok(name + ': #review=goal-2-4:33 opens at that moment', (await nowIndex(p)) === 4 && (await p.evaluate(() => window.__yt.opts.playerVars.start)) === 1400);
  ok(name + ': address keeps the moment', (await p.evaluate(() => location.hash)) === '#review=goal-2-4:33');
  await wait(300);
  await p.screenshot({ path: path.join(shots, `review_${name}_header.png`) });
  const btns = await p.$$('.rv-row');
  await btns[1].click();
  ok(name + ': hash follows a clicked row', (await p.evaluate(() => location.hash)) === '#review=penalty-1-7:10', await p.evaluate(() => location.hash));
  await p.evaluate(() => { window.__yt.ct = 3000; window.__yt.opts.events.onStateChange({ data: 1 }); });
  await wait(900);
  ok(name + ': hash follows playback', (await p.evaluate(() => location.hash)) === '#review=goal-3-4:16', await p.evaluate(() => location.hash));
  await p.evaluate(() => window.__yt.opts.events.onStateChange({ data: 2 }));
  const hl = await p.evaluate(() => history.length);
  await p.$eval('.rv-share', (e) => e.focus());
  const href = await p.evaluate(() => location.href);
  await p.click('.rv-share');
  const cp = await p.evaluate(() => ({ copied: window.__copied, tip: document.querySelector('.rv-share').getAttribute('data-tip'), shown: (document.querySelector('.tip') || {}).textContent, vis: (document.querySelector('.tip') || {style:{}}).style.display, hist: window.__hist }));
  ok(name + ': copy link writes the current address', cp.copied.length === 1 && cp.copied[0] === href && href.endsWith('#review=goal-3-4:16'), JSON.stringify(cp));
  ok(name + ': tooltip says Link copied', cp.tip === 'Link copied' && cp.shown === 'Link copied' && cp.vis === 'block', JSON.stringify(cp));
  await p.screenshot({ path: path.join(shots, `review_${name}_copied.png`) });
  await wait(2500);
  ok(name + ': tooltip returns to Copy link', (await p.$eval('.rv-share', (e) => e.getAttribute('data-tip'))) === 'Copy link');
  ok(name + ': no history entries added', cp.hist === 0 && (await p.evaluate(() => history.length)) === hl);
  await p.keyboard.press('Escape');
  ok(name + ': closing removes the hash', (await p.evaluate(() => location.hash)) === '' && (await p.$('.rv')) === null);
  await p.close();
}
{
  const p = await newPage(1100, 800, true);
  await p.open(info.moments);
  await p.goto('file://' + path.join(dir, info.moments) + '#review=goal-9-9:99'); await p.reload();
  await p.waitForSelector('.rv #stub-player', { timeout: 8000 });
  ok('unknown moment opens at the start', (await nowIndex(p)) === -1 && !(await p.evaluate(() => 'start' in window.__yt.opts.playerVars)) && (await p.evaluate(() => location.hash)) === '#review');
  await p.close();
  const q = await newPage(1100, 800, true);
  await q.open(info.moments);
  await q.goto('file://' + path.join(dir, info.moments) + '#review'); await q.reload();
  await q.waitForSelector('.rv #stub-player', { timeout: 8000 });
  ok('#review opens at the start of the film', (await nowIndex(q)) === -1 && (await q.evaluate(() => location.hash)) === '#review');
  await q.close();
}

// Game sheet lists: three columns where they fit, rows one line high, no overflow, long names cut with an ellipsis.
for (const signedIn of [false, true]) for (const w of [1100, 1000, 871, 700, 390]) {
  const p = await newPage(w, 900, signedIn);
  await p.open(info.moments);
  if (signedIn) await p.waitForSelector('a.is-film', { timeout: 8000 });
  const r = await p.evaluate(() => {
    const lists = document.querySelector('.sheet-lists');
    const nl = lists.querySelectorAll('.sheet-list').length, cols = new Set(Array.from(lists.querySelectorAll('.sheet-list')).map((x) => Math.round(x.getBoundingClientRect().left))).size;
    const lis = Array.from(lists.querySelectorAll('li'));
    const hs = lis.map((l) => Math.round(l.getBoundingClientRect().height));
    const cut = lis.filter((l) => { const n = l.querySelector('.sheet-what > span'); return n && n.scrollWidth > n.clientWidth; }).map((l) => l.textContent.replace(/\s+/g, ' ').trim());
    const notes = Array.from(lists.querySelectorAll('.sheet-note')).every((n) => n.getBoundingClientRect().width > 25 && n.getBoundingClientRect().right <= n.closest('li').getBoundingClientRect().right + 0.5);
    const logos = Array.from(lists.querySelectorAll('.team-logo')).every((n) => Math.round(n.getBoundingClientRect().width) === 20);
    return { cols, nl, n: lis.length, hmin: Math.min(...hs), hmax: Math.max(...hs), cut, notes, logos, width: lists.getBoundingClientRect().width, sw: document.documentElement.scrollWidth, iw: innerWidth };
  });
  const tag = (signedIn ? 'links ' : 'plain ') + w;
  console.log('  lists', tag, JSON.stringify(r));
  ok(tag + ': all ' + r.n + ' rows the same height', r.hmin === r.hmax, r.hmin + '-' + r.hmax);
  ok(tag + ': no horizontal overflow', r.sw <= r.iw);
  ok(tag + ': logos 20px and minutes visible inside the row', r.notes && r.logos);
  ok(tag + ': columns', r.cols === Math.min(r.nl, r.width >= 3 * 250 + 36 ? 3 : r.width >= 2 * 250 + 18 ? 2 : 1), r.cols + ' of ' + r.nl + ' lists at list width ' + Math.round(r.width));
  ok(tag + ': the unusually long name is cut with an ellipsis, nothing wraps', r.cut.some((c) => /Unsportsmanlike/.test(c)), JSON.stringify(r.cut));
  if (signedIn) {
    await p.$eval('.sheet-lists', (e) => e.scrollIntoView());
    await p.screenshot({ path: path.join(shots, `sheet_lists_${w}.png`) });
  }
  await p.close();
}

// A package without info falls back to the plain heading.
{
  const p = await newPage(1100, 800, true);
  await p.evaluateOnNewDocument(() => { const f = JSON.parse; JSON.parse = function (t) { const o = f(t); if (o && o.moments && o.info) delete o.info; return o; }; });
  await p.open(info.moments);
  await p.waitForSelector('.match-actions a.film', { timeout: 8000 });
  await p.click('.match-actions a.film');
  await p.waitForSelector('.rv');
  ok('no info: plain Video review heading', (await p.$eval('.rv-title', (e) => e.textContent)) === 'Video review' && (await p.$('.rv-sub')) === null && (await p.$eval('.rv', (e) => e.getAttribute('aria-label'))) === 'Video review');
  await p.close();
}
// Signed out (none, then wrong) with a shared link: the sign-in box, no film data, and the review after a good password.
for (const [label, wrong] of [['signed out', false], ['wrong password', true]]) {
  const p = await newPage(390, 800, false);
  await p.goto('file://' + path.join(dir, info.moments));
  await p.evaluate((w) => { localStorage.clear(); if (w) localStorage.setItem('eagles-team-password', 'nope'); }, wrong);
  await p.goto('file://' + path.join(dir, info.moments) + '#review=goal-2-4:33'); await p.reload();
  await p.waitForSelector('dialog.login-dialog[open]', { timeout: 8000 });
  ok(label + ': sign-in box shown', true);
  const c = await p.content();
  ok(label + ': no review, film button or film words', (await p.$('.rv')) === null && (await p.$('.match-actions a.film')) === null && !/youtu|Video review/i.test(c.replace(/<(script|style)[\s\S]*?<\/\1>/g, '')) && p.hostRequests.length === 0);
  ok(label + ': box has focus in the password field', await p.evaluate(() => document.activeElement.id === 'login-password'));
  await p.screenshot({ path: path.join(shots, `review_phone_signin_${wrong ? 'wrong' : 'out'}.png`) });
  await p.type('#login-password', 'bad-guess'); await p.keyboard.press('Enter');
  await p.waitForFunction(() => /didn/.test(document.querySelector('.login-msg').textContent), { timeout: 8000 });
  ok(label + ': a bad password is refused and no review opens', (await p.$('.rv')) === null);
  await p.$eval('#login-password', (e) => { e.value = ''; });
  await p.type('#login-password', info.password); await p.keyboard.press('Enter');
  await p.waitForSelector('.rv #stub-player', { timeout: 8000 });
  ok(label + ': after sign-in the review opens at the moment', (await nowIndex(p)) === 4 && (await p.evaluate(() => localStorage.getItem('eagles-team-password'))) === info.password);
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
  ok('plain ' + name + ': a game without a score line shows no strip', (await p.$('.rv-sb')) === null && (await p.$('.has-sb')) === null);
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
