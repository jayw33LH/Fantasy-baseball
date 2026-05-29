import express from 'express';
import Anthropic from '@anthropic-ai/sdk';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json({ limit: '50mb' }));
app.use(express.static(join(__dirname, 'public')));

// ── Demo data (fallback when Baseball Savant is unreachable) ─────────────────
const DEMO_BATTERS = [
  { name: 'Goldschmidt, Paul',  luck_score:  0.068, woba: 0.390, xwoba: 0.322, ba: 0.285, xba: 0.238, pa: 420 },
  { name: 'Arraez, Luis',       luck_score:  0.058, woba: 0.375, xwoba: 0.317, ba: 0.338, xba: 0.284, pa: 398 },
  { name: 'Bregman, Alex',      luck_score:  0.051, woba: 0.381, xwoba: 0.330, ba: 0.270, xba: 0.228, pa: 445 },
  { name: 'Rosario, Amed',      luck_score:  0.047, woba: 0.352, xwoba: 0.305, ba: 0.295, xba: 0.255, pa: 360 },
  { name: 'Nimmo, Brandon',     luck_score:  0.039, woba: 0.368, xwoba: 0.329, ba: 0.262, xba: 0.229, pa: 355 },
  { name: 'Benintendi, Andrew', luck_score:  0.037, woba: 0.362, xwoba: 0.325, ba: 0.294, xba: 0.260, pa: 322 },
  { name: 'Turner, Trea',       luck_score:  0.034, woba: 0.375, xwoba: 0.341, ba: 0.300, xba: 0.271, pa: 468 },
  { name: 'Edman, Tommy',       luck_score:  0.030, woba: 0.345, xwoba: 0.315, ba: 0.275, xba: 0.249, pa: 385 },
  { name: 'Hernandez, Teoscar', luck_score:  0.025, woba: 0.355, xwoba: 0.330, ba: 0.270, xba: 0.248, pa: 412 },
  { name: 'Verdugo, Alex',      luck_score:  0.023, woba: 0.340, xwoba: 0.317, ba: 0.265, xba: 0.244, pa: 388 },
  { name: 'Cronenworth, Jake',  luck_score:  0.035, woba: 0.350, xwoba: 0.315, ba: 0.255, xba: 0.223, pa: 340 },
  { name: 'Pederson, Joc',      luck_score:  0.027, woba: 0.365, xwoba: 0.338, ba: 0.248, xba: 0.225, pa: 270 },
  { name: 'Trout, Mike',        luck_score:  0.008, woba: 0.405, xwoba: 0.397, ba: 0.265, xba: 0.258, pa: 285 },
  { name: 'Freeman, Freddie',   luck_score:  0.005, woba: 0.410, xwoba: 0.405, ba: 0.298, xba: 0.293, pa: 455 },
  { name: 'Guerrero, Vladimir', luck_score:  0.003, woba: 0.398, xwoba: 0.395, ba: 0.285, xba: 0.282, pa: 472 },
  { name: 'Alvarez, Yordan',    luck_score:  0.002, woba: 0.435, xwoba: 0.433, ba: 0.302, xba: 0.300, pa: 390 },
  { name: 'Ohtani, Shohei',     luck_score: -0.001, woba: 0.450, xwoba: 0.451, ba: 0.320, xba: 0.321, pa: 510 },
  { name: 'Acuna, Ronald',      luck_score: -0.003, woba: 0.412, xwoba: 0.415, ba: 0.298, xba: 0.301, pa: 448 },
  { name: 'Judge, Aaron',       luck_score: -0.015, woba: 0.420, xwoba: 0.435, ba: 0.285, xba: 0.298, pa: 480 },
  { name: 'Betts, Mookie',      luck_score: -0.018, woba: 0.388, xwoba: 0.406, ba: 0.272, xba: 0.286, pa: 440 },
  { name: 'Soto, Juan',         luck_score: -0.035, woba: 0.395, xwoba: 0.430, ba: 0.280, xba: 0.310, pa: 488 },
  { name: 'Schwarber, Kyle',    luck_score: -0.038, woba: 0.340, xwoba: 0.378, ba: 0.208, xba: 0.240, pa: 422 },
  { name: 'Steer, Spencer',     luck_score: -0.030, woba: 0.338, xwoba: 0.368, ba: 0.248, xba: 0.272, pa: 362 },
  { name: 'Burger, Jake',       luck_score: -0.028, woba: 0.342, xwoba: 0.370, ba: 0.252, xba: 0.275, pa: 380 },
  { name: 'McCarthy, Jake',     luck_score: -0.048, woba: 0.315, xwoba: 0.363, ba: 0.242, xba: 0.282, pa: 340 },
  { name: 'Gallo, Joey',        luck_score: -0.046, woba: 0.298, xwoba: 0.344, ba: 0.192, xba: 0.228, pa: 295 },
  { name: 'Canha, Mark',        luck_score: -0.060, woba: 0.295, xwoba: 0.355, ba: 0.222, xba: 0.272, pa: 290 },
  { name: 'Winker, Jesse',      luck_score: -0.041, woba: 0.312, xwoba: 0.353, ba: 0.240, xba: 0.275, pa: 308 },
  { name: 'Robert, Luis',       luck_score: -0.072, woba: 0.300, xwoba: 0.372, ba: 0.218, xba: 0.278, pa: 355 },
  { name: 'Laureano, Ramon',    luck_score: -0.055, woba: 0.310, xwoba: 0.365, ba: 0.230, xba: 0.278, pa: 315 },
];

