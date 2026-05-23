import { createCanvas, loadImage } from 'canvas';
import * as fs from 'fs';
import * as path from 'path';

const SIZE = 72;
const ICONS_DIR = path.join(__dirname, '..', 'node_modules', '@tabler', 'icons', 'icons', 'outline');

const DIR_COLORS: Record<string, string> = {
  OUT: '#22c55e', IN: '#3b82f6', APP: '#a855f7', MIC: '#f59e0b', MICOUT: '#ec4899',
};
const DIR_LABELS: Record<string, string> = {
  OUT: 'OUT', IN: 'IN', APP: 'APP', MIC: 'MIC IN', MICOUT: 'MIC OUT',
};

export interface ChannelData {
  name: string;
  color: string;
  icon: string;
  iconId: string | null;
  customIconBase64: string | null;
  direction: string;
  enabled: boolean;
  volume: number;
  status: string;
  level: number;
}

function hexToRgb(hex: string) {
  const clean = hex.replace('#', '').padEnd(6, '0');
  return {
    r: parseInt(clean.slice(0, 2), 16) || 0,
    g: parseInt(clean.slice(2, 4), 16) || 0,
    b: parseInt(clean.slice(4, 6), 16) || 0,
  };
}

/** Extract path `d` attributes from a Tabler SVG string, skipping the clear rect. */
function extractPaths(svgText: string): string[] {
  const paths: string[] = [];
  const re = /\bd="([^"]+)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(svgText)) !== null) {
    const d = m[1];
    // Skip the invisible bounding-box clear path
    if (d.startsWith('M0 0h24v24H0z') || d === 'M0 0h24v24H0z fill=none') continue;
    paths.push(d);
  }
  return paths;
}

function drawTablerIcon(
  ctx: CanvasRenderingContext2D,
  iconName: string,
  color: string,
  x: number,
  y: number,
  size: number,
) {
  // ti-brand-spotify → brand-spotify.svg
  const slug = iconName.replace(/^ti-/, '');
  const file = path.join(ICONS_DIR, `${slug}.svg`);
  if (!fs.existsSync(file)) return;

  const svg = fs.readFileSync(file, 'utf-8');
  const paths = extractPaths(svg);
  if (paths.length === 0) return;

  const scale = size / 24;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.strokeStyle = color;
  ctx.lineWidth = 2 / scale;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.fillStyle = 'none';

  for (const d of paths) {
    const p = new Path2D(d);
    ctx.stroke(p);
  }
  ctx.restore();
}

// ── PNG icon system ──────────────────────────────────────────────────────────

const BUNDLED_ICONS_DIR = path.join(__dirname, '..', 'imgs', 'icons');
const iconCache = new Map<string, any>();

async function loadIconImage(iconId: string): Promise<any | null> {
  if (iconCache.has(iconId)) return iconCache.get(iconId);
  const iconPath = path.join(BUNDLED_ICONS_DIR, `${iconId}.png`);
  if (!fs.existsSync(iconPath)) return null;
  try {
    const img = await loadImage(iconPath);
    iconCache.set(iconId, img);
    return img;
  } catch { return null; }
}

async function drawChannelIcon(
  ctx: any,
  ch: ChannelData,
  x: number,
  y: number,
  size: number
) {
  // Step 1 — Draw the backing square
  ctx.save();
  ctx.globalAlpha = 0.55;
  ctx.fillStyle = '#000000';
  ctx.beginPath();
  ctx.roundRect(x, y, size, size, size * 0.22);
  ctx.fill();
  ctx.restore();

  // Step 2 — Draw the icon image on top at full opacity
  ctx.save();
  ctx.globalAlpha = 1.0;

  const pad = size * 0.12;
  const iconX = x + pad;
  const iconY = y + pad;
  const iconSize = size - pad * 2;

  if (ch.customIconBase64) {
    try {
      const img = await loadImage(ch.customIconBase64);
      ctx.drawImage(img, iconX, iconY, iconSize, iconSize);
    } catch {
      drawFallbackIcon(ctx, ch.color, x, y, size);
    }
  } else {
    const iconId = ch.iconId ?? ch.icon?.replace('ti-', '') ?? null;
    if (iconId) {
      const img = await loadIconImage(iconId);
      if (img) {
        ctx.drawImage(img, iconX, iconY, iconSize, iconSize);
      } else {
        drawFallbackIcon(ctx, ch.color, x, y, size);
      }
    } else {
      drawFallbackIcon(ctx, ch.color, x, y, size);
    }
  }

  ctx.restore();
}

