const PLANS = new Set(["FREE", "MEDIUM", "FULL"]);
const SOURCES = new Set(["manual", "gift", "tester", "staff", "promo", "paid"]);
const encoder = new TextEncoder();

function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...extra,
    },
  });
}

function b64url(bytes) {
  let s = "";
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  for (let i = 0; i < arr.length; i += 0x8000) {
    s += String.fromCharCode(...arr.subarray(i, i + 0x8000));
  }
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function pemToDer(pem) {
  const base64 = String(pem || "")
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s+/g, "");
  if (!base64) throw new Error("LICENSE_PRIVATE_KEY_PEM mancante");
  const binary = atob(base64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out.buffer;
}

let importedPrivateKey = null;
async function privateKey(env) {
  if (importedPrivateKey) return importedPrivateKey;
  importedPrivateKey = await crypto.subtle.importKey(
    "pkcs8",
    pemToDer(env.LICENSE_PRIVATE_KEY_PEM),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  return importedPrivateKey;
}

async function signEntitlement(env, row) {
  const now = new Date().toISOString();
  const payload = {
    schema: 1,
    dossierId: String(row.dossier_id),
    plan: String(row.plan),
    licenseId: String(row.license_id),
    source: String(row.source || "manual"),
    issuedAt: now,
    validUntil: row.valid_until ? String(row.valid_until) : "",
    refreshAfter: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    notAfter: new Date(Math.min(
      row.valid_until && Number.isFinite(Date.parse(row.valid_until)) ? Date.parse(row.valid_until) : Number.POSITIVE_INFINITY,
      Date.now() + 14 * 24 * 60 * 60 * 1000
    )).toISOString(),
  };
  const raw = encoder.encode(JSON.stringify(payload));
  const signature = await crypto.subtle.sign(
    { name: "RSASSA-PKCS1-v1_5" },
    await privateKey(env),
    raw
  );
  return {
    payload: b64url(raw),
    signature: b64url(signature),
    keyId: "clinica-digitale-license-rsa-2026-01",
  };
}

function cleanDossierId(value) {
  const s = String(value || "").trim();
  if (!/^[A-Za-z0-9._:-]{8,160}$/.test(s)) return "";
  return s;
}

function cleanEmail(value) {
  const s = String(value || "").trim().toLowerCase();
  if (!s) return "";
  if (s.length > 254 || !s.includes("@")) return "";
  return s;
}

function adminAuthorized(request, env) {
  const expected = String(env.ADMIN_API_KEY || "");
  if (!expected) return false;
  const header = request.headers.get("authorization") || "";
  return header === `Bearer ${expected}`;
}

function corsHeaders(request, env) {
  const origin = request.headers.get("origin") || "";
  const allowed = new Set([
    String(env.PUBLIC_SITE_ORIGIN || "https://dossiersanitario.it"),
    "https://www.dossiersanitario.it",
    "http://127.0.0.1:8896",
    "http://localhost:8896",
  ]);
  return allowed.has(origin)
    ? {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": "GET,POST,OPTIONS",
        "access-control-allow-headers": "content-type,authorization",
        "access-control-max-age": "86400",
        vary: "Origin",
      }
    : {};
}

function expired(validUntil) {
  if (!validUntil) return false;
  const t = Date.parse(validUntil);
  return Number.isFinite(t) && t <= Date.now();
}

async function resolveLicense(request, env) {
  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  if (!dossierId) return json({ ok: false, error: "dossier_id_invalid" }, 400);

  const row = await env.DB.prepare(
    "SELECT dossier_id, license_id, account_email, plan, status, source, note, valid_until, created_at, updated_at FROM entitlements WHERE dossier_id = ?1"
  ).bind(dossierId).first();

  if (!row || row.status !== "active" || expired(row.valid_until)) {
    return json({ ok: true, plan: "FREE", entitlement: null });
  }
  const token = await signEntitlement(env, row);
  return json({
    ok: true,
    plan: row.plan,
    entitlement: {
      dossierId: row.dossier_id,
      licenseId: row.license_id,
      plan: row.plan,
      source: row.source,
      validUntil: row.valid_until || "",
      updatedAt: row.updated_at,
    },
    token,
  });
}

async function grantEntitlement(request, env) {
  if (!adminAuthorized(request, env)) return json({ ok: false, error: "unauthorized" }, 401);
  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  const plan = String(body.plan || "").trim().toUpperCase();
  const email = cleanEmail(body.accountEmail);
  const source = SOURCES.has(String(body.source || "")) ? String(body.source) : "manual";
  const note = String(body.note || "").trim().slice(0, 500);
  const validUntil = body.validUntil ? String(body.validUntil).trim() : null;
  if (!dossierId || !PLANS.has(plan)) return json({ ok: false, error: "invalid_input" }, 400);
  if (validUntil && !Number.isFinite(Date.parse(validUntil))) return json({ ok: false, error: "valid_until_invalid" }, 400);

  const now = new Date().toISOString();
  const current = await env.DB.prepare("SELECT license_id, created_at FROM entitlements WHERE dossier_id = ?1").bind(dossierId).first();
  const licenseId = current?.license_id || crypto.randomUUID();
  const createdAt = current?.created_at || now;

  await env.DB.prepare(`
    INSERT INTO entitlements(dossier_id, license_id, account_email, plan, status, source, note, valid_until, created_at, updated_at)
    VALUES(?1, ?2, ?3, ?4, 'active', ?5, ?6, ?7, ?8, ?9)
    ON CONFLICT(dossier_id) DO UPDATE SET
      account_email=excluded.account_email,
      plan=excluded.plan,
      status='active',
      source=excluded.source,
      note=excluded.note,
      valid_until=excluded.valid_until,
      updated_at=excluded.updated_at
  `).bind(dossierId, licenseId, email || null, plan, source, note, validUntil, createdAt, now).run();

  await env.DB.prepare(
    "INSERT INTO entitlement_audit(dossier_id, action, plan, source, note, created_at) VALUES(?1,'grant',?2,?3,?4,?5)"
  ).bind(dossierId, plan, source, note, now).run();

  const row = await env.DB.prepare("SELECT * FROM entitlements WHERE dossier_id = ?1").bind(dossierId).first();
  return json({ ok: true, entitlement: row, token: await signEntitlement(env, row) });
}

async function revokeEntitlement(request, env) {
  if (!adminAuthorized(request, env)) return json({ ok: false, error: "unauthorized" }, 401);
  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  const note = String(body.note || "").trim().slice(0, 500);
  if (!dossierId) return json({ ok: false, error: "dossier_id_invalid" }, 400);
  const now = new Date().toISOString();
  await env.DB.prepare("UPDATE entitlements SET status='revoked', note=?2, updated_at=?3 WHERE dossier_id=?1")
    .bind(dossierId, note, now).run();
  await env.DB.prepare(
    "INSERT INTO entitlement_audit(dossier_id, action, plan, source, note, created_at) VALUES(?1,'revoke',NULL,'manual',?2,?3)"
  ).bind(dossierId, note, now).run();
  return json({ ok: true });
}

async function listEntitlements(request, env) {
  if (!adminAuthorized(request, env)) return json({ ok: false, error: "unauthorized" }, 401);
  const url = new URL(request.url);
  const q = String(url.searchParams.get("q") || "").trim().toLowerCase();
  const rows = q
    ? await env.DB.prepare(`
        SELECT dossier_id, license_id, account_email, plan, status, source, note, valid_until, created_at, updated_at
        FROM entitlements
        WHERE lower(dossier_id) LIKE ?1 OR lower(coalesce(account_email,'')) LIKE ?1 OR lower(coalesce(note,'')) LIKE ?1
        ORDER BY updated_at DESC LIMIT 100
      `).bind(`%${q}%`).all()
    : await env.DB.prepare(`
        SELECT dossier_id, license_id, account_email, plan, status, source, note, valid_until, created_at, updated_at
        FROM entitlements ORDER BY updated_at DESC LIMIT 100
      `).all();
  return json({ ok: true, entitlements: rows.results || [] });
}

function planPricing(env) {
  const promoEnd = String(env.PROMO_END || "2027-02-15T00:00:00+01:00");
  const promoActive = Date.now() < Date.parse(promoEnd);
  return {
    ok: true,
    promoEnd,
    promoActive,
    plans: {
      FREE: { current: 0, standard: 0, currency: "EUR" },
      MEDIUM: { current: promoActive ? 1.99 : 4.99, launch: 1.99, standard: 4.99, currency: "EUR" },
      FULL: { current: promoActive ? 2.99 : 9.99, launch: 2.99, standard: 9.99, currency: "EUR" },
    },
  };
}

function adminHtml() {
  return `<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clinica Digitale - Gestore licenze</title><style>
  body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f4f7f6;color:#17342e;margin:0}.wrap{max-width:960px;margin:40px auto;padding:0 20px}.card{background:#fff;border:1px solid #d9e7e2;border-radius:18px;padding:22px;margin:16px 0}label{display:grid;gap:6px;font-weight:700;margin:12px 0}input,select,textarea,button{font:inherit;padding:11px 12px;border-radius:10px;border:1px solid #bfd3cc}button{cursor:pointer;font-weight:800;background:#2f796d;color:#fff;border:0}.danger{background:#b42318}.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}.search-block{display:grid;gap:6px}.search-block>label{margin:0}.search-controls{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:stretch}.search-controls input,.search-controls button{height:44px;box-sizing:border-box;margin:0}.search-controls button{display:flex;align-items:center;justify-content:center;white-space:nowrap}.status{display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:12px;font-weight:800;margin:14px 0}.status.hidden{display:none}.status.ok{background:#e7f6ec;color:#166534;border:1px solid #a7dfb7}.status.err{background:#fdeaea;color:#991b1b;border:1px solid #efb0b0}.lamp{width:14px;height:14px;border-radius:50%;flex:0 0 14px;background:#9ca3af}.status.ok .lamp{background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.14)}.status.err .lamp{background:#ef4444;box-shadow:0 0 0 4px rgba(239,68,68,.14)}details{margin-top:12px}.out{white-space:pre-wrap;background:#10231f;color:#dff3ed;padding:16px;border-radius:12px;min-height:80px;max-height:360px;overflow:auto;font-size:13px}@media(max-width:700px){.row{grid-template-columns:1fr}.search-controls{grid-template-columns:1fr}.search-controls button{width:100%}}
  </style><div class="wrap"><h1>Gestore licenze Clinica Digitale</h1><p>Il token amministratore non viene salvato dal browser.</p><div class="card"><label>Token amministratore<input id="key" type="password" autocomplete="off"></label><div class="row"><label>ID Dossier<input id="dossier"></label><label>E-mail account<input id="email" type="email"></label></div><div class="row"><label>Piano<select id="plan"><option>FREE</option><option>MEDIUM</option><option>FULL</option></select></label><label>Origine<select id="source"><option value="manual">Manuale</option><option value="gift">Omaggio</option><option value="tester">Tester</option><option value="staff">Staff</option><option value="promo">Promozione</option><option value="paid">Pagamento</option></select></label></div><label>Validità fino a (opzionale)<input id="until" type="datetime-local"></label><label>Nota<textarea id="note" rows="3"></textarea></label><p><button id="grant">Assegna / aggiorna</button> <button id="revoke" class="danger">Revoca</button></p></div><div class="card"><div class="search-block"><label for="q">Cerca</label><div class="search-controls"><input id="q"><button id="search">Cerca licenze</button></div></div><div id="status" class="status hidden"><span class="lamp"></span><span id="statusText"></span></div><details id="technical"><summary>Dettagli tecnici</summary><div id="out" class="out"></div></details></div></div><script>
  const $=id=>document.getElementById(id);
  const headers=()=>({'content-type':'application/json','authorization':'Bearer '+$('key').value});
  function render(result, action){
    $('out').textContent=JSON.stringify(result,null,2);
    const st=$('status');
    st.classList.remove('hidden','ok','err');
    if(result && result.ok){
      st.classList.add('ok');
      let msg='Operazione completata correttamente.';
      if(action==='grant'){
        const e=result.entitlement||{};
        msg='LICENZA ATTIVA: '+(e.plan||'')+' assegnata a '+(e.dossier_id||'Dossier')+'.';
      } else if(action==='revoke'){
        msg='LICENZA REVOCATA correttamente.';
      } else if(action==='search'){
        const n=Array.isArray(result.entitlements)?result.entitlements.length:0;
        msg=n===1?'1 licenza trovata.':n+' licenze trovate.';
      }
      $('statusText').textContent=msg;
      $('technical').open=false;
    }else{
      st.classList.add('err');
      $('statusText').textContent='ERRORE: '+((result&&result.error)||'operazione non riuscita')+'.';
      $('technical').open=true;
    }
  }
  async function call(url,options,action){
    try{
      const res=await fetch(url,options);
      let data;
      try{data=await res.json()}catch{data={ok:false,error:'risposta_non_valida'}}
      if(!res.ok && data.ok!==false) data.ok=false;
      render(data,action);
    }catch(e){
      render({ok:false,error:'connessione_non_disponibile',detail:String(e)},action);
    }
  }
  $('grant').onclick=async()=>{
    const valid=$('until').value?new Date($('until').value).toISOString():'';
    await call('/v1/admin/entitlements',{method:'POST',headers:headers(),body:JSON.stringify({dossierId:$('dossier').value,accountEmail:$('email').value,plan:$('plan').value,source:$('source').value,note:$('note').value,validUntil:valid})},'grant');
  };
  $('revoke').onclick=async()=>await call('/v1/admin/revoke',{method:'POST',headers:headers(),body:JSON.stringify({dossierId:$('dossier').value,note:$('note').value})},'revoke');
  $('search').onclick=async()=>await call('/v1/admin/entitlements?q='+encodeURIComponent($('q').value),{headers:headers()},'search');
  </script></html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    let response;
    try {
      if (request.method === "GET" && url.pathname === "/health") response = json({ ok: true, service: "clinica-digitale-licenze" });
      else if (request.method === "GET" && url.pathname === "/v1/public/plans") response = json(planPricing(env));
      else if (request.method === "GET" && url.pathname === "/admin") response = new Response(adminHtml(), { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
      else if (request.method === "POST" && url.pathname === "/v1/license/resolve") response = await resolveLicense(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/admin/entitlements") response = await grantEntitlement(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/admin/revoke") response = await revokeEntitlement(request, env);
      else if (request.method === "GET" && url.pathname === "/v1/admin/entitlements") response = await listEntitlements(request, env);
      else response = json({ ok: false, error: "not_found" }, 404);
    } catch (error) {
      response = json({ ok: false, error: "internal_error", detail: String(error?.message || error) }, 500);
    }
    const headers = corsHeaders(request, env);
    for (const [k, v] of Object.entries(headers)) response.headers.set(k, v);
    return response;
  },
};