const DEMO_PITCHERS = [
  { name: 'Woodruff, Brandon',  luck_score:  1.42, era: 2.88, xera: 4.30, pa: 420 },
  { name: 'Eflin, Zach',        luck_score:  1.15, era: 3.05, xera: 4.20, pa: 398 },
  { name: 'Luzardo, Jesus',     luck_score:  1.08, era: 3.20, xera: 4.28, pa: 355 },
  { name: 'Gausman, Kevin',     luck_score:  0.95, era: 3.15, xera: 4.10, pa: 445 },
  { name: 'Pivetta, Nick',      luck_score:  0.82, era: 3.55, xera: 4.37, pa: 360 },
  { name: 'Kelly, Merrill',     luck_score:  0.75, era: 3.40, xera: 4.15, pa: 415 },
  { name: 'Nelson, Ryne',       luck_score:  0.68, era: 3.60, xera: 4.28, pa: 330 },
  { name: 'Cease, Dylan',       luck_score:  0.55, era: 3.42, xera: 3.97, pa: 438 },
  { name: 'Bieber, Shane',      luck_score:  0.48, era: 3.25, xera: 3.73, pa: 425 },
  { name: 'Sandoval, Patrick',  luck_score:  0.42, era: 3.58, xera: 4.00, pa: 392 },
  { name: 'Cole, Gerrit',       luck_score:  0.08, era: 2.95, xera: 3.03, pa: 510 },
  { name: 'Wheeler, Zack',      luck_score:  0.03, era: 2.90, xera: 2.93, pa: 498 },
  { name: 'Fried, Max',         luck_score: -0.05, era: 2.95, xera: 2.90, pa: 468 },
  { name: 'Rodon, Carlos',      luck_score: -0.32, era: 3.88, xera: 3.56, pa: 392 },
  { name: 'Nola, Aaron',        luck_score: -0.42, era: 4.08, xera: 3.66, pa: 448 },
  { name: 'Flaherty, Jack',     luck_score: -0.38, era: 3.98, xera: 3.60, pa: 410 },
  { name: 'Buehler, Walker',    luck_score: -0.15, era: 3.62, xera: 3.47, pa: 358 },
  { name: 'Darvish, Yu',        luck_score: -0.75, era: 4.55, xera: 3.80, pa: 405 },
  { name: 'Lynn, Lance',        luck_score: -0.68, era: 4.50, xera: 3.82, pa: 388 },
  { name: 'Quantrill, Cal',     luck_score: -0.88, era: 4.75, xera: 3.87, pa: 362 },
  { name: 'Matz, Steven',       luck_score: -0.82, era: 4.68, xera: 3.86, pa: 340 },
  { name: 'Stroman, Marcus',    luck_score: -1.05, era: 4.95, xera: 3.90, pa: 385 },
  { name: 'Giolito, Lucas',     luck_score: -1.18, era: 5.35, xera: 4.17, pa: 340 },
  { name: 'Montgomery, Jordan', luck_score: -1.25, era: 5.10, xera: 3.85, pa: 355 },
  { name: 'Bassitt, Chris',     luck_score: -1.38, era: 5.20, xera: 3.82, pa: 368 },
];