function drawFallbackIcon(
  ctx: any,
  color: string,
  x: number,
  y: number,
  size: number
) {
  ctx.save();
  ctx.globalAlpha = 1.0;
  ctx.fillStyle = color;
  const heights = [0.35, 0.65, 1.0, 0.65, 0.35];
  const h = size * 0.35;
  heights.forEach((ht, i) => {
    const bx = x + size * 0.1 + i * size * 0.16;
    const bh = h * ht * 1.8;
    ctx.beginPath();
    ctx.roundRect(bx, y + size / 2 - bh / 2, size * 0.10, bh, 1);
    ctx.fill();
  });
  ctx.restore();
}

// Keep old brand SVG data for backward compat with channels not yet migrated
const BRAND_SVGS: Record<string, string> = {
  discord:
    '<path fill="#5865F2" d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.015.043.03.056a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>',
  spotify:
    '<path fill="#1DB954" d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.36-.66.48-1.02.24-2.82-1.74-6.36-2.1-10.56-1.14-.42.12-.78-.18-.9-.54-.12-.42.18-.78.54-.9 4.56-1.02 8.52-.6 11.64 1.32.42.18.48.66.3 1.02zm1.44-3.3c-.3.42-.84.6-1.26.3-3.24-1.98-8.16-2.58-11.94-1.38-.48.12-1.02-.12-1.14-.6-.12-.48.12-1.02.6-1.14 4.38-1.32 9.84-.66 13.44 1.62.36.18.54.78.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.3c-.6.18-1.2-.18-1.38-.72-.18-.6.18-1.2.72-1.38 4.26-1.26 11.28-1.02 15.72 1.62.54.3.72 1.02.42 1.56-.3.42-1.02.6-1.56.3z"/>',
};

const OBS_ICON_PATH = path.join(__dirname, '..', 'imgs', 'obs_icon.png');

/** Cache resolved brand images to avoid re-encoding on every frame. */
const brandImageCache = new Map<string, any>();

/** Renders a brand icon (discord/spotify/obs). Returns true if drawn. */
async function drawBrandIcon(ctx: any, icon: string, x: number, y: number, sz: number): Promise<boolean> {
  const name = icon.replace(/^brand:/, '').replace(/^ti-brand-/, '');

  if (BRAND_SVGS[name]) {
    try {
      if (!brandImageCache.has(name)) {
        const svgText = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">${BRAND_SVGS[name]}</svg>`;
        const b64 = Buffer.from(svgText).toString('base64');
        const dataUrl = `data:image/svg+xml;base64,${b64}`;
        brandImageCache.set(name, await loadImage(dataUrl));
      }
      const img = brandImageCache.get(name);
      ctx.drawImage(img as any, x, y, sz, sz);
      return true;
    } catch (e) {
      console.error('drawBrandIcon svg error:', e);
    }
  }

  if (name === 'obs') {
    try {
      if (!brandImageCache.has('obs')) {
        brandImageCache.set('obs', await loadImage(OBS_ICON_PATH));
      }
      const img = brandImageCache.get('obs');
      ctx.drawImage(img as any, x, y, sz, sz);
      return true;
    } catch (e) {
      console.error('drawBrandIcon obs error:', e);
    }
  }

  return false;
}

