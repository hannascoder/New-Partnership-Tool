// Small Cloudflare Worker for the "Get feedback" page (plan: docs/FEEDBACK_PLAN.md).
// It reads the owner's PRIVATE Google Sheet with a Google service account and hands the rows to the page.
// Everything else is served from site/ (static files). No secret is in this repository:
//   GOOGLE_SERVICE_ACCOUNT_JSON  (Cloudflare secret)  the key file of the service account
//   FEEDBACK_SHEET_ID            (Cloudflare secret or variable)  the id in the Sheet's address
//   FEEDBACK_SHEET_TAB           (optional) tab name, default "Contacts"
// The whole site sits behind Cloudflare Access; as a second safeguard /api/* answers only when Access has
// put its login header on the request.

const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const enc = new TextEncoder();
let tokenCache = { token: "", exp: 0 };

async function accessToken(sa) {
  const now = Math.floor(Date.now() / 1000);
  if (tokenCache.token && tokenCache.exp - 60 > now) return tokenCache.token;
  const head = b64url(enc.encode(JSON.stringify({ alg: "RS256", typ: "JWT" })));
  const claim = b64url(enc.encode(JSON.stringify({
    iss: sa.client_email, scope: "https://www.googleapis.com/auth/spreadsheets.readonly",
    aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600 })));
  const pem = sa.private_key.replace(/-----[A-Z ]+-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", der, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, enc.encode(head + "." + claim));
  const jwt = head + "." + claim + "." + b64url(sig);
  const r = await fetch("https://oauth2.googleapis.com/token", { method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=" + jwt });
  if (!r.ok) throw new Error("Google login failed (" + r.status + ")");
  const j = await r.json();
  tokenCache = { token: j.access_token, exp: now + (j.expires_in || 3600) };
  return tokenCache.token;
}

// rows (array of arrays) -> objects keyed by the header row
export function rowsToObjects(values) {
  if (!values || values.length < 2) return [];
  const head = values[0].map((h) => String(h).trim());
  return values.slice(1).filter((r) => r.some((c) => String(c).trim())).map((r) => {
    const o = {}; head.forEach((h, i) => { if (h) o[h] = String(r[i] ?? "").trim(); }); return o;
  });
}

const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });

async function contacts(env) {
  if (!env.GOOGLE_SERVICE_ACCOUNT_JSON || !env.FEEDBACK_SHEET_ID) return json({ error: "not_configured" }, 503);
  const sa = JSON.parse(env.GOOGLE_SERVICE_ACCOUNT_JSON);
  const tab = env.FEEDBACK_SHEET_TAB || "Contacts";
  const tok = await accessToken(sa);
  const url = "https://sheets.googleapis.com/v4/spreadsheets/" + encodeURIComponent(env.FEEDBACK_SHEET_ID) +
    "/values/" + encodeURIComponent(tab) + "?majorDimension=ROWS";
  const r = await fetch(url, { headers: { authorization: "Bearer " + tok } });
  if (!r.ok) return json({ error: "sheet_" + r.status }, 502);
  const j = await r.json();
  return json({ source: "sheet", contacts: rowsToObjects(j.values) });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/contacts") {
      const local = ["localhost", "127.0.0.1"].includes(url.hostname);
      if (!local && !request.headers.get("Cf-Access-Jwt-Assertion")) return json({ error: "login_required" }, 401);
      try { return await contacts(env); } catch (e) { return json({ error: "failed", detail: String(e.message || e) }, 500); }
    }
    return env.ASSETS.fetch(request);
  },
};
