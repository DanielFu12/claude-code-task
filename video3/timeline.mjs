// 由 story.js 生成时间轴 build/v3_timeline.json（供配乐与渲染使用）
import fs from 'node:fs';
import { buildTimeline } from './story.js';
const tl = buildTimeline();
fs.writeFileSync(new URL('../build/v3_timeline.json', import.meta.url), JSON.stringify(tl, null, 1));
console.log(`total ${tl.total.toFixed(1)}s (${(tl.total / 60).toFixed(2)} min), sections ${tl.sections.length}, cards ${tl.sections.reduce((a, s) => a + s.cards.length, 0)}`);
for (const s of tl.sections) console.log(s.id.padEnd(9), s.start.toFixed(1).padStart(6), (s.dur.toFixed(1) + 's').padStart(7), 'E' + s.energy);
