import { createCanvas } from '@napi-rs/canvas';
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const norm = (t, t0, t1) => clamp((t - t0) / (t1 - t0));
export const mix = (a, b, t) => Array.isArray(a) ? a.map((v, i) => lerp(v, b[i], t)) : lerp(a, b, t);

export function rng(seed = 1) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

export function cubicBezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = t => ((ax * t + bx) * t + cx) * t, sy = t => ((ay * t + by) * t + cy) * t;
  const dx = t => (3 * ax * t + 2 * bx) * t + cx;
  return x => {
    if (x <= 0) return 0; if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) { const e = sx(t) - x, d = dx(t); if (Math.abs(e) < 1e-6 || Math.abs(d) < 1e-6) break; t -= e / d; }
    t = clamp(t); return sy(t);
  };
}
export const E = {
  linear: t => t,
  sine: t => -(Math.cos(Math.PI * t) - 1) / 2,
  expoOut: t => t >= 1 ? 1 : 1 - Math.pow(2, -10 * t),
  start: t => t <= 0 ? 0 : t >= 1 ? 1 : 1 - 0.65 * Math.pow(1 - t, 3.2),
  drop: cubicBezier(0.42, 0, 0.25, 1),
  camera: cubicBezier(0.42, 0, 0.36, 1),
  spread: t => t < 0.62 ? 1.1 * Math.pow(t / 0.62, 1.6) : 1.1 - 0.1 * E.sine((t - 0.62) / 0.38),
  push: u => { u = clamp(u); return 1 - Math.pow(1 - u, 4) * (1 + 4 * u); },
  spring: (t, z = 0.72, w = 9) => { if (t <= 0) return 0; if (t >= 1) return 1; const wd = w * Math.sqrt(1 - z * z); const v = 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t)); return lerp(v, 1, Math.pow(t, 6)); },
  critical: (t, w = 8) => { if (t >= 1) return 1; const v = 1 - Math.exp(-w * t) * (1 + w * t); return lerp(v, 1, Math.pow(t, 6)); },
};
export function pop(t, t0, fps, peak = 1.18, up = 2.5, settle = 7) {
  const f = (t - t0) * fps; if (f <= 0) return 0;
  if (f < up) return peak * E.expoOut(f / up);
  return lerp(peak, 1, E.sine(clamp((f - up) / settle)));
}

export function kf(t, keys) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, ease = E.sine] = keys[i], [t0, v0] = keys[i - 1];
    if (t <= t1) return mix(v0, v1, ease(norm(t, t0, t1)));
  }
  return keys[keys.length - 1][1];
}
export const tween = (t, t0, t1, a, b, ease = E.sine) => mix(a, b, ease(norm(t, t0, t1)));
export const between = (t, a, b) => t >= a && t < b;

export function grid(bpm, offset = 0) {
  const beat = 60 / bpm;
  return { bpm, beat, at: n => offset + n * beat, eighth: n => offset + n * beat / 2, snap: (t, div = 2) => offset + Math.round((t - offset) / (beat / div)) * (beat / div), index: t => (t - offset) / beat };
}

export function smoothPath(fn, duration, fps, sigma = 0.16) {
  const n = Math.ceil(duration * fps) + 1, raw = [];
  for (let i = 0; i < n; i++) raw.push(fn(i / fps));
  const s = sigma * fps, r = Math.ceil(s * 3), w = [];
  for (let k = -r; k <= r; k++) w.push(Math.exp(-(k * k) / (2 * s * s)));
  const out = raw.map((_, i) => { const acc = raw[0].map(() => 0); let ws = 0; for (let k = -r; k <= r; k++) { const j = clamp(i + k, 0, n - 1); const wk = w[k + r]; raw[j].forEach((v, d) => acc[d] += v * wk); ws += wk; } return acc.map(v => v / ws); });
  return t => { const f = clamp(t * fps, 0, n - 1), i = Math.floor(f), fr = f - i, a = out[i], b = out[Math.min(i + 1, n - 1)]; return a.map((v, d) => lerp(v, b[d], fr)); };
}