// ── CSV parser (handles quoted commas) ───────────────────────────────────────
function parseLine(line) {
  const fields = [];
  let cur = '', inQ = false;
  for (const ch of line) {
    if (ch === '"') { inQ = !inQ; }
    else if (ch === ',' && !inQ) { fields.push(cur.trim()); cur = ''; }
    else cur += ch;
  }
  fields.push(cur.trim());
  return fields;
}

function parseCSV(text) {
  const lines = text.trim().split('\n').filter(Boolean);
  const headers = parseLine(lines[0]).map(h => h.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''));
  return lines.slice(1).map(line => {
    const vals = parseLine(line);
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] ?? ''; });
    return obj;
  });
}

// ── Fetch Baseball Savant ─────────────────────────────────────────────────────
const YEAR = new Date().getFullYear();
const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36',
  'Accept': 'text/csv,*/*',
  'Referer': 'https://baseballsavant.mlb.com/',
};

async function fetchSavant(type) {
  const url = `https://baseballsavant.mlb.com/leaderboard/expected_statistics?type=${type}&year=${YEAR}&position=&team=&min=100&csv=true`;
  const res = await fetch(url, { headers: HEADERS });
  if (!res.ok) throw new Error(`Savant ${type}: HTTP ${res.status}`);
  return parseCSV(await res.text());
}

function toBatterLuck(rows) {
  return rows.flatMap(r => {
    const name = r['last_name__first_name'] || (r.last_name && r.first_name ? `${r.last_name}, ${r.first_name}` : null);
    if (!name) return [];
    const woba = parseFloat(r.woba), xwoba = parseFloat(r.est_woba);
    const diff = parseFloat(r.est_woba_minus_woba_diff);
    const luck_score = isNaN(diff) ? (woba - xwoba) : -diff;
    if (isNaN(luck_score)) return [];
    return [{ name, luck_score: +luck_score.toFixed(3), woba: isNaN(woba) ? null : +woba.toFixed(3), xwoba: isNaN(xwoba) ? null : +xwoba.toFixed(3), ba: parseFloat(r.ba) || null, xba: parseFloat(r.est_ba) || null, pa: parseInt(r.pa) || null }];
  }).sort((a, b) => b.luck_score - a.luck_score);
}

function toPitcherLuck(rows) {
  return rows.flatMap(r => {
    const name = r['last_name__first_name'] || (r.last_name && r.first_name ? `${r.last_name}, ${r.first_name}` : null);
    if (!name) return [];
    const era = parseFloat(r.p_era ?? r.era), xera = parseFloat(r.xera);
    const woba = parseFloat(r.woba), xwoba = parseFloat(r.est_woba);
    let luck_score;
    if (!isNaN(era) && !isNaN(xera)) {
      luck_score = xera - era;
    } else {
      const diff = parseFloat(r.est_woba_minus_woba_diff);
      luck_score = isNaN(diff) ? (xwoba - woba) : diff;
    }
    if (isNaN(luck_score)) return [];
    return [{ name, luck_score: +luck_score.toFixed(3), era: isNaN(era) ? null : +era.toFixed(2), xera: isNaN(xera) ? null : +xera.toFixed(2), woba: isNaN(woba) ? null : +woba.toFixed(3), xwoba: isNaN(xwoba) ? null : +xwoba.toFixed(3), pa: parseInt(r.pa) || null }];
  }).sort((a, b) => b.luck_score - a.luck_score);
}

// ── In-memory cache ───────────────────────────────────────────────────────────
let _cache = { batters: null, pitchers: null, ts: 0, isDemo: false, demoReason: '' };

async function getLuckData(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && _cache.batters && (now - _cache.ts) < 3_600_000) {
    return { batters: _cache.batters, pitchers: _cache.pitchers, lastUpdated: new Date(_cache.ts).toISOString(), cached: true, isDemo: _cache.isDemo, demoReason: _cache.demoReason };
  }

  let batters, pitchers, isDemo = false, demoReason = '';
  try {
    const [bRows, pRows] = await Promise.all([fetchSavant('batter'), fetchSavant('pitcher')]);
    batters = toBatterLuck(bRows);
    pitchers = toPitcherLuck(pRows);
    if (!batters.length && !pitchers.length) throw new Error('Empty response');
  } catch (err) {
    console.warn('Baseball Savant unavailable:', err.message, '— using demo data');
    batters = [...DEMO_BATTERS].sort((a, b) => b.luck_score - a.luck_score);
    pitchers = [...DEMO_PITCHERS].sort((a, b) => b.luck_score - a.luck_score);
    isDemo = true;
    demoReason = `Could not reach Baseball Savant (${err.message}) — showing sample data`;
  }

  _cache = { batters, pitchers, ts: now, isDemo, demoReason };
  return { batters, pitchers, lastUpdated: new Date(now).toISOString(), cached: false, isDemo, demoReason };
}

