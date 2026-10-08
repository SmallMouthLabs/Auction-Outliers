// End-to-end smoke test against the running dev server (localhost:3000) and backend (127.0.0.1:8000).
// Usage: node scripts/e2e.mjs [screenshotDir]
import { chromium } from "playwright";

const outDir = process.argv[2] || "/tmp";
const exe = process.env.CHROME_PATH || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const browser = await chromium.launch({ executablePath: exe });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
const consoleErrors = [];
page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); });
page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));
page.on("dialog", (d) => d.accept());

const results = [];
async function step(name, fn) {
  try { const r = await fn(); results.push({ name, ok: true, info: r }); console.log("PASS", name, r ?? ""); }
  catch (e) { results.push({ name, ok: false, info: String(e.message || e).slice(0, 300) }); console.log("FAIL", name, e.message); }
}
const toastText = async () => (await page.locator('[role="status"]').allInnerTexts()).join(" | ");

await step("dashboard loads with rows", async () => {
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
  const rows = await page.locator("tbody tr").count();
  if (rows < 5) throw new Error(`only ${rows} rows`);
  return `${rows} rows`;
});

await step("dashboard: filter by tier via URL + search", async () => {
  await page.goto("http://localhost:3000/?tier=LOW_VALUE&q=jacket", { waitUntil: "networkidle" });
  const rows = await page.locator("tbody tr").count();
  const titles = await page.locator("tbody tr td:nth-child(2)").allInnerTexts();
  if (!titles.every((t) => /jacket/i.test(t))) throw new Error("search filter not applied: " + titles.join(";"));
  return `${rows} rows match`;
});

await step("dashboard: sort by ends_at toggles order", async () => {
  await page.goto("http://localhost:3000/?sort=ends_at&order=asc", { waitUntil: "networkidle" });
  const ends = await page.locator("tbody tr td:nth-child(9)").allInnerTexts();
  return ends.slice(0, 3).join(" < ");
});

await step("dashboard: watch quick action toggles", async () => {
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
  const btn = page.locator('tbody tr').nth(1).locator('button[aria-label="Watch"], button[aria-label="Unwatch"]');
  const before = await btn.getAttribute("aria-label");
  await btn.click();
  await page.waitForTimeout(800);
  const after = await btn.getAttribute("aria-label");
  if (before === after) throw new Error("watch state did not change");
  await btn.click(); // revert
  await page.waitForTimeout(500);
  return `${before} -> ${after} -> reverted`;
});

await step("row click navigates to item", async () => {
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
  await page.locator("tbody tr").first().click();
  await page.waitForURL(/\/items\/\d+/);
  await page.waitForSelector("h1");
  return page.url();
});

await step("item: run triage with demo provider", async () => {
  await page.goto("http://localhost:3000/items/1", { waitUntil: "networkidle" });
  await page.selectOption("select:has(option[value='demo'])", "demo");
  await page.getByRole("button", { name: "Triage" }).click();
  await page.waitForSelector("text=Pipeline result", { timeout: 20000 });
  const txt = await page.locator("text=Pipeline result").locator("..").innerText();
  return txt.replace(/\s+/g, " ").slice(0, 140);
});

await step("item: deep with anthropic shows 424 setup alert", async () => {
  await page.goto("http://localhost:3000/items/1", { waitUntil: "networkidle" });
  await page.selectOption("select:has(option[value='anthropic'])", "anthropic");
  await page.getByRole("button", { name: "Deep" }).click();
  await page.waitForSelector("text=AI provider not configured (424)", { timeout: 20000 });
  await page.screenshot({ path: `${outDir}/13-item-424-alert.png`, fullPage: false });
  return "424 alert rendered inline";
});

