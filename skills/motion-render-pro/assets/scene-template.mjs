import { render, still, E, kf, pop, grid, smoothPath, glow } from './motion-tools/engine.mjs';

const W = 1080, H = 1920, FPS = 30, D = 6, G = grid(120);
const cam = smoothPath(t => [kf(t, [[0, 1], [3, 1.25, E.camera], [6, 1.1]])], D, FPS);

function draw(ctx, t) {
  ctx.fillStyle = '#E6E3DC'; ctx.fillRect(0, 0, W, H);
  const [k] = cam(t); ctx.translate(W / 2, H / 2); ctx.scale(k, k); ctx.translate(-W / 2, -H / 2);
  const s = pop(t, G.at(1), FPS);
  const x = kf(t, [[1.5, 300], [2.5, 780, E.drop]]);
  glow(ctx, x, 1100, 90 * s, 'rgba(240,102,43,0.55)');
  ctx.fillStyle = '#F0662B'; ctx.beginPath(); ctx.arc(x, 1100, 90 * s, 0, Math.PI * 2); ctx.fill();
}

if (process.argv.includes('--stills')) still({ width: W, height: H, draw, times: [0.6, 1.2, 2.0, 2.6], prefix: 'check' });
else await render({ width: W, height: H, fps: FPS, duration: D, draw, out: 'out.mp4', subframes: t => (t > 1.5 && t < 2.5 ? 16 : 8) });