function drawIconSafe(ctx: any, iconName: string, color: string, cx: number, cy: number, size: number) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = Math.max(1.5, size / 10);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.globalAlpha = 1;

  const h = size * 0.38;

  if (iconName?.includes('gamepad')) {
    ctx.beginPath();
    ctx.roundRect(cx - h, cy - h * 0.55, h * 2, h * 1.1, h * 0.25);
    ctx.stroke();
    ctx.beginPath(); ctx.arc(cx - h * 0.35, cy, h * 0.18, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + h * 0.35, cy, h * 0.18, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.moveTo(cx + h * 0.62, cy - h * 0.2); ctx.lineTo(cx + h * 0.62, cy + h * 0.2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + h * 0.42, cy); ctx.lineTo(cx + h * 0.82, cy); ctx.stroke();

  } else if (iconName?.includes('microphone') || iconName?.includes('mic')) {
    ctx.beginPath();
    ctx.roundRect(cx - h * 0.35, cy - h * 0.8, h * 0.7, h * 0.9, h * 0.35);
    ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy + h * 0.1, h * 0.6, Math.PI, 0); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy + h * 0.7); ctx.lineTo(cx, cy + h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - h * 0.4, cy + h); ctx.lineTo(cx + h * 0.4, cy + h); ctx.stroke();

  } else if (iconName?.includes('volume') || iconName?.includes('speaker')) {
    ctx.beginPath();
    ctx.moveTo(cx - h * 0.2, cy - h * 0.35);
    ctx.lineTo(cx - h * 0.65, cy - h * 0.35);
    ctx.lineTo(cx - h * 0.65, cy + h * 0.35);
    ctx.lineTo(cx - h * 0.2, cy + h * 0.35);
    ctx.lineTo(cx + h * 0.45, cy + h * 0.75);
    ctx.lineTo(cx + h * 0.45, cy - h * 0.75);
    ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx + h * 0.7, cy, h * 0.35, -Math.PI * 0.6, Math.PI * 0.6); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx + h * 0.7, cy, h * 0.6, -Math.PI * 0.5, Math.PI * 0.5); ctx.stroke();

  } else if (iconName?.includes('bell')) {
    ctx.beginPath();
    ctx.moveTo(cx, cy - h);
    ctx.bezierCurveTo(cx + h * 0.8, cy - h, cx + h * 0.8, cy + h * 0.4, cx + h * 0.8, cy + h * 0.4);
    ctx.lineTo(cx - h * 0.8, cy + h * 0.4);
    ctx.bezierCurveTo(cx - h * 0.8, cy + h * 0.4, cx - h * 0.8, cy - h, cx, cy - h);
    ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - h * 0.8, cy + h * 0.4); ctx.lineTo(cx + h * 0.8, cy + h * 0.4); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy + h * 0.7, h * 0.22, 0, Math.PI * 2); ctx.stroke();

  } else if (iconName?.includes('headset') || iconName?.includes('headphone')) {
    ctx.beginPath(); ctx.arc(cx, cy - h * 0.15, h * 0.75, Math.PI, 0); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(cx - h * 0.9, cy - h * 0.15, h * 0.3, h * 0.55, h * 0.15); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(cx + h * 0.6, cy - h * 0.15, h * 0.3, h * 0.55, h * 0.15); ctx.stroke();

  } else if (iconName?.includes('spotify')) {
    ctx.beginPath(); ctx.arc(cx, cy, h, 0, Math.PI * 2); ctx.stroke();
    const arcs: [number, number][] = [[cy - h * 0.25, h * 0.65], [cy, h * 0.5], [cy + h * 0.25, h * 0.35]];
    arcs.forEach(([ay, ar]) => {
      ctx.beginPath(); ctx.arc(cx - h * 0.3, ay, ar, -0.5, 0.5); ctx.stroke();
    });

  } else if (iconName?.includes('discord')) {
    ctx.beginPath();
    ctx.moveTo(cx - h * 0.8, cy - h * 0.6);
    ctx.bezierCurveTo(cx - h * 0.5, cy - h, cx + h * 0.5, cy - h, cx + h * 0.8, cy - h * 0.6);
    ctx.lineTo(cx + h * 0.8, cy + h * 0.3);
    ctx.bezierCurveTo(cx + h * 0.8, cy + h * 0.6, cx + h * 0.5, cy + h * 0.7, cx + h * 0.2, cy + h * 0.7);
    ctx.lineTo(cx - h * 0.4, cy + h);
    ctx.lineTo(cx - h * 0.4, cy + h * 0.7);
    ctx.bezierCurveTo(cx - h * 0.7, cy + h * 0.6, cx - h * 0.8, cy + h * 0.5, cx - h * 0.8, cy + h * 0.3);
    ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx - h * 0.3, cy, h * 0.2, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(cx + h * 0.3, cy, h * 0.2, 0, Math.PI * 2); ctx.fill();

  } else if (iconName?.includes('twitch') || iconName?.includes('broadcast')) {
    ctx.beginPath();
    ctx.moveTo(cx - h * 0.7, cy + h * 0.8);
    ctx.lineTo(cx - h * 0.7, cy - h);
    ctx.lineTo(cx + h * 0.7, cy - h);
    ctx.lineTo(cx + h * 0.7, cy + h * 0.2);
    ctx.lineTo(cx + h * 0.2, cy + h * 0.8);
    ctx.closePath(); ctx.stroke();
    ctx.beginPath(); ctx.roundRect(cx - h * 0.2, cy - h * 0.5, h * 0.2, h * 0.5, h * 0.05); ctx.fill();
    ctx.beginPath(); ctx.roundRect(cx + h * 0.2, cy - h * 0.5, h * 0.2, h * 0.5, h * 0.05); ctx.fill();

  } else if (iconName?.includes('music') || iconName?.includes('player')) {
    ctx.beginPath(); ctx.arc(cx - h * 0.3, cy + h * 0.5, h * 0.28, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx + h * 0.4, cy + h * 0.2, h * 0.28, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx - h * 0.02, cy + h * 0.5);
    ctx.lineTo(cx - h * 0.02, cy - h * 0.5);
    ctx.lineTo(cx + h * 0.68, cy - h * 0.5);
    ctx.lineTo(cx + h * 0.68, cy + h * 0.2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx - h * 0.02, cy - h * 0.5);
    ctx.lineTo(cx + h * 0.68, cy - h * 0.5);
    ctx.lineTo(cx + h * 0.68, cy - h * 0.18);
    ctx.lineTo(cx - h * 0.02, cy - h * 0.18);
    ctx.closePath(); ctx.fill();

  } else {
    // Generic waveform — 5 bars of varying height
    const heights = [0.35, 0.65, 1.0, 0.65, 0.35];
    heights.forEach((ht, i) => {
      const bx = cx - h * 0.6 + i * h * 0.3;
      const bh = h * ht * 1.6;
      ctx.beginPath();
      ctx.roundRect(bx, cy - bh / 2, h * 0.18, bh, h * 0.05);
      ctx.fill();
    });
  }

  ctx.restore();
}

