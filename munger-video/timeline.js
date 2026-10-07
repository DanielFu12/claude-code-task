// Shared timeline for the Munger video: one grid for music and picture.
(function (root) {
  const BPM = 90;
  const BEAT = 60 / BPM;          // 0.667 s
  const BAR = BEAT * 4;           // 2.667 s
  const FPS = 30;
  const TAIL = 3;

  // subs: local beats with an internal cut (soft deep whoosh); hits: local beats where something lands
  const S = (b, k) => ({ b, k });
  const SCENES = [
    { id: 'hook',  bar: 0,   bars: 8,  years: [1924, 2023], subs: [8, 16, 24],              hits: [S(1, 'soft'), S(12, 'soft')] },
    { id: 'title', bar: 8,   bars: 3,  years: [1924, 1924], subs: [],                       hits: [] },
    { id: 'map',   bar: 11,  bars: 5,  years: [1924, 1924], subs: [],                       hits: [S(2, 'soft'), S(4, 'soft'), S(6, 'soft'), S(8, 'soft'), S(10, 'soft'), S(12, 'soft'), S(14, 'land')] },
    { id: 'ch1',   bar: 16,  bars: 14, years: [1924, 1978], subs: [4, 14, 24, 34, 46],      hits: [S(24, 'land'), S(40, 'land')] },
    { id: 'ch2',   bar: 30,  bars: 20, years: [1994, 1996], subs: [4, 16, 36, 48, 56, 68],  hits: [S(12, 'soft'), S(44, 'land'), S(75, 'land')] },
    { id: 'ch3',   bar: 50,  bars: 20, years: [1986, 1995], subs: [4, 16, 28, 56, 68],      hits: [S(26, 'land'), S(64, 'soft')] },
    { id: 'ch4',   bar: 70,  bars: 10, years: [1996, 1996], subs: [4, 24],                  hits: [S(14, 'land')] },
    { id: 'ch5',   bar: 80,  bars: 20, years: [1972, 1997], subs: [4, 20, 30, 40, 52, 68],  hits: [S(16, 'land'), S(36, 'land'), S(72, 'land')] },
    { id: 'ch6',   bar: 100, bars: 16, years: [2000, 2009], subs: [4, 20, 36, 48],          hits: [S(40, 'big')] },
    { id: 'ch7',   bar: 116, bars: 14, years: [1973, 2009], subs: [4, 20, 36],              hits: [S(16, 'land'), S(48, 'big')] },
    { id: 'ch8',   bar: 130, bars: 20, years: [2007, 2023], subs: [4, 20, 36, 52, 64],      hits: [S(66, 'soft')] },
    { id: 'outro', bar: 150, bars: 10, years: [2023, 2023], subs: [16, 26, 32],             hits: [S(26, 'land'), S(36, 'land')] },
  ];
  const TOTAL_BARS = 160;
  const DURATION = TOTAL_BARS * BAR + TAIL;

  // ---------- harmony (E minor) ----------
  const CH = {
    Em: { root: 40, tones: [52, 55, 59] },
    C:  { root: 36, tones: [48, 52, 55] },
    G:  { root: 43, tones: [50, 55, 59] },
    D:  { root: 38, tones: [50, 54, 57] },
    Am: { root: 33, tones: [45, 48, 52] },
    B:  { root: 35, tones: [47, 51, 54] },
    E:  { root: 40, tones: [52, 56, 59] },
  };
  const SCALE = [4, 6, 7, 9, 11, 0, 2]; // E F# G A B C D (pitch classes)
  const PROG = [];
  const put = (from, seq, times) => { for (let i = 0; i < times; i++) PROG[from + i] = seq[i % seq.length]; };
  put(0,   ['Em', 'Em', 'C', 'C', 'G', 'G', 'D', 'D'], 8);
  put(8,   ['Em', 'C', 'D'], 3);
  put(11,  ['Em', 'C', 'G', 'D', 'Em'], 5);
  put(16,  ['Em', 'C', 'G', 'D'], 14);
  put(30,  ['Em', 'C', 'G', 'D'], 20);
  put(50,  ['Em', 'Em', 'C', 'B'], 20);
  put(70,  ['C', 'G', 'D', 'Em'], 10);
  put(80,  ['Em', 'C', 'G', 'D'], 20);
  put(100, ['Am', 'Am', 'Em', 'Em'], 8);
  put(108, ['C', 'B'], 2);
  put(110, ['Em', 'C', 'G', 'D', 'Em', 'C'], 6);
  put(116, ['C', 'D', 'Em', 'G'], 11);
  put(127, ['B'], 1);
  put(128, ['C', 'D'], 2);
  put(130, ['C', 'G', 'Am', 'Em'], 16);
  put(146, ['C', 'D', 'Em', 'Em'], 4);
  put(150, ['C', 'G', 'D', 'Em'], 8);
  put(158, ['C', 'E'], 2);
  const chordAt = (bar) => CH[PROG[Math.max(0, Math.min(TOTAL_BARS - 1, Math.floor(bar)))]];

  // ---------- arrangement ----------
  // piano: 0 | hook | broken | lead | sparse ; strings: 0 | pad | lead (value = level)
  const A = (from, to, o) => Object.assign({ from, to, pad: 0.6, piano: 0, sub: 0.5, arp: 0, bass: 0, kick: 'none', snare: 0, taiko: 0, strings: 0, smode: 'pad' }, o);
  const ARR = [
    A(0, 8,     { pad: 0.5, piano: 'hook', sub: 0.35 }),
    A(8, 11,    { pad: 0.8, sub: 0.8, arp: 0.5, bass: 0.6, kick: 'one', strings: 0.9, smode: 'lead' }),
    A(11, 16,   { pad: 0.65, arp: 0.6, bass: 0.6, kick: 'one' }),
    A(16, 30,   { pad: 0.6, piano: 'broken', arp: 0.45, bass: 0.6, kick: 'half' }),
    A(30, 40,   { pad: 0.6, arp: 0.75, bass: 0.8, kick: 'half', snare: 0.3 }),
    A(40, 50,   { pad: 0.65, arp: 0.8, bass: 0.9, kick: 'four', snare: 0.45, taiko: 0.4 }),
    A(50, 70,   { pad: 0.65, arp: 0.7, bass: 0.9, kick: 'four', snare: 0.5, taiko: 0.5, strings: 0.5 }),
    A(70, 80,   { pad: 0.6, piano: 'lead', arp: 0.5, bass: 0.7, kick: 'half', snare: 0.3 }),
    A(80, 100,  { pad: 0.8, arp: 0.9, bass: 1, kick: 'four', snare: 0.6, taiko: 0.7, strings: 0.7 }),
    A(100, 108, { pad: 0.5, piano: 'sparse', sub: 0.9, kick: 'heart', strings: 0.4 }),
    A(108, 110, { pad: 0.65, sub: 0.7, arp: 0.5, bass: 0.7, kick: 'half', taiko: 0.6 }),
    A(110, 116, { pad: 0.9, sub: 0.7, arp: 1, bass: 1, kick: 'four', snare: 0.6, taiko: 0.9, strings: 1, smode: 'lead' }),
    A(116, 128, { pad: 0.8, sub: 0.6, arp: 0.9, bass: 1, kick: 'four', snare: 0.6, taiko: 0.7, strings: 0.8 }),
    A(128, 130, { pad: 0.9, sub: 0.7, arp: 1, bass: 1, kick: 'four', snare: 0.65, taiko: 1, strings: 1, smode: 'lead' }),
    A(130, 138, { pad: 0.7, piano: 'lead', arp: 0.35, bass: 0.6, kick: 'one', strings: 0.7 }),
    A(138, 146, { pad: 0.7, piano: 'lead', arp: 0.45, bass: 0.7, kick: 'half', strings: 0.7 }),
    A(146, 150, { pad: 0.8, arp: 0.8, bass: 0.9, kick: 'four', snare: 0.5, taiko: 0.6, strings: 0.9, smode: 'lead' }),
    A(150, 158, { pad: 0.85, piano: 'broken', sub: 0.6, arp: 0.6, bass: 0.8, kick: 'one', strings: 0.9, smode: 'lead' }),
    A(158, 160, { pad: 0.85, sub: 0.7, bass: 0.7, kick: 'one', taiko: 0.5, strings: 0.9 }),
  ];
  const arrAt = (bar) => ARR.find((a) => bar >= a.from && bar < a.to) || ARR[ARR.length - 1];
  // section dynamics (dB)
  const DYN = [[0, -7], [8, 0], [11, -4], [16, -5], [30, -3], [40, -2], [70, -4], [80, 0], [100, -6], [108, -2], [110, 1], [116, 0], [128, 1], [130, -3], [146, -1], [150, 0], [158, -2]];

  const SILENCE = [
    { from: 109 * 4 + 3, to: 110 * 4 },   // beat before "下重注"
    { from: 127 * 4 + 3, to: 128 * 4 },   // beat before the compounding climax
  ];
  const RISERS = [[7, 8, 0.8], [108, 109.75, 0.9], [126, 127.75, 0.8], [146, 147.9, 0.5]];

  function kickBeats() {
    const out = [];
    for (let bar = 0; bar < TOTAL_BARS; bar++) {
      const a = arrAt(bar);
      const pat = { none: [], one: [0], half: [0, 2], four: [0, 1, 2, 3], heart: [0, 0.35, 2, 2.35] }[a.kick];
      for (const p of pat) {
        const b = bar * 4 + p;
        if (SILENCE.some((s) => b >= s.from && b < s.to)) continue;
        out.push(b);
      }
    }
    return out;
  }
  function sceneAt(t) { const bar = t / BAR; let s = SCENES[0]; for (const sc of SCENES) if (bar >= sc.bar) s = sc; return s; }
  function events() {
    const trans = [], subs = [], hits = [];
    for (const s of SCENES) {
      if (s.bar > 0) trans.push({ beat: s.bar * 4, id: s.id });
      for (const b of s.subs) subs.push({ beat: s.bar * 4 + b });
      for (const h of s.hits) hits.push({ beat: s.bar * 4 + h.b, k: h.k });
    }
    return { trans, subs, hits };
  }

  root.TL = { BPM, BEAT, BAR, FPS, TAIL, SCENES, TOTAL_BARS, DURATION, CH, SCALE, PROG, chordAt, ARR, arrAt, DYN, SILENCE, RISERS, kickBeats, sceneAt, events };
})(typeof window !== 'undefined' ? window : module.exports);
