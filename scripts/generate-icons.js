import * as si from 'simple-icons';
import { slugToVariableName } from 'simple-icons/sdk';
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const APP_OUT    = path.join(__dirname, '../static/icons');
const PLUGIN_OUT = path.join(__dirname, '../../streamdeck-plugin/com.shadowbridge.app.sdPlugin/imgs/icons');
[APP_OUT, PLUGIN_OUT].forEach(d => fs.mkdirSync(d, { recursive: true }));

// [simple-icons slug, override hex (or null to use brand color), display label]
const BRAND_ICONS = [
  ['discord',          null,     'Discord'],
  ['spotify',          null,     'Spotify'],
  ['twitch',           null,     'Twitch'],
  ['obsstudio',        'FFFFFF', 'OBS Studio'],
  ['youtube',          null,     'YouTube'],
  ['googlechrome',     null,     'Chrome'],
  ['steam',            'C7D5E0', 'Steam'],
  ['vlcmediaplayer',   null,     'VLC'],
  ['teamspeak',        null,     'TeamSpeak'],
  ['teamviewer',       null,     'TeamViewer'],
];

// [id, hex color, label, inner SVG content (24x24 viewBox)]
const AUDIO_ICONS = [
  ['microphone', 'FF6B6B', 'Microphone', `
    <rect x="9" y="2" width="6" height="12" rx="3" fill="none" stroke="#FF6B6B" stroke-width="2"/>
    <path d="M5 10a7 7 0 0014 0" fill="none" stroke="#FF6B6B" stroke-width="2" stroke-linecap="round"/>
    <line x1="12" y1="22" x2="12" y2="17" stroke="#FF6B6B" stroke-width="2" stroke-linecap="round"/>
    <line x1="8" y1="22" x2="16" y2="22" stroke="#FF6B6B" stroke-width="2" stroke-linecap="round"/>
  `],
  ['headphones', '60A5FA', 'Headphones', `
    <path d="M3 18v-6a9 9 0 0118 0v6" fill="none" stroke="#60A5FA" stroke-width="2" stroke-linecap="round"/>
    <rect x="1" y="15" width="5" height="8" rx="2" fill="#60A5FA"/>
    <rect x="18" y="15" width="5" height="8" rx="2" fill="#60A5FA"/>
  `],
  ['headset', '818CF8', 'Headset', `
    <path d="M3 18v-6a9 9 0 0118 0v6" fill="none" stroke="#818CF8" stroke-width="2"/>
    <rect x="1" y="15" width="5" height="7" rx="2" fill="#818CF8"/>
    <rect x="18" y="15" width="5" height="7" rx="2" fill="#818CF8"/>
    <path d="M23 18a3 3 0 01-3 3h-1" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round"/>
  `],
  ['speaker', 'FB923C', 'Speaker', `
    <polygon points="11,5 6,9 2,9 2,15 6,15 11,19" fill="#FB923C"/>
    <path d="M15.54 8.46a5 5 0 010 7.07" fill="none" stroke="#FB923C" stroke-width="2" stroke-linecap="round"/>
    <path d="M19.07 4.93a10 10 0 010 14.14" fill="none" stroke="#FB923C" stroke-width="2" stroke-linecap="round"/>
  `],
  ['gamepad', '4ADE80', 'Game Audio', `
    <rect x="2" y="7" width="20" height="13" rx="4" fill="none" stroke="#4ADE80" stroke-width="2"/>
    <line x1="8" y1="13" x2="12" y2="13" stroke="#4ADE80" stroke-width="2" stroke-linecap="round"/>
    <line x1="10" y1="11" x2="10" y2="15" stroke="#4ADE80" stroke-width="2" stroke-linecap="round"/>
    <circle cx="16" cy="12" r="1" fill="#4ADE80"/>
    <circle cx="18" cy="14" r="1" fill="#4ADE80"/>
  `],
  ['bell', 'FCD34D', 'Alerts', `
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" fill="none" stroke="#FCD34D" stroke-width="2" stroke-linecap="round"/>
    <path d="M13.73 21a2 2 0 01-3.46 0" fill="none" stroke="#FCD34D" stroke-width="2" stroke-linecap="round"/>
  `],
  ['music', 'C084FC', 'Music', `
    <path d="M9 18V5l12-2v13" fill="none" stroke="#C084FC" stroke-width="2" stroke-linecap="round"/>
    <circle cx="6" cy="18" r="3" fill="none" stroke="#C084FC" stroke-width="2"/>
    <circle cx="18" cy="16" r="3" fill="none" stroke="#C084FC" stroke-width="2"/>
  `],
  ['waveform', '22D3EE', 'Audio', `
    <polyline points="2,12 5,8 8,16 11,5 14,19 17,8 20,12 22,12" fill="none" stroke="#22D3EE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  `],
  ['podcast', 'F472B6', 'Podcast', `
    <circle cx="12" cy="11" r="4" fill="none" stroke="#F472B6" stroke-width="2"/>
    <path d="M12 3C7.03 3 3 7.03 3 12" fill="none" stroke="#F472B6" stroke-width="2" stroke-linecap="round"/>
    <path d="M12 3c4.97 0 9 4.03 9 9" fill="none" stroke="#F472B6" stroke-width="2" stroke-linecap="round"/>
    <line x1="12" y1="19" x2="12" y2="22" stroke="#F472B6" stroke-width="2" stroke-linecap="round"/>
  `],
  ['phone', '34D399', 'Phone', `
    <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.8 19.79 19.79 0 01.21 1.18 2 2 0 012.2 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.92z" fill="none" stroke="#34D399" stroke-width="2" stroke-linecap="round"/>
  `],
  ['video', 'F87171', 'Video', `
    <polygon points="23,7 16,12 23,17" fill="#F87171"/>
    <rect x="1" y="5" width="15" height="14" rx="2" fill="none" stroke="#F87171" stroke-width="2"/>
  `],
  ['system', '94A3B8', 'System', `
    <rect x="2" y="3" width="20" height="14" rx="2" fill="none" stroke="#94A3B8" stroke-width="2"/>
    <line x1="8" y1="21" x2="16" y2="21" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
    <line x1="12" y1="17" x2="12" y2="21" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
  `],
  ['equalizer', '2DD4BF', 'EQ / Mixer', `
    <line x1="4" y1="21" x2="4" y2="14" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="4" y1="10" x2="4" y2="3"  stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="12" y1="21" x2="12" y2="12" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="12" y1="8" x2="12" y2="3"  stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="20" y1="21" x2="20" y2="16" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="20" y1="12" x2="20" y2="3"  stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="1" y1="12" x2="7" y2="12"  stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="9" y1="6"  x2="15" y2="6"  stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
    <line x1="17" y1="14" x2="23" y2="14" stroke="#2DD4BF" stroke-width="2" stroke-linecap="round"/>
  `],
  ['alert', 'FBBF24', 'Stream Alert', `
    <circle cx="12" cy="12" r="10" fill="none" stroke="#FBBF24" stroke-width="2"/>
    <line x1="12" y1="8" x2="12" y2="12" stroke="#FBBF24" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="12" cy="16" r="1.5" fill="#FBBF24"/>
  `],
  ['voice', '38BDF8', 'Voice Chat', `
    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round"/>
    <circle cx="9" cy="10" r="1.5" fill="#38BDF8"/>
    <circle cx="12" cy="10" r="1.5" fill="#38BDF8"/>
    <circle cx="15" cy="10" r="1.5" fill="#38BDF8"/>
  `],
];