await step("item: feedback adds and deletes", async () => {
  await page.goto("http://localhost:3000/items/2", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Worth Investigating" }).click();
  await page.waitForTimeout(1000);
  const badge = page.locator("li:has-text('Worth Investigating')").first();
  if (!(await badge.count())) throw new Error("feedback row missing");
  await badge.locator('button[aria-label="Delete feedback"]').click();
  await page.waitForTimeout(800);
  return "added + removed";
});

await step("item: research note add + flag + resolve", async () => {
  await page.goto("http://localhost:3000/items/2#research", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /Research & outcome/ }).click();
  await page.fill("textarea[placeholder*='What to verify']", "E2E note: verify 925 stamp with acid test");
  await page.check("text=Flag for investigation >> input");
  await page.getByRole("button", { name: "Add note" }).click();
  await page.waitForTimeout(1500);
  const noteRows = await page.locator("li:has-text('E2E note')").count();
  if (!noteRows) throw new Error("note not added - backend bug: POST /notes returns 500 (TypeError on unflushed note id). Toast: " + (await toastText()).slice(0, 120));
  await page.locator('button[title="Mark resolved"]').first().click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${outDir}/14-item-research.png`, fullPage: true });
  return "note added, flagged, resolved";
});

await step("item: outcome saved shows realized profit", async () => {
  await page.goto("http://localhost:3000/items/2#research", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /Research & outcome/ }).click();
  await page.check("text=Purchased >> input");
  await page.fill("text=Purchase price (hammer) >> xpath=following::input[1]", "20");
  await page.check("text=Sold >> input");
  await page.fill("text=Resale price >> xpath=following::input[1]", "110");
  await page.fill("text=Selling fees >> xpath=following::input[1]", "15");
  await page.getByRole("button", { name: "Save outcome" }).click();
  await page.waitForSelector("text=realized", { timeout: 10000 });
  return await page.locator("text=realized").first().innerText();
});

await step("item: finance what-if recomputes on bid change", async () => {
  await page.goto("http://localhost:3000/items/3#finance", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: "Finance" }).click();
  await page.waitForSelector("text=Expected scenario", { timeout: 15000 });
  const stat = page.locator("div:has(> div:text-is('Expected profit')) > div.num").first();
  const before = (await page.locator("h3:has-text('Expected scenario')").innerText()) + " " + (await stat.innerText());
  const bid = page.locator("label:has-text('Your bid')").locator("..").locator("input");
  await bid.fill("30");
  await page.waitForTimeout(1500);
  const after = (await page.locator("h3:has-text('Expected scenario')").innerText()) + " " + (await stat.innerText());
  if (before === after) throw new Error("profit unchanged after bid change");
  await page.selectOption("select:has(option[value='etsy'])", "etsy");
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/15-item-finance-whatif.png`, fullPage: true });
  return `${before.replace(/\s+/g, " ")} => ${after.replace(/\s+/g, " ")}`;
});

await step("item: comps inline edit (similarity) recalculates valuation", async () => {
  await page.goto("http://localhost:3000/items/1#comps", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /Comparables/ }).click();
  const sim = page.locator('input[aria-label="Similarity"]').first();
  await sim.fill("0.95");
  await sim.blur();
  await page.waitForTimeout(1200);
  const t = await toastText();
  if (!/Comparable updated/.test(t)) throw new Error("no update toast: " + t);
  await sim.fill("0.9"); await sim.blur(); await page.waitForTimeout(800);
  return "ok";
});

await step("item: add comp + delete comp", async () => {
  await page.goto("http://localhost:3000/items/6#comps", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /Comparables/ }).click();
  await page.fill("input[placeholder='Sold listing title']", "E2E sold modernist cuff");
  await page.locator("label:has-text('Price')").locator("..").locator("input").first().fill("180");
  await page.getByRole("button", { name: "Add comp" }).click();
  await page.waitForSelector("text=E2E sold modernist cuff", { timeout: 10000 });
  const row = page.locator("tr:has-text('E2E sold modernist cuff')");
  await row.locator('button[aria-label="Delete comparable"]').click();
  await page.waitForTimeout(1000);
  if (await page.locator("text=E2E sold modernist cuff").count()) throw new Error("comp not deleted");
  return "added and deleted";
});

