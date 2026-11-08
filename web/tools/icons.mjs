// Generates the PNG icons from one SVG (needs sharp).
import sharp from "sharp";
import { mkdirSync } from "node:fs";

const svg = (pad) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" fill="#2f6f6a"/>
<g transform="translate(256 256) scale(${1 - pad}) translate(-256 -256)">
<rect x="96" y="118" width="250" height="300" rx="34" fill="#cfe3df" transform="rotate(-8 221 268)"/>
<rect x="150" y="96" width="250" height="300" rx="34" fill="#fbfaf6"/>
<text x="275" y="288" font-family="DejaVu Sans, Arial, sans-serif" font-weight="700" font-size="190" text-anchor="middle" fill="#2f6f6a">Ąę</text>
<rect x="205" y="322" width="140" height="14" rx="7" fill="#2f6f6a" opacity=".35"/>
</g></svg>`;

export async function makeIcons(outDir) {
  mkdirSync(outDir, { recursive: true });
  const png = (pad, size, name) => sharp(Buffer.from(svg(pad))).resize(size, size).png().toFile(`${outDir}/${name}`);
  await png(0, 192, "icon-192.png");
  await png(0, 512, "icon-512.png");
  await png(0.2, 512, "icon-maskable-512.png"); // keep the artwork inside the safe zone
  await png(0, 180, "apple-touch-icon.png");
}