async function svgToPng(svgContent, outPath) {
  await sharp(Buffer.from(svgContent)).resize(64, 64).png().toFile(outPath);
}

async function main() {
  console.log('Generating brand icons from simple-icons...');

  const brandManifest = [];
  for (const [slug, overrideHex, label] of BRAND_ICONS) {
    const varName = slugToVariableName(slug);
    const icon = si[varName];
    if (!icon) { console.warn(`  ⚠ Not found: ${slug} (tried ${varName})`); continue; }

    const hex = overrideHex ?? icon.hex;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="64" height="64">
      <path d="${icon.path}" fill="#${hex}"/>
    </svg>`;

    const fname = `${slug}.png`;
    await svgToPng(svg, path.join(APP_OUT, fname));
    await svgToPng(svg, path.join(PLUGIN_OUT, fname));
    brandManifest.push({ id: slug, label, color: `#${hex}`, src: `/icons/${fname}` });
    console.log(`  ✓ ${label}`);
  }

  console.log('Generating audio icons...');
  const audioManifest = [];
  for (const [name, hex, label, paths] of AUDIO_ICONS) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="64" height="64">
      ${paths}
    </svg>`;

    const fname = `${name}.png`;
    await svgToPng(svg, path.join(APP_OUT, fname));
    await svgToPng(svg, path.join(PLUGIN_OUT, fname));
    audioManifest.push({ id: name, label, color: `#${hex}`, src: `/icons/${fname}` });
    console.log(`  ✓ ${label}`);
  }

  const manifest = { brand: brandManifest, audio: audioManifest };
  const manifestJson = JSON.stringify(manifest, null, 2);
  fs.writeFileSync(path.join(APP_OUT, 'manifest.json'), manifestJson);
  fs.writeFileSync(path.join(PLUGIN_OUT, 'manifest.json'), manifestJson);
  console.log('✓ manifest.json written to both projects');
  console.log(`\nDone! ${brandManifest.length} brand + ${audioManifest.length} audio = ${brandManifest.length + audioManifest.length} total icons`);
}

main().catch(console.error);