export async function renderChannelStrip(ch: ChannelData, scale = 1): Promise<string> {
  try {
    return await _renderChannelStrip(ch, scale);
  } catch (err) {
    console.error('renderChannelStrip error:', err);
    const canvas = createCanvas(SIZE * scale, SIZE * scale);
    const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, SIZE * scale, SIZE * scale);
    ctx.fillStyle = '#ffffff';
    ctx.font = `10px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(ch?.name ?? 'ERR', (SIZE * scale) / 2, (SIZE * scale) / 2);
    return canvas.toDataURL('image/png');
  }
}

async function _renderChannelStrip(ch: ChannelData, scale = 1): Promise<string> {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  const { r, g, b } = hexToRgb(ch.color);

  // Background
  ctx.fillStyle = `rgba(${r},${g},${b},0.48)`;
  ctx.beginPath();
  (ctx as any).roundRect(0, 0, sz, sz, 8 * scale);
  ctx.fill();

  // Border
  ctx.strokeStyle = `rgba(${r},${g},${b},0.72)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  (ctx as any).roundRect(0.5, 0.5, sz - 1, sz - 1, 8 * scale);
  ctx.stroke();

  // Top accent bar
  ctx.fillStyle = ch.color;
  ctx.beginPath();
  (ctx as any).roundRect(0, 0, sz, 3 * scale, [8 * scale, 8 * scale, 0, 0]);
  ctx.fill();

  // Disabled overlay
  if (!ch.enabled) {
    ctx.fillStyle = 'rgba(0,0,0,0.45)';
    ctx.fillRect(0, 0, sz, sz);
  }

  // Icon
  const iconSize = 22 * scale;
  const iconX = sz / 2 - iconSize / 2;
  const iconY = 6 * scale;
  await drawChannelIcon(ctx, ch, iconX, iconY, iconSize);

  // Channel name
  ctx.fillStyle = ch.enabled ? '#e6edf3' : '#666666';
  ctx.font = `600 ${8 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const name = ch.name.length > 9 ? ch.name.slice(0, 8) + '\u2026' : ch.name;
  ctx.fillText(name, sz / 2, 31 * scale);

  // Direction badge
  const dirColor = DIR_COLORS[ch.direction] || ch.color;
  const dirLabel = DIR_LABELS[ch.direction] || ch.direction || 'OUT';
  const { r: dr, g: dg, b: db } = hexToRgb(dirColor);
  ctx.fillStyle = `rgba(${dr},${dg},${db},0.70)`;
  const badgeW = 28 * scale;
  const badgeH = 10 * scale;
  const badgeX = sz / 2 - badgeW / 2;
  const badgeY = 41 * scale;
  ctx.beginPath();
  (ctx as any).roundRect(badgeX, badgeY, badgeW, badgeH, 3 * scale);
  ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.font = `700 ${7 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(dirLabel, sz / 2, badgeY + badgeH / 2);

  // VU meter — 10 segments
  const meterY = 54 * scale;
  const meterH = 5 * scale;
  const meterPad = 3 * scale;
  const totalW = sz - meterPad * 2;
  const nBars = 10;
  const barW = (totalW - (nBars - 1) * 1.5 * scale) / nBars;
  const litBars = Math.round(ch.level * nBars);

  for (let i = 0; i < nBars; i++) {
    const bx = meterPad + i * (barW + 1.5 * scale);
    const isLit = i < litBars;
    let barColor: string;
    if (i >= nBars - 2)      barColor = isLit ? '#ff6b6b' : '#2a1515';
    else if (i >= nBars - 4) barColor = isLit ? '#ffd166' : '#2a2010';
    else                     barColor = isLit ? ch.color : '#21262d';
    ctx.fillStyle = barColor;
    ctx.beginPath();
    (ctx as any).roundRect(bx, meterY, barW, meterH, 1 * scale);
    ctx.fill();
  }

  // Status dot
  const dotColor = ch.status === 'active' ? '#3fb950' : ch.enabled ? '#484f58' : '#1a2535';
  ctx.fillStyle = dotColor;
  ctx.beginPath();
  ctx.arc(6 * scale, sz - 6 * scale, 3 * scale, 0, Math.PI * 2);
  ctx.fill();

  return canvas.toDataURL('image/png');
}

export async function renderStripHeader(ch: ChannelData, scale = 1): Promise<string> {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  const { r, g, b } = hexToRgb(ch.color);

  // Background
  ctx.fillStyle = `rgba(${r},${g},${b},0.48)`;
  ctx.fillRect(0, 0, sz, sz);

  // Top accent bar
  ctx.fillStyle = ch.color;
  ctx.fillRect(0, 0, sz, 3 * scale);

  // Full border
  ctx.strokeStyle = `rgba(${r},${g},${b},0.72)`;
  ctx.lineWidth = 1 * scale;
  ctx.strokeRect(0.5, 0.5, sz - 1, sz - 1);

  // Disabled overlay
  if (!ch.enabled) {
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(0, 0, sz, sz);
  }

  // Direction badge — top-center
  const dirColor = DIR_COLORS[ch.direction] || ch.color;
  const dirLabel = DIR_LABELS[ch.direction] || ch.direction || 'OUT';
  const { r: dr, g: dg, b: db } = hexToRgb(dirColor);
  const badgeW = 34 * scale;
  const badgeH = 12 * scale;
  const badgeX = sz / 2 - badgeW / 2;
  const badgeY = 6 * scale;
  ctx.fillStyle = `rgba(${dr},${dg},${db},0.70)`;
  ctx.beginPath();
  (ctx as any).roundRect(badgeX, badgeY, badgeW, badgeH, 4 * scale);
  ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.font = `700 ${7 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(dirLabel, sz / 2, badgeY + badgeH / 2);

  // Large icon box — transparent background lets icon colors show through
  const iconSz = 38 * scale;
  const iconX = sz / 2 - iconSz / 2;
  const iconY = 21 * scale;
  await drawChannelIcon(ctx, ch, iconX, iconY, iconSz);

  // Channel name — bottom
  ctx.fillStyle = ch.enabled ? '#e6edf3' : '#666666';
  ctx.font = `600 ${8 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  const name = ch.name.length > 9 ? ch.name.slice(0, 8) + '\u2026' : ch.name;
  ctx.fillText(name, sz / 2, sz - 3 * scale);

  return canvas.toDataURL('image/png');
}

export function renderStripFader(ch: ChannelData, muted: boolean, scale = 1): string {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  const { r, g, b } = hexToRgb(ch.color);

  ctx.fillStyle = `rgba(${r},${g},${b},0.48)`;
  ctx.fillRect(0, 0, sz, sz);

  // Border — left, right, bottom only (top shared with slot 0)
  ctx.strokeStyle = `rgba(${r},${g},${b},0.72)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  ctx.moveTo(0, 0); ctx.lineTo(0, sz); ctx.lineTo(sz, sz); ctx.lineTo(sz, 0);
  ctx.stroke();

  if (!ch.enabled) {
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(0, 0, sz, sz);
  }

  const trackX = sz / 2 - 1.5 * scale;
  const trackTop = 6 * scale;
  const trackBottom = sz - 26 * scale;
  const trackH = trackBottom - trackTop;

  ctx.fillStyle = '#21262d';
  ctx.beginPath();
  (ctx as any).roundRect(trackX, trackTop, 3 * scale, trackH, 2 * scale);
  ctx.fill();

  const vol = muted ? 0 : (ch.volume ?? 100) / 100;
  const fillH = trackH * vol;
  ctx.fillStyle = muted ? '#484f58' : ch.color;
  ctx.beginPath();
  (ctx as any).roundRect(trackX, trackBottom - fillH, 3 * scale, fillH, 2 * scale);
  ctx.fill();

  const handleY = trackBottom - fillH - 4 * scale;
  ctx.fillStyle = '#adbac7';
  ctx.beginPath();
  (ctx as any).roundRect(sz / 2 - 12 * scale, handleY, 24 * scale, 6 * scale, 2 * scale);
  ctx.fill();

  ctx.fillStyle = muted ? '#484f58' : '#8b949e';
  ctx.font = `600 ${8 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(muted ? 'MUTED' : `${ch.volume ?? 100}%`, sz / 2, sz - 22 * scale);

  const muteW = 44 * scale;
  const muteH = 14 * scale;
  const muteX = sz / 2 - muteW / 2;
  const muteY = sz - 15 * scale;

  if (muted) {
    ctx.fillStyle = '#7f1d1d';
    ctx.beginPath();
    (ctx as any).roundRect(muteX, muteY, muteW, muteH, 7 * scale);
    ctx.fill();
    ctx.fillStyle = '#f87171';
    ctx.font = `700 ${8 * scale}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('MUTED', sz / 2, muteY + muteH / 2);
  } else {
    ctx.fillStyle = `rgba(${r},${g},${b},0.30)`;
    ctx.beginPath();
    (ctx as any).roundRect(muteX, muteY, muteW, muteH, 7 * scale);
    ctx.fill();
    ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;
    ctx.font = `700 ${8 * scale}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('MUTE', sz / 2, muteY + muteH / 2);
  }

  return canvas.toDataURL('image/png');
}

export async function renderStripHeaderH(ch: ChannelData, scale = 1): Promise<string> {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  const { r, g, b } = hexToRgb(ch.color);

  ctx.fillStyle = `rgba(${r},${g},${b},0.48)`;
  ctx.fillRect(0, 0, sz, sz);

  // Left accent bar
  ctx.fillStyle = ch.color;
  ctx.fillRect(0, 0, 3 * scale, sz);

  // Border — top, bottom, left only (right shared with slot 1)
  ctx.strokeStyle = `rgba(${r},${g},${b},0.72)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  ctx.moveTo(sz, 0); ctx.lineTo(0, 0); ctx.lineTo(0, sz); ctx.lineTo(sz, sz);
  ctx.stroke();

  if (!ch.enabled) {
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(0, 0, sz, sz);
  }

  const iconSz = 22 * scale;
  const iconX = 8 * scale;
  const iconY = sz / 2 - iconSz / 2 - 8 * scale;
  await drawChannelIcon(ctx, ch, iconX, iconY, iconSz);

  ctx.fillStyle = ch.enabled ? '#e6edf3' : '#666666';
  ctx.font = `600 ${7 * scale}px Arial`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  const name = ch.name.length > 8 ? ch.name.slice(0, 7) + '\u2026' : ch.name;
  ctx.fillText(name, 8 * scale, iconY + iconSz + 3 * scale);

  const hDirColor = DIR_COLORS[ch.direction] || ch.color;
  const hDirLabel = DIR_LABELS[ch.direction] || ch.direction || 'OUT';
  const { r: hdr, g: hdg, b: hdb } = hexToRgb(hDirColor);
  const badgeW = 26 * scale;
  const badgeH = 10 * scale;
  const badgeX = 8 * scale;
  const badgeY = iconY + iconSz + 13 * scale;
  ctx.fillStyle = `rgba(${hdr},${hdg},${hdb},0.70)`;
  ctx.beginPath();
  (ctx as any).roundRect(badgeX, badgeY, badgeW, badgeH, 3 * scale);
  ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.font = `700 ${6 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(hDirLabel, badgeX + badgeW / 2, badgeY + badgeH / 2);

  // VU meter — vertical bars on right side
  const nBars = 8;
  const meterX = sz - 14 * scale;
  const meterW = 6 * scale;
  const meterPad = 4 * scale;
  const totalH = sz - meterPad * 2;
  const barH = (totalH - (nBars - 1) * scale) / nBars;
  const litBars = Math.round((ch.level ?? 0) * nBars);

  for (let i = 0; i < nBars; i++) {
    const by = meterPad + (nBars - 1 - i) * (barH + scale);
    const isLit = i < litBars;
    let barColor: string;
    if (i >= nBars - 2)      barColor = isLit ? '#ff6b6b' : '#2a1515';
    else if (i >= nBars - 3) barColor = isLit ? '#ffd166' : '#2a2010';
    else                     barColor = isLit ? ch.color  : '#21262d';
    ctx.fillStyle = barColor;
    ctx.beginPath();
    (ctx as any).roundRect(meterX, by, meterW, barH, 1 * scale);
    ctx.fill();
  }

  return canvas.toDataURL('image/png');
}

export function renderStripFaderH(ch: ChannelData, muted: boolean, scale = 1): string {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  const { r, g, b } = hexToRgb(ch.color);

  ctx.fillStyle = `rgba(${r},${g},${b},0.48)`;
  ctx.fillRect(0, 0, sz, sz);

  // Border — top, bottom, right only (left shared with slot 0)
  ctx.strokeStyle = `rgba(${r},${g},${b},0.72)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  ctx.moveTo(0, 0); ctx.lineTo(sz, 0); ctx.lineTo(sz, sz); ctx.lineTo(0, sz);
  ctx.stroke();

  if (!ch.enabled) {
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.fillRect(0, 0, sz, sz);
  }

  // Horizontal fader track
  const trackY = sz / 2 - 1.5 * scale;
  const trackLeft = 6 * scale;
  const trackRight = sz - 6 * scale;
  const trackW = trackRight - trackLeft;

  ctx.fillStyle = '#21262d';
  ctx.beginPath();
  (ctx as any).roundRect(trackLeft, trackY, trackW, 3 * scale, 2 * scale);
  ctx.fill();

  const vol = muted ? 0 : (ch.volume ?? 100) / 100;
  const fillW = trackW * vol;
  ctx.fillStyle = muted ? '#484f58' : ch.color;
  ctx.beginPath();
  (ctx as any).roundRect(trackLeft, trackY, fillW, 3 * scale, 2 * scale);
  ctx.fill();

  const handleX = trackLeft + fillW - 3 * scale;
  ctx.fillStyle = '#adbac7';
  ctx.beginPath();
  (ctx as any).roundRect(handleX, sz / 2 - 12 * scale, 6 * scale, 24 * scale, 2 * scale);
  ctx.fill();

  // VU meter at bottom
  const nBars = 8;
  const meterY = sz - 18 * scale;
  const meterH = 10 * scale;
  const meterPad = 4 * scale;
  const totalW = sz - meterPad * 2;
  const barW = (totalW - (nBars - 1) * scale) / nBars;
  const litBars = Math.round((ch.level ?? 0) * nBars);

  for (let i = 0; i < nBars; i++) {
    const bx = meterPad + i * (barW + scale);
    const isLit = i < litBars;
    let barColor: string;
    if (i >= nBars - 2)      barColor = isLit ? '#ff6b6b' : '#2a1515';
    else if (i >= nBars - 3) barColor = isLit ? '#ffd166' : '#2a2010';
    else                     barColor = isLit ? ch.color  : '#21262d';
    ctx.fillStyle = barColor;
    ctx.beginPath();
    (ctx as any).roundRect(bx, meterY, barW, meterH, 1 * scale);
    ctx.fill();
  }

  ctx.fillStyle = muted ? '#f87171' : `rgba(${r},${g},${b},0.7)`;
  ctx.font = `700 ${8 * scale}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(muted ? 'MUTED' : `${ch.volume ?? 100}%`, sz / 2, 4 * scale);

  return canvas.toDataURL('image/png');
}

export function renderFaderFull(ch: ChannelData, muted: boolean, scale = 1): { top: string; bottom: string } {
  const W = SIZE * scale;
  const H = SIZE * scale * 2;
  const canvas = createCanvas(W, H);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  const { r, g, b } = hexToRgb(ch.color);

  // Background
  ctx.fillStyle = `rgba(${r},${g},${b},0.48)`;
  ctx.fillRect(0, 0, W, H);

  // Left and right borders only
  ctx.strokeStyle = `rgba(${r},${g},${b},0.72)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  ctx.moveTo(0, 0); ctx.lineTo(0, H);
  ctx.moveTo(W, 0); ctx.lineTo(W, H);
  ctx.stroke();

  // Faint midpoint line showing button boundary
  ctx.strokeStyle = `rgba(${r},${g},${b},0.1)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2);
  ctx.stroke();

  // ── Fader track ──
  const trackX = W * 0.35;
  const trackW = 3 * scale;
  const trackTop = 10 * scale;
  const trackBottom = H - 10 * scale;
  const trackH = trackBottom - trackTop;

  ctx.fillStyle = '#21262d';
  ctx.beginPath();
  (ctx as any).roundRect(trackX, trackTop, trackW, trackH, 2 * scale);
  ctx.fill();

  const vol = muted ? 0 : (ch.volume ?? 100) / 100;
  const fillH = trackH * vol;
  ctx.fillStyle = muted ? '#484f58' : ch.color;
  ctx.beginPath();
  (ctx as any).roundRect(trackX, trackBottom - fillH, trackW, fillH, 2 * scale);
  ctx.fill();

  // Fader handle
  const handleW = W * 0.5;
  const handleH = 8 * scale;
  const handleX = trackX + trackW / 2 - handleW / 2;
  const handleY = trackBottom - fillH - 5 * scale;
  ctx.fillStyle = '#c8d8e0';
  ctx.beginPath();
  (ctx as any).roundRect(handleX, handleY, handleW, handleH, 3 * scale);
  ctx.fill();

  // ── VU meter — vertical segments on right side ──
  const nBars = 16;
  const meterRight = W - 8 * scale;
  const meterLeft = meterRight - 10 * scale;
  const meterTop = trackTop;
  const meterBottom = trackBottom;
  const meterH = meterBottom - meterTop;
  const barH = (meterH - (nBars - 1) * 2 * scale) / nBars;
  const litBars = Math.round((ch.level ?? 0) * nBars);

  for (let i = 0; i < nBars; i++) {
    const by = meterBottom - (i + 1) * (barH + 2 * scale) + 2 * scale;
    const isLit = i < litBars;
    let barColor: string;
    if (i >= nBars - 2)      barColor = isLit ? '#ff6b6b' : '#2a1515';
    else if (i >= nBars - 4) barColor = isLit ? '#ffd166' : '#2a2010';
    else                     barColor = isLit ? ch.color  : '#21262d';
    ctx.fillStyle = barColor;
    ctx.beginPath();
    (ctx as any).roundRect(meterLeft, by, meterRight - meterLeft, barH, 1 * scale);
    ctx.fill();
  }

  // Volume / mute label — top-left
  ctx.fillStyle = muted ? '#f87171' : '#8b949e';
  ctx.font = `600 ${9 * scale}px Arial`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillText(muted ? 'MUTE' : `${ch.volume ?? 100}%`, 6 * scale, 6 * scale);

  // Up/down arrow hints
  ctx.fillStyle = `rgba(${r},${g},${b},0.4)`;
  ctx.font = `${10 * scale}px Arial`;
  ctx.textAlign = 'right';
  ctx.fillText('\u25b2', W - 4 * scale, H * 0.25);
  ctx.fillText('\u25bc', W - 4 * scale, H * 0.75);

  // ── Split: crop top and bottom halves ──
  const topCanvas = createCanvas(W, SIZE * scale);
  const topCtx = topCanvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  (topCtx as any).drawImage(canvas as any, 0, 0, W, SIZE * scale, 0, 0, W, SIZE * scale);

  const botCanvas = createCanvas(W, SIZE * scale);
  const botCtx = botCanvas.getContext('2d') as unknown as CanvasRenderingContext2D;
  (botCtx as any).drawImage(canvas as any, 0, SIZE * scale, W, SIZE * scale, 0, 0, W, SIZE * scale);

  return {
    top: topCanvas.toDataURL('image/png'),
    bottom: botCanvas.toDataURL('image/png'),
  };
}

export function renderStartButton(isStreaming: boolean, scale = 1): string {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;

  if (isStreaming) {
    ctx.fillStyle = '#1e1014';
    ctx.beginPath();
    (ctx as any).roundRect(0, 0, sz, sz, 8 * scale);
    ctx.fill();
    ctx.strokeStyle = '#3a1e1a';
    ctx.lineWidth = 1 * scale;
    ctx.beginPath();
    (ctx as any).roundRect(0.5, 0.5, sz - 1, sz - 1, 8 * scale);
    ctx.stroke();
    // Stop square
    ctx.fillStyle = '#f78166';
    const sq = 18 * scale;
    ctx.fillRect(sz / 2 - sq / 2, sz / 2 - sq / 2 - 6 * scale, sq, sq);
    ctx.font = `700 ${10 * scale}px Arial`;
    ctx.fillStyle = '#f78166';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('STOP', sz / 2, sz / 2 + 14 * scale);
  } else {
    ctx.fillStyle = '#0d2018';
    ctx.beginPath();
    (ctx as any).roundRect(0, 0, sz, sz, 8 * scale);
    ctx.fill();
    ctx.strokeStyle = '#1e4228';
    ctx.lineWidth = 1 * scale;
    ctx.beginPath();
    (ctx as any).roundRect(0.5, 0.5, sz - 1, sz - 1, 8 * scale);
    ctx.stroke();
    // Play triangle
    ctx.fillStyle = '#3fb950';
    const cx = sz / 2 - 2 * scale;
    const cy = sz / 2 - 6 * scale;
    const ts = 16 * scale;
    ctx.beginPath();
    ctx.moveTo(cx - ts / 2, cy - ts / 2);
    ctx.lineTo(cx + ts / 2, cy);
    ctx.lineTo(cx - ts / 2, cy + ts / 2);
    ctx.closePath();
    ctx.fill();
    ctx.font = `700 ${10 * scale}px Arial`;
    ctx.fillStyle = '#3fb950';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('START', sz / 2, sz / 2 + 12 * scale);
  }

  return canvas.toDataURL('image/png');
}

export function renderConnectionButton(connected: boolean, peerIp: string | null, scale = 1): string {
  const sz = SIZE * scale;
  const canvas = createCanvas(sz, sz);
  const ctx = canvas.getContext('2d') as unknown as CanvasRenderingContext2D;

  const color = connected ? '#3fb950' : '#e3b341';
  const { r, g, b } = hexToRgb(color);

  ctx.fillStyle = `rgba(${r},${g},${b},0.12)`;
  ctx.beginPath();
  (ctx as any).roundRect(0, 0, sz, sz, 8 * scale);
  ctx.fill();
  ctx.strokeStyle = `rgba(${r},${g},${b},0.3)`;
  ctx.lineWidth = 1 * scale;
  ctx.beginPath();
  (ctx as any).roundRect(0.5, 0.5, sz - 1, sz - 1, 8 * scale);
  ctx.stroke();

  // Status dot
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(sz / 2, sz / 2 - 10 * scale, 10 * scale, 0, Math.PI * 2);
  ctx.fill();

  ctx.font = `700 ${9 * scale}px Arial`;
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(connected ? 'PEER'    : 'SEARCH', sz / 2, sz / 2 + 4 * scale);
  ctx.fillText(connected ? 'ONLINE'  : 'ING...',  sz / 2, sz / 2 + 15 * scale);

  return canvas.toDataURL('image/png');
}