await step("item: valuation override + recalculate", async () => {
  await page.goto("http://localhost:3000/items/5#comps", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /Comparables/ }).click();
  await page.locator("label:has-text('Expected *')").locator("..").locator("input").fill("75");
  await page.getByRole("button", { name: "Apply override" }).click();
  await page.waitForTimeout(1200);
  const t1 = await toastText();
  await page.getByRole("button", { name: "Recalculate" }).click();
  await page.waitForTimeout(1200);
  return t1.slice(0, 80);
});

await step("item: correct identification + revert", async () => {
  await page.goto("http://localhost:3000/items/6", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Correct", exact: true }).click();
  await page.fill("input[placeholder*='Kingstone']", "E2E: Ed Levin modernist sterling cuff");
  await page.getByRole("button", { name: "Save correction" }).click();
  await page.waitForSelector("text=E2E: Ed Levin", { timeout: 10000 });
  await page.screenshot({ path: `${outDir}/16-item-user-correction.png`, fullPage: false });
  await page.getByRole("button", { name: /Revert to AI/ }).click();
  await page.waitForTimeout(1200);
  if (await page.locator("h2:has-text('E2E: Ed Levin')").count()) throw new Error("revert failed");
  return "corrected then reverted";
});

await step("item: snapshot form records price", async () => {
  await page.goto("http://localhost:3000/items/4#auction", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: "Auction data" }).click();
  await page.locator("label:has-text('Current bid')").locator("..").locator("input").fill("19");
  await page.getByRole("button", { name: "Record snapshot" }).click();
  await page.waitForTimeout(1200);
  const rows = await page.locator("text=Price / status history").locator("..").locator("..").locator("tbody tr").count();
  return `${rows} snapshots`;
});

await step("item: gallery lightbox + add image URL error surfaces", async () => {
  await page.goto("http://localhost:3000/items/1", { waitUntil: "networkidle" });
  await page.locator('button[aria-label="Photo 2"]').click();
  await page.locator('button[aria-label="View full size"]').click({ force: true });
  await page.waitForSelector('[role="dialog"]');
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Add image URLs" }).click();
  await page.fill("textarea[placeholder*='One image URL']", "not-a-url");
  await page.getByRole("button", { name: "Fetch & add" }).click();
  await page.waitForTimeout(500);
  const t = await toastText();
  if (!/No valid/.test(t)) throw new Error("expected validation toast, got: " + t);
  return "lightbox ok, validation ok";
});

