// 由时间轴生成带时间码的屏幕文字稿 output/文字稿.md
import fs from 'node:fs';
const tl = JSON.parse(fs.readFileSync(new URL('../build/v3_timeline.json', import.meta.url)));
const names = { cold: '冷开场', paradox: '悖论', title: '片名', origin: '出厂', darwin: '达尔文', organ: '核心观点', clock: '时间错配', set1: '出厂设置 01 · 恐惧', snake: '怕蛇的证据', set2: '出厂设置 02 · 食欲', set3: '出厂设置 03 · 社交', quiz: '互动测试', set4: '出厂设置 04 · 合作', warning: '三个提醒', return: '回到草丛', finale: '终章', refs: '参考资料' };
const ts = t => String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(Math.floor(t % 60)).padStart(2, '0');
const o = ['# 出厂设置：你的大脑，比你想的更古老', '', `> v3 屏幕文字稿（无旁白，配乐卡点）· 时长约 ${(tl.total / 60).toFixed(1)} 分钟 · ${tl.bpm} BPM · [ ] 为橙色高亮`, ''];
for (const s of tl.sections) {
  if (s.id === 'refs') continue;
  o.push(`## ${ts(s.start)} ${names[s.id]}（能量 ${s.energy}${s.impact ? ' · 低频冲击' : ''}）`, '');
  for (const c of s.cards) {
    if (!c.t) { if (c.tick) o.push(`- **[${ts(s.start + c.start)}]** 倒计时 ${c.tick}`); continue; }
    o.push(`- **[${ts(s.start + c.start)}]** ${c.t.replace(/\|/g, ' ')}${c.unlock ? `  ← 解锁 ${c.unlock}/4` : ''}${c.hit ? '  ← 重击' : ''}`);
  }
  o.push('');
}
fs.writeFileSync(new URL('../output/文字稿.md', import.meta.url), o.join('\n'));
console.log('ok');
