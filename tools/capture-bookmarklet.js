// OUTLIER capture bookmarklet (user-initiated; captures only the page you are currently viewing).
// 1. Start the backend (http://127.0.0.1:8000).
// 2. Create a bookmark whose URL is the minified one-liner at the bottom of this file.
// 3. On a ShopGoodwill item page, click the bookmark. The page HTML + URL is POSTed to /api/listings/import/page,
//    parsed deterministically (no model calls), and the listing opens in OUTLIER.
(async function () {
  const base = "http://127.0.0.1:8000";
  const html = document.documentElement.outerHTML;
  const fd = new FormData();
  fd.append("html", html);
  fd.append("url", location.href);
  try {
    const r = await fetch(base + "/api/listings/import/page?fetch_images=true&analyze=false", { method: "POST", body: fd });
    const j = await r.json();
    if (!r.ok) { alert("OUTLIER import failed: " + (j.detail || r.status)); return; }
    const id = j.ids && j.ids[0];
    alert("OUTLIER: imported '" + (j.parsed && j.parsed.title) + "' (listing " + id + ", " + (j.parsed.image_urls || []).length + " image urls). Opening...");
    window.open("http://localhost:3000/items/" + id, "_blank");
  } catch (e) { alert("OUTLIER import failed: " + e + "\nIs the backend running on " + base + "?"); }
})();

// Minified bookmark URL:
// javascript:(async()=>{const b="http://127.0.0.1:8000",f=new FormData();f.append("html",document.documentElement.outerHTML);f.append("url",location.href);try{const r=await fetch(b+"/api/listings/import/page?fetch_images=true&analyze=false",{method:"POST",body:f}),j=await r.json();if(!r.ok){alert("OUTLIER import failed: "+(j.detail||r.status));return}const i=j.ids&&j.ids[0];alert("OUTLIER: imported '"+(j.parsed&&j.parsed.title)+"' (listing "+i+")");window.open("http://localhost:3000/items/"+i,"_blank")}catch(e){alert("OUTLIER import failed: "+e)}})();
