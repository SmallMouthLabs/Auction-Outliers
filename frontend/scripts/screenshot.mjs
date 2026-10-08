// Usage: node scripts/screenshot.mjs <path> <outfile> [width] [height] [fullPage 1|0]
// Captures a page from the running dev server (localhost:3000), reports console errors
// and whether the page scrolls horizontally.
import { chromium } from "playwright";

const [, , path = "/", out = "shot.png", w = "1440", h = "900", full = "1"] = process.argv;
const exe = process.env.CHROME_PATH || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const browser = await chromium.launch({ executablePath: exe });
const page = await browser.newPage({ viewport: { width: Number(w), height: Number(h) }, colorScheme: process.env.LIGHT ? "light" : "dark" });
const errors = [];
page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") errors.push(`[${m.type()}] ${m.text()}`); });
page.on("pageerror", (e) => errors.push(`[pageerror] ${e.message}`));
await page.goto(`http://localhost:3000${path}`, { waitUntil: "networkidle" });
await page.waitForTimeout(800);
const sw = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }));
await page.screenshot({ path: out, fullPage: full === "1" });
console.log(JSON.stringify({ path, out, ...sw, horizontalOverflow: sw.scrollWidth > sw.clientWidth, errors }, null, 1));
await browser.close();