// ── Name matching ─────────────────────────────────────────────────────────────
function normName(n) { return n.toLowerCase().replace(/[^a-z ]/g, '').trim(); }

function findPlayer(name, players) {
  const q = normName(name);
  // Exact
  let hit = players.find(p => normName(p.name) === q);
  if (hit) return hit;
  // "First Last" → last name lookup
  const parts = q.split(' ');
  const last = parts[parts.length - 1];
  hit = players.find(p => normName(p.name.split(',')[0]) === last);
  if (hit) return hit;
  // Substring
  hit = players.find(p => normName(p.name).includes(q) || q.includes(normName(p.name)));
  return hit || null;
}

// ── Routes ────────────────────────────────────────────────────────────────────
app.get('/api/luck-data', async (req, res) => {
  try {
    const data = await getLuckData(req.query.refresh === 'true');
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/analyze-screenshot', async (req, res) => {
  const { imageBase64, mediaType = 'image/png', context = 'my fantasy roster', apiKey } = req.body;
  const key = apiKey || process.env.ANTHROPIC_API_KEY;
  if (!key) return res.status(400).json({ error: 'No ANTHROPIC_API_KEY provided' });
  if (!imageBase64) return res.status(400).json({ error: 'No image data' });

  try {
    const client = new Anthropic({ apiKey: key });
    const { batters, pitchers } = await getLuckData();

    // Step 1: extract player names
    const extract = await client.messages.create({
      model: 'claude-opus-4-8',
      max_tokens: 800,
      messages: [{
        role: 'user',
        content: [
          { type: 'image', source: { type: 'base64', media_type: mediaType, data: imageBase64 } },
          { type: 'text', text: `This is a screenshot of ${context} from a fantasy baseball app.\n\nExtract ALL MLB player names visible. Return ONLY a JSON array, e.g.: ["Mike Trout","Shohei Ohtani"]\n\nReturn only the JSON array.` },
        ],
      }],
    });

    const raw = extract.content[0].text.trim();
    const m = raw.match(/\[[\s\S]*?\]/);
    let playerNames = [];
    try { playerNames = m ? JSON.parse(m[0]) : []; } catch {}

    if (!playerNames.length) return res.json({ success: false, message: 'No player names found', raw });

    // Step 2: cross-reference luck
    const matched = playerNames.map(name => {
      const b = findPlayer(name, batters);
      const p = findPlayer(name, pitchers);
      const hit = b || p;
      const type = b ? 'batter' : (p ? 'pitcher' : 'unknown');
      if (!hit) return { name, type, luck_score: null, stats: null };
      const score = hit.luck_score;
      const thresh = type === 'batter' ? 0.015 : 0.25;
      return { name, matchedName: hit.name, type, luck_score: score, lucky: score > thresh, unlucky: score < -thresh, stats: hit };
    });

    // Step 3: AI analysis
    const analysis = await client.messages.create({
      model: 'claude-opus-4-8',
      max_tokens: 2000,
      messages: [{
        role: 'user',
        content: `You are a fantasy baseball analyst specializing in sabermetric luck analysis.\n\nContext: ${context}\n\nPlayer luck data:\n${JSON.stringify(matched, null, 2)}\n\nLuck guide:\n• Batters: luck = wOBA − xwOBA. Positive = lucky (expect regression, sell high). Negative = unlucky (expect improvement, buy low).\n• Pitchers: luck = xERA − ERA. Positive = lucky (expect regression, fade/sell). Negative = unlucky (expect improvement, stream/buy).\n\nProvide:\n1. **SELL HIGH / FADE** — lucky players to move\n2. **BUY LOW / TARGET** — unlucky players to acquire\n3. **Specific actions** — start/sit, add/drop, trade advice\n\nBe concise, direct, and actionable. Use bullet points.`,
      }],
    });

    res.json({ success: true, playersFound: playerNames, matchedPlayers: matched, analysis: analysis.content[0].text });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`MLB Luck Analyzer running at http://localhost:${PORT}`));
