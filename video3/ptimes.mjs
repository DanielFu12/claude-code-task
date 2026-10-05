// 用法：node ptimes.mjs "sec:card:frac,sec:card:frac,..."  → 输出逗号分隔的时间点
import fs from 'node:fs';
const tl = JSON.parse(fs.readFileSync(new URL('../build/v3_timeline.json', import.meta.url)));
const out = process.argv[2].split(',').map(x => { const [id, ci, f] = x.split(':'); const s = tl.sections.find(s => s.id === id); const c = s.cards[+ci]; return (s.start + c.start + c.dur * (+f)).toFixed(2); });
console.log(out.join(','));
