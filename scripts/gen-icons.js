// Generate the recipe site's PWA icons: a white utensils-crossed glyph on a
// terracotta (#c2410c) vertical gradient squircle. Matches the shared
// gradient-glyph icon family used across the PWD dashboards.
//
// Requires `sharp` (npm i sharp). Run from the repo root:
//   node scripts/gen-icons.js
// Outputs into site/app-icons/.
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'site', 'app-icons');
const COLOR = '#c2410c';
const GLYPH = '<path d="m16 2-2.3 2.3a3 3 0 0 0 0 4.2l1.8 1.8a3 3 0 0 0 4.2 0L22 8"/><path d="M15 15 3.3 3.3a4.2 4.2 0 0 0 0 6l7.3 7.3c.7.7 2 .7 2.8 0L15 15Zm0 0 7 7"/><path d="m2.1 21.8 6.4-6.3"/><path d="m19 5-7 7"/>';

// [name, size, rounded?, glyphFrac]
const JOBS = [
  ['icon-32.png',           32,  false, 0.56],
  ['icon-180.png',          180, false, 0.50],
  ['icon-192.png',          192, true,  0.48],
  ['icon-512.png',          512, true,  0.48],
  ['icon-maskable-512.png', 512, false, 0.40],
];

function darken(h,f){const n=parseInt(h.slice(1),16);let r=(n>>16)&255,g=(n>>8)&255,b=n&255;r=Math.round(r*f);g=Math.round(g*f);b=Math.round(b*f);return`#${((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1)}`;}
function lighten(h,f){const n=parseInt(h.slice(1),16);let r=(n>>16)&255,g=(n>>8)&255,b=n&255;r=Math.round(r+(255-r)*f);g=Math.round(g+(255-g)*f);b=Math.round(b+(255-b)*f);return`#${((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1)}`;}

function svg(size, rounded, glyphFrac){
  const R = rounded ? Math.round(size*0.225) : 0;
  const box = Math.round(size*glyphFrac);
  const off = (size-box)/2;
  const scale = box/24;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${lighten(COLOR,0.12)}"/>
      <stop offset="1" stop-color="${darken(COLOR,0.62)}"/></linearGradient></defs>
    <rect width="${size}" height="${size}" rx="${R}" fill="url(#g)"/>
    <g transform="translate(${off},${off}) scale(${scale})" fill="none" stroke="#ffffff"
       stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">${GLYPH}</g>
  </svg>`;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (const [name, size, rounded, frac] of JOBS){
    await sharp(Buffer.from(svg(size, rounded, frac))).png().toFile(path.join(OUT, name));
  }
  console.log(`wrote ${JOBS.length} icons to site/app-icons/`);
})();