export function typing(t, text, t0, avg = 0.06, seed = 7, riseFrames = 2, fps = 30) {
  const r = rng(seed); let at = t0; const out = [];
  for (const ch of text) { out.push({ ch, start: at, p: clamp((t - at) * fps / riseFrames) }); at += avg * (0.55 + r() * 0.9) * (ch === ' ' ? 1.8 : 1); }
  return { letters: out, end: at, caretX: out.filter(l => l.p > 0).length };
}
export const caret = (t, end) => t < end + 0.35 ? 1 : 0.5 + 0.5 * Math.cos((t - end - 0.35) * Math.PI * 2 * 0.9);

export async function render({ width = 1080, height = 1920, fps = 30, duration, draw, out = 'out.mp4', subframes = 8, shutter = 0.5, crf = 18, preset = 'veryfast', from = 0, to, audio, log = true }) {
  const canvas = createCanvas(width, height), ctx = canvas.getContext('2d');
  const N = Math.round(duration * fps), last = to ?? N;
  const args = ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${width}x${height}`, '-r', String(fps), '-i', '-'];
  if (audio) args.push('-i', audio, '-c:a', 'aac', '-b:a', '256k', '-shortest');
  args.push('-c:v', 'libx264', '-preset', preset, '-crf', String(crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out);
  const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'ignore', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  const acc = new Float32Array(width * height * 4), buf = Buffer.alloc(width * height * 4);
  const t0 = Date.now();
  for (let f = from; f < last; f++) {
    const t = f / fps;
    const n = Math.max(1, typeof subframes === 'function' ? subframes(t) : subframes);
    if (n === 1) { ctx.setTransform(1, 0, 0, 1, 0, 0); draw(ctx, t, { frame: f, fps, width, height }); buf.set(ctx.getImageData(0, 0, width, height).data); }
    else {
      acc.fill(0);
      for (let i = 0; i < n; i++) {
        const ts = t + ((i + 0.5) / n - 0.5) * shutter / fps;
        ctx.setTransform(1, 0, 0, 1, 0, 0); draw(ctx, ts, { frame: f, fps, width, height, sub: i });
        const d = ctx.getImageData(0, 0, width, height).data;
        for (let k = 0; k < d.length; k++) acc[k] += d[k];
      }
      for (let k = 0; k < acc.length; k++) buf[k] = acc[k] / n + 0.5;
    }
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (log && f % fps === 0) process.stderr.write(`frame ${f}/${last} ${((Date.now() - t0) / 1000).toFixed(1)}s\n`);
  }
  ff.stdin.end(); await done;
  return out;
}

export function still({ width = 1080, height = 1920, fps = 30, draw, times = [0], prefix = 'still' }) {
  const canvas = createCanvas(width, height), ctx = canvas.getContext('2d');
  return times.map(t => { ctx.setTransform(1, 0, 0, 1, 0, 0); draw(ctx, t, { frame: Math.round(t * fps), fps, width, height }); const p = `${prefix}_${t.toFixed(2)}s.png`; writeFileSync(p, canvas.toBuffer('image/png')); return p; });
}

export function roundRect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
export function glow(ctx, x, y, r, color, strength = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r * 2.1); g.addColorStop(0, color); g.addColorStop(0.55, color.replace(/[\d.]+\)$/, `${0.5 * strength})`)); g.addColorStop(1, color.replace(/[\d.]+\)$/, '0)'));
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 2.1, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}
export function maskedText(ctx, str, x, y, size, p, opts = {}) {
  const { font = `700 ${size}px sans-serif`, color = '#fff', align = 'center' } = opts;
  ctx.save(); ctx.font = font; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  const w = ctx.measureText(str).width; const left = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  ctx.beginPath(); ctx.rect(left - size, y - size * 1.05, w + size * 2, size * 1.35); ctx.clip();
  ctx.fillStyle = color; ctx.fillText(str, x, y + (1 - E.expoOut(clamp(p))) * size * 1.25); ctx.restore();
}