await step("watchlist: status change + max bid save", async () => {
  await page.goto("http://localhost:3000/watchlist", { waitUntil: "networkidle" });
  const rows = await page.locator("tbody tr").count();
  if (!rows) throw new Error("no rows");
  const first = page.locator("tbody tr").first();
  await first.locator('input[aria-label="Your max bid"]').fill(String(50 + Math.floor(Math.random() * 40)));
  await first.locator('button[title="Save max bid / reminder"]').click();
  await page.waitForTimeout(1000);
  await first.locator('select[aria-label="Watch status"]').selectOption("bidding");
  await page.waitForTimeout(1000);
  await first.locator('input[aria-label="New current bid"]').fill("14");
  await first.getByRole("button", { name: "Update price" }).click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/06-watchlist.png`, fullPage: true });
  return `${rows} rows; saved max bid, status, price`;
});

await step("settings: change threshold, save only that section, discard", async () => {
  await page.goto("http://localhost:3000/settings", { waitUntil: "networkidle" });
  const inp = page.locator("label:has-text('Min profit $')").locator("..").locator("input");
  await inp.fill("30");
  await page.waitForSelector("text=Unsaved changes in: thresholds");
  await page.getByRole("button", { name: /Save \(1\)/ }).click();
  await page.waitForTimeout(1200);
  const t = await toastText();
  if (!/Settings saved/.test(t)) throw new Error("no save toast: " + t);
  await inp.fill("25");
  await page.getByRole("button", { name: /Save \(1\)/ }).click();
  await page.waitForTimeout(1000);
  return "saved thresholds twice";
});

await step("import: manual listing created, appears in result, photo upload control present", async () => {
  await page.goto("http://localhost:3000/import", { waitUntil: "networkidle" });
  await page.fill("input[placeholder='Auction title as listed']", "E2E Vintage Pendleton Wool Shirt L");
  await page.selectOption("select:has(option[value='clothing'])", "clothing");
  await page.locator("label:has-text('Current bid')").locator("..").locator("input").fill("8");
  await page.getByRole("button", { name: "Create listing" }).click();
  await page.waitForSelector("text=Parsed preview", { timeout: 10000 });
  const created = await page.locator("div.rounded:has-text('created')").first().innerText();
  await page.screenshot({ path: `${outDir}/17-import-result.png`, fullPage: true });
  return created.replace(/\s+/g, " ");
});

await step("import: CSV upload", async () => {
  await page.goto("http://localhost:3000/import", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /CSV/ }).click();
  const csv = "title,current_bid,domain,category\nE2E CSV Taxco sterling bracelet,12,jewelry,Jewelry > Bracelets\n,5,jewelry,bad row\n";
  await page.setInputFiles("input[type=file]", { name: "test.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
  await page.getByRole("button", { name: "Import", exact: true }).click();
  await page.waitForTimeout(1500);
  const t = await toastText();
  return t.slice(0, 120);
});

await step("import: e-mail with no links shows backend error list", async () => {
  await page.goto("http://localhost:3000/import", { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /Personal Shopper/ }).click();
  await page.fill("textarea[placeholder='<html>…']", "<html><body>nothing here</body></html>");
  await page.getByRole("button", { name: "Import from e-mail" }).click();
  await page.waitForTimeout(1500);
  const errs = await page.locator('[role="alert"]').allInnerTexts();
  return errs.join(" | ").slice(0, 160);
});

await step("reference: add + delete entry", async () => {
  await page.goto("http://localhost:3000/reference", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Add entry" }).click();
  await page.locator("label:has-text('Name *')").locator("..").locator("input").fill("E2E Test Maker");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await page.waitForSelector("tr:has-text('E2E Test Maker')", { timeout: 10000 });
  await page.locator("tr:has-text('E2E Test Maker')").locator('button[aria-label="Delete"]').click();
  await page.waitForTimeout(1000);
  if (await page.locator("tr:has-text('E2E Test Maker')").count()) throw new Error("not deleted");
  return "ok";
});

await step("jobs: process pending", async () => {
  await page.goto("http://localhost:3000/jobs", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Process pending now/ }).click();
  await page.waitForTimeout(1500);
  return (await toastText()).slice(0, 100);
});

await step("analytics renders KPIs", async () => {
  await page.goto("http://localhost:3000/analytics", { waitUntil: "networkidle" });
  await page.waitForSelector("text=AI usage & cost");
  return await page.locator("text=Realized profit").locator("..").innerText();
});

await step("light mode renders", async () => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${outDir}/18-dashboard-light.png`, fullPage: false });
  await page.emulateMedia({ colorScheme: "dark" });
  return "ok";
});

await step("no horizontal overflow at 1280 on every page", async () => {
  await page.setViewportSize({ width: 1280, height: 800 });
  const bad = [];
  for (const p of ["/", "/items/1", "/items/3#finance", "/watchlist", "/analytics", "/settings", "/import", "/reference", "/jobs"]) {
    await page.goto(`http://localhost:3000${p}`, { waitUntil: "networkidle" });
    if (p.includes("#finance")) await page.getByRole("tab", { name: "Finance" }).click();
    await page.waitForTimeout(500);
    const sw = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
    if (sw[0] > sw[1]) bad.push(`${p}: ${sw[0]}>${sw[1]}`);
  }
  if (bad.length) throw new Error(bad.join(", "));
  return "ok";
});

await browser.close();
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
console.log("console errors:", JSON.stringify([...new Set(consoleErrors)], null, 1));
process.exit(failed.length ? 1 : 0);
