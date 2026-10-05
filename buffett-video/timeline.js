// Shared timeline: the single source of truth for music and picture.
// Everything is measured in bars/beats so cuts, text reveals and sound hits
// land on the same grid.
(function (root) {
  const BPM = 96;
  const BEAT = 60 / BPM;          // 0.625 s
  const BAR = BEAT * 4;           // 2.5 s
  const FPS = 30;
  const TAIL = 3;                 // seconds of reverb tail after the last bar

  // subs  : local beats with an internal cut (soft deep whoosh)
  // hits  : local beats where something lands  (soft | land | big)
  const SCENES = [
    { id: 'hook',   bar: 0,   bars: 8,  years: [1965, 2024], subs: [8, 20],                hits: [{ b: 1, k: 'soft' }, { b: 20, k: 'land' }, { b: 26, k: 'soft' }] },
    { id: 'title',  bar: 8,   bars: 3,  years: [1930, 1930], subs: [],                     hits: [] },
    { id: 'thesis', bar: 11,  bars: 4,  years: [1930, 1930], subs: [],                     hits: [{ b: 4, k: 'land' }, { b: 8, k: 'land' }, { b: 12, k: 'land' }] },
    { id: 'ch1',    bar: 15,  bars: 7,  years: [1930, 1949], subs: [4, 16, 20],            hits: [{ b: 13, k: 'land' }] },
    { id: 'ch2',    bar: 22,  bars: 14, years: [1950, 1956], subs: [4, 8, 20, 36, 52],     hits: [{ b: 13, k: 'soft' }, { b: 29, k: 'soft' }, { b: 44, k: 'land' }] },
    { id: 'ch3',    bar: 36,  bars: 12, years: [1956, 1969], subs: [4, 8, 20, 36, 44],     hits: [{ b: 32, k: 'land' }, { b: 39, k: 'soft' }] },
    { id: 'ch4',    bar: 48,  bars: 16, years: [1970, 1972], subs: [4, 8, 20, 32, 48],     hits: [{ b: 12, k: 'land' }, { b: 28, k: 'land' }, { b: 60, k: 'land' }] },
    { id: 'ch5',    bar: 64,  bars: 16, years: [1973, 1998], subs: [4, 16, 28, 40, 52],    hits: [{ b: 10, k: 'land' }, { b: 22, k: 'soft' }, { b: 36, k: 'land' }, { b: 60, k: 'big' }] },
    { id: 'ch6',    bar: 80,  bars: 12, years: [1999, 2011], subs: [4, 20, 40],            hits: [{ b: 14, k: 'big' }, { b: 26, k: 'land' }, { b: 30, k: 'big' }] },
    { id: 'ch7',    bar: 92,  bars: 10, years: [2010, 2025], subs: [4, 14, 30],            hits: [{ b: 24, k: 'land' }] },
    { id: 'ch8',    bar: 102, bars: 14, years: [1965, 2024], subs: [4, 24, 36, 44],        hits: [{ b: 20, k: 'land' }, { b: 32, k: 'big' }, { b: 48, k: 'land' }] },
    { id: 'outro',  bar: 116, bars: 8,  years: [2025, 2025], subs: [14, 20, 28],           hits: [{ b: 16, k: 'soft' }, { b: 24, k: 'land' }] },
  ];
  const TOTAL_BARS = 124;
  const DURATION = TOTAL_BARS * BAR + TAIL;

  // ---------- harmony ----------
  const CH = {
    Dm: { root: 38, tones: [50, 53, 57] },
    Bb: { root: 34, tones: [46, 50, 53] },
    F:  { root: 41, tones: [48, 53, 57] },
    C:  { root: 36, tones: [48, 52, 55] },
    A:  { root: 33, tones: [49, 52, 57] },
    Gm: { root: 43, tones: [50, 55, 58] },
    D:  { root: 38, tones: [50, 54, 57] },
  };
  // per bar chord names
  const PROG = [];
  const put = (from, seq, times) => { for (let i = 0; i < times; i++) PROG[from + i] = seq[i % seq.length]; };
  put(0,   ['Dm', 'Dm', 'Bb', 'Bb', 'F', 'F', 'C', 'C'], 8);
  put(8,   ['Dm', 'Bb', 'C'], 3);
  put(11,  ['Dm', 'Bb', 'F', 'C'], 4);
  put(15,  ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'C'], 7);
  put(22,  ['Dm', 'Bb', 'F', 'C'], 14);
  put(36,  ['Dm', 'C', 'Bb', 'A'], 12);
  put(48,  ['Bb', 'F', 'C', 'Dm'], 16);
  put(64,  ['Dm', 'Bb', 'F', 'C'], 16);
  put(80,  ['Dm', 'Dm', 'Bb', 'A'], 5);
  put(85,  ['Dm'], 3);
  put(88,  ['Gm', 'Bb', 'C', 'A'], 4);
  put(92,  ['F', 'C', 'Dm', 'Bb'], 10);
  put(102, ['Bb', 'C', 'Dm', 'F'], 7);
  put(109, ['A'], 1);
  put(110, ['Dm', 'Bb', 'C', 'Dm', 'Bb', 'C'], 6);
  put(116, ['Bb', 'F', 'C', 'Dm'], 4);
  put(120, ['Bb', 'C', 'D', 'D'], 4);
  const chordAt = (bar) => CH[PROG[Math.max(0, Math.min(TOTAL_BARS - 1, Math.floor(bar)))]];

  // ---------- arrangement ----------
  // levels 0..1 ; kick pattern: none | one | half | four | heart
  const ARR = [
    { from: 0,   to: 8,   pad: 0.5,  piano: 1, sub: 0.35, arp: 0,    bass: 0,   kick: 'none', snare: 0,   taiko: 0,   strings: 0 },
    { from: 8,   to: 11,  pad: 0.8,  piano: 0, sub: 0.8, arp: 0.5,  bass: 0.6, kick: 'one',  snare: 0,   taiko: 0,   strings: 0.6 },
    { from: 11,  to: 15,  pad: 0.65, piano: 0, sub: 0.6, arp: 0.6,  bass: 0.6, kick: 'one',  snare: 0,   taiko: 0,   strings: 0 },
    { from: 15,  to: 22,  pad: 0.6,  piano: 2, sub: 0.5, arp: 0.5,  bass: 0.6, kick: 'half', snare: 0,   taiko: 0,   strings: 0 },
    { from: 22,  to: 36,  pad: 0.6,  piano: 0, sub: 0.5, arp: 0.75, bass: 0.8, kick: 'half', snare: 0.3, taiko: 0,   strings: 0 },
    { from: 36,  to: 48,  pad: 0.6,  piano: 0, sub: 0.5, arp: 0.8,  bass: 0.9, kick: 'four', snare: 0.5, taiko: 0,   strings: 0 },
    { from: 48,  to: 64,  pad: 0.75, piano: 3, sub: 0.6, arp: 0.8,  bass: 0.9, kick: 'four', snare: 0.55, taiko: 0.4, strings: 0.8 },
    { from: 64,  to: 80,  pad: 0.8,  piano: 0, sub: 0.6, arp: 0.9,  bass: 1,   kick: 'four', snare: 0.6, taiko: 0.7, strings: 0.7 },
    { from: 80,  to: 85,  pad: 0.7,  piano: 0, sub: 0.7, arp: 0.55, bass: 0.8, kick: 'half', snare: 0.4, taiko: 0.4, strings: 0 },
    { from: 85,  to: 88,  pad: 0.5,  piano: 0, sub: 0.9, arp: 0,    bass: 0,   kick: 'heart', snare: 0,  taiko: 0,   strings: 0.5 },
    { from: 88,  to: 92,  pad: 0.75, piano: 0, sub: 0.7, arp: 0.8,  bass: 0.9, kick: 'four', snare: 0.5, taiko: 0.6, strings: 0.6 },
    { from: 92,  to: 102, pad: 0.7,  piano: 0, sub: 0.6, arp: 0.9,  bass: 0.9, kick: 'four', snare: 0.5, taiko: 0.3, strings: 0.4 },
    { from: 102, to: 116, pad: 0.9,  piano: 0, sub: 0.7, arp: 1,    bass: 1,   kick: 'four', snare: 0.65, taiko: 0.9, strings: 1 },
    { from: 116, to: 120, pad: 0.7,  piano: 4, sub: 0.5, arp: 0.6,  bass: 0.6, kick: 'one',  snare: 0,   taiko: 0,   strings: 0.6 },
    { from: 120, to: 124, pad: 0.85, piano: 4, sub: 0.7, arp: 0.4,  bass: 0.7, kick: 'one',  snare: 0,   taiko: 0.5, strings: 0.9 },
  ];
  const arrAt = (bar) => ARR.find((a) => bar >= a.from && bar < a.to) || ARR[ARR.length - 1];

  // music drops out for one beat before the big "140x" landing and at the 2008 crash
  const SILENCE = [
    { from: 109 * 4 + 3, to: 110 * 4 },   // beat before ch8 big hit
    { from: 84 * 4 + 3.5, to: 85 * 4 },   // tiny gap before 2008
  ];

  // kick beat list (absolute beats) -> used by audio + picture pulses
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

  function sceneAt(t) {
    const bar = t / BAR;
    let s = SCENES[0];
    for (const sc of SCENES) if (bar >= sc.bar) s = sc;
    return s;
  }

  // absolute event lists for audio
  function events() {
    const trans = [], subs = [], hits = [];
    for (const s of SCENES) {
      if (s.bar > 0) trans.push({ beat: s.bar * 4, id: s.id });
      for (const b of s.subs) subs.push({ beat: s.bar * 4 + b });
      for (const h of s.hits) hits.push({ beat: s.bar * 4 + h.b, k: h.k });
    }
    return { trans, subs, hits };
  }

  root.TL = { BPM, BEAT, BAR, FPS, TAIL, SCENES, TOTAL_BARS, DURATION, CH, PROG, chordAt, ARR, arrAt, SILENCE, kickBeats, sceneAt, events };
})(typeof window !== 'undefined' ? window : module.exports);
