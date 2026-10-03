const PLANS = new Set(["FREE", "MEDIUM", "FULL"]);
const PLAN_RANK = { FREE: 0, MEDIUM: 1, FULL: 2 };
const SOURCES = new Set(["manual", "gift", "tester", "staff", "promo", "paid"]);
const PAYPAL_SECURITY_EVENTS = new Set([
  "PAYMENT.CAPTURE.COMPLETED",
  "PAYMENT.CAPTURE.DENIED",
  "PAYMENT.CAPTURE.PENDING",
  "PAYMENT.CAPTURE.REFUNDED",
  "PAYMENT.CAPTURE.REVERSED",
  "CHECKOUT.PAYMENT-APPROVAL.REVERSED",
  "CUSTOMER.DISPUTE.CREATED",
  "CUSTOMER.DISPUTE.UPDATED",
  "CUSTOMER.DISPUTE.RESOLVED",
]);
const encoder = new TextEncoder();

function securityHeaders() {
  return {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "cross-origin-resource-policy": "same-origin",
  };
}

function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...securityHeaders(),
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
  const paid = String(row.source || "") === "paid";
  const refreshMs = paid ? 6 * 60 * 60 * 1000 : 24 * 60 * 60 * 1000;
  const offlineMs = paid ? 24 * 60 * 60 * 1000 : 14 * 24 * 60 * 60 * 1000;
  const payload = {
    schema: 1,
    dossierId: String(row.dossier_id),
    plan: String(row.plan),
    licenseId: String(row.license_id),
    source: String(row.source || "manual"),
    issuedAt: now,
    validUntil: row.valid_until ? String(row.valid_until) : "",
    refreshAfter: new Date(Date.now() + refreshMs).toISOString(),
    notAfter: new Date(Math.min(
      row.valid_until && Number.isFinite(Date.parse(row.valid_until)) ? Date.parse(row.valid_until) : Number.POSITIVE_INFINITY,
      Date.now() + offlineMs
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

function cleanInstallationId(value) {
  const s = String(value || "").trim();
  if (!/^[A-Za-z0-9._:-]{8,160}$/.test(s)) return "";
  return s;
}

function cleanVersion(value) {
  return String(value || "").trim().slice(0, 40);
}

function cleanPlatform(value) {
  return String(value || "").trim().slice(0, 40);
}

async function ensureUsageSchema(env) {
  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS usage_installations (
      dossier_id TEXT NOT NULL,
      installation_id TEXT NOT NULL,
      plan TEXT NOT NULL DEFAULT 'FREE' CHECK (plan IN ('FREE','MEDIUM','FULL')),
      first_seen TEXT NOT NULL,
      last_seen TEXT NOT NULL,
      launch_count INTEGER NOT NULL DEFAULT 1,
      app_version TEXT NOT NULL DEFAULT '',
      platform TEXT NOT NULL DEFAULT '',
      PRIMARY KEY (dossier_id, installation_id)
    )
  `).run();
  await env.DB.prepare(
    "CREATE INDEX IF NOT EXISTS idx_usage_last_seen ON usage_installations(last_seen)"
  ).run();
}

async function effectivePlanForDossier(env, dossierId) {
  const row = await env.DB.prepare(
    "SELECT plan, status, valid_until FROM entitlements WHERE dossier_id = ?1"
  ).bind(dossierId).first();
  if (!row || row.status !== "active" || expired(row.valid_until)) return "FREE";
  const plan = String(row.plan || "FREE").toUpperCase();
  return PLANS.has(plan) ? plan : "FREE";
}

async function usagePing(request, env) {
  await ensureUsageSchema(env);
  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  const installationId = cleanInstallationId(body.installationId);
  const appVersion = cleanVersion(body.appVersion);
  const platform = cleanPlatform(body.platform);
  if (!dossierId || !installationId) return json({ ok: false, error: "usage_id_invalid" }, 400);

  const now = new Date().toISOString();
  const plan = await effectivePlanForDossier(env, dossierId);
  await env.DB.prepare(`
    INSERT INTO usage_installations(
      dossier_id, installation_id, plan, first_seen, last_seen, launch_count, app_version, platform
    )
    VALUES(?1, ?2, ?3, ?4, ?4, 1, ?5, ?6)
    ON CONFLICT(dossier_id, installation_id) DO UPDATE SET
      plan=excluded.plan,
      last_seen=excluded.last_seen,
      launch_count=usage_installations.launch_count + 1,
      app_version=excluded.app_version,
      platform=excluded.platform
  `).bind(dossierId, installationId, plan, now, appVersion, platform).run();
  return json({ ok: true });
}

async function listUsage(request, env) {
  if (!adminAuthorized(request, env)) return json({ ok: false, error: "unauthorized" }, 401);
  await ensureUsageSchema(env);
  const url = new URL(request.url);
  const q = String(url.searchParams.get("q") || "").trim().toLowerCase();
  const where = q ? "WHERE lower(u.dossier_id) LIKE ?1" : "";
  const sql = `
    SELECT
      u.dossier_id,
      MIN(u.first_seen) AS first_seen,
      MAX(u.last_seen) AS last_seen,
      SUM(u.launch_count) AS launch_count,
      COUNT(*) AS installations,
      CASE MAX(CASE u.plan WHEN 'FULL' THEN 2 WHEN 'MEDIUM' THEN 1 ELSE 0 END)
        WHEN 2 THEN 'FULL' WHEN 1 THEN 'MEDIUM' ELSE 'FREE' END AS plan,
      MAX(u.app_version) AS app_version,
      MAX(u.platform) AS platform
    FROM usage_installations u
    ${where}
    GROUP BY u.dossier_id
    ORDER BY last_seen DESC
    LIMIT 500
  `;
  const result = q
    ? await env.DB.prepare(sql).bind(`%${q}%`).all()
    : await env.DB.prepare(sql).all();

  const now = Date.now();
  const usage = (result.results || []).map(row => {
    const lastMs = Date.parse(row.last_seen || "");
    const daysInactive = Number.isFinite(lastMs) ? Math.max(0, Math.floor((now - lastMs) / 86400000)) : null;
    const launches = Number(row.launch_count || 0);
    let activity = "inactive";
    if (launches <= 1) activity = "single_launch";
    else if (daysInactive !== null && daysInactive <= 7) activity = "active";
    return { ...row, launch_count: launches, installations: Number(row.installations || 0), daysInactive, activity };
  });
  return json({
    ok: true,
    summary: {
      dossiers: usage.length,
      active7d: usage.filter(x => x.activity === "active").length,
      singleLaunch: usage.filter(x => x.activity === "single_launch").length,
      inactiveOver7d: usage.filter(x => x.activity === "inactive").length,
    },
    usage,
  });
}


function paymentModel(env) {
  return String(env.PAYMENT_MODEL || "disabled").trim().toLowerCase();
}

function paypalBaseUrl(env) {
  return String(env.PAYPAL_ENVIRONMENT || "sandbox").toLowerCase() === "live"
    ? "https://api-m.paypal.com"
    : "https://api-m.sandbox.paypal.com";
}

function paypalReady(env) {
  return paymentModel(env) === "one_time"
    && String(env.PAYPAL_CLIENT_ID || "")
    && String(env.PAYPAL_CLIENT_SECRET || "");
}

function cleanPaymentId(value) {
  const s = String(value || "").trim();
  return /^[A-Za-z0-9._:-]{16,160}$/.test(s) ? s : "";
}

async function ensurePaymentSchema(env) {
  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS payments (
      id TEXT PRIMARY KEY,
      provider TEXT NOT NULL DEFAULT 'paypal',
      provider_order_id TEXT UNIQUE,
      provider_capture_id TEXT UNIQUE,
      dossier_id TEXT NOT NULL,
      installation_id TEXT NOT NULL DEFAULT '',
      target_plan TEXT NOT NULL,
      previous_plan TEXT NOT NULL DEFAULT 'FREE',
      previous_status TEXT NOT NULL DEFAULT '',
      previous_source TEXT NOT NULL DEFAULT '',
      previous_source_ref TEXT NOT NULL DEFAULT '',
      previous_valid_until TEXT,
      amount_cents INTEGER NOT NULL,
      currency TEXT NOT NULL DEFAULT 'EUR',
      status TEXT NOT NULL DEFAULT 'created',
      seller_protection TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  `).run();
  await env.DB.prepare("CREATE INDEX IF NOT EXISTS idx_payments_dossier ON payments(dossier_id, created_at)").run();
  await env.DB.prepare("CREATE INDEX IF NOT EXISTS idx_payments_capture ON payments(provider_capture_id)").run();
  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS payment_events (
      event_id TEXT PRIMARY KEY,
      event_type TEXT NOT NULL,
      transmission_id TEXT NOT NULL DEFAULT '',
      resource_id TEXT NOT NULL DEFAULT '',
      result TEXT NOT NULL DEFAULT 'processing',
      received_at TEXT NOT NULL,
      processed_at TEXT
    )
  `).run();
  const info = await env.DB.prepare("PRAGMA table_info(entitlements)").all();
  if (!(info.results || []).some(row => String(row.name) === "source_ref")) {
    try { await env.DB.prepare("ALTER TABLE entitlements ADD COLUMN source_ref TEXT").run(); }
    catch (error) {
      if (!/duplicate column/i.test(String(error?.message || error))) throw error;
    }
  }
}

let paypalTokenCache = { key: "", token: "", until: 0 };
async function paypalAccessToken(env) {
  const clientId = String(env.PAYPAL_CLIENT_ID || "");
  const clientSecret = String(env.PAYPAL_CLIENT_SECRET || "");
  if (!clientId || !clientSecret) throw new Error("paypal_not_configured");
  const key = String(env.PAYPAL_ENVIRONMENT || "sandbox") + ":" + clientId;
  if (paypalTokenCache.key === key && paypalTokenCache.token && paypalTokenCache.until > Date.now() + 60000) {
    return paypalTokenCache.token;
  }
  const response = await fetch(paypalBaseUrl(env) + "/v1/oauth2/token", {
    method: "POST",
    headers: {
      "authorization": "Basic " + btoa(clientId + ":" + clientSecret),
      "content-type": "application/x-www-form-urlencoded",
      "accept": "application/json",
    },
    body: "grant_type=client_credentials",
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) throw new Error("paypal_oauth_failed");
  const expires = Math.max(60, Number(data.expires_in || 300) - 120);
  paypalTokenCache = { key, token: String(data.access_token), until: Date.now() + expires * 1000 };
  return paypalTokenCache.token;
}

async function paypalApi(env, path, { method = "GET", body = null, requestId = "" } = {}) {
  const token = await paypalAccessToken(env);
  const headers = {
    "authorization": "Bearer " + token,
    "accept": "application/json",
  };
  if (body !== null) headers["content-type"] = "application/json";
  if (requestId) headers["paypal-request-id"] = requestId;
  const response = await fetch(paypalBaseUrl(env) + path, {
    method,
    headers,
    body: body === null ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error("paypal_api_failed");
    error.paypalStatus = response.status;
    throw error;
  }
  return data;
}

function amountCents(value) {
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n * 100) : -1;
}

async function paymentIdentityAllowed(env, dossierId, installationId) {
  await ensureUsageSchema(env);
  const row = await env.DB.prepare(
    "SELECT 1 AS ok FROM usage_installations WHERE dossier_id=?1 AND installation_id=?2 LIMIT 1"
  ).bind(dossierId, installationId).first();
  return !!row;
}

async function paymentThrottleAllowed(env, dossierId) {
  const cutoff = new Date(Date.now() - 15 * 60 * 1000).toISOString();
  const row = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM payments WHERE dossier_id=?1 AND created_at>=?2"
  ).bind(dossierId, cutoff).first();
  return Number(row?.n || 0) < 5;
}

async function createPayPalOrder(request, env) {
  await ensurePaymentSchema(env);
  if (!paypalReady(env)) return json({ ok: false, error: "payments_not_enabled" }, 503);
  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  const installationId = cleanInstallationId(body.installationId);
  const targetPlan = String(body.plan || "").toUpperCase();
  if (!dossierId || !installationId || !["MEDIUM", "FULL"].includes(targetPlan)) {
    return json({ ok: false, error: "invalid_input" }, 400);
  }
  if (!await paymentIdentityAllowed(env, dossierId, installationId)) {
    return json({ ok: false, error: "installation_not_recognized" }, 403);
  }
  if (!await paymentThrottleAllowed(env, dossierId)) {
    return json({ ok: false, error: "too_many_payment_attempts" }, 429);
  }

  const current = await env.DB.prepare(
    "SELECT dossier_id, license_id, plan, status, source, source_ref, valid_until, created_at FROM entitlements WHERE dossier_id=?1"
  ).bind(dossierId).first();
  const currentPlan = !current || current.status !== "active" || expired(current.valid_until)
    ? "FREE"
    : (PLANS.has(String(current.plan || "").toUpperCase()) ? String(current.plan).toUpperCase() : "FREE");
  if (PLAN_RANK[currentPlan] >= PLAN_RANK[targetPlan]) {
    return json({ ok: false, error: "plan_already_active" }, 409);
  }
  if (currentPlan === "MEDIUM" && targetPlan === "FULL") {
    return json({ ok: false, error: "medium_to_full_price_not_defined" }, 409);
  }

  const pricing = planPricing(env);
  const cents = amountCents(pricing.plans[targetPlan]?.current);
  if (cents <= 0) return json({ ok: false, error: "price_not_available" }, 503);

  const paymentId = crypto.randomUUID();
  const now = new Date().toISOString();
  await env.DB.prepare(`
    INSERT INTO payments(
      id, provider, dossier_id, installation_id, target_plan,
      previous_plan, previous_status, previous_source, previous_source_ref, previous_valid_until,
      amount_cents, currency, status, created_at, updated_at
    ) VALUES(?1,'paypal',?2,?3,?4,?5,?6,?7,?8,?9,?10,'EUR','creating',?11,?11)
  `).bind(
    paymentId, dossierId, installationId, targetPlan,
    currentPlan, String(current?.status || ""), String(current?.source || ""),
    String(current?.source_ref || ""), current?.valid_until || null,
    cents, now
  ).run();

  const order = await paypalApi(env, "/v2/checkout/orders", {
    method: "POST",
    requestId: paymentId,
    body: {
      intent: "CAPTURE",
      purchase_units: [{
        reference_id: paymentId,
        custom_id: paymentId,
        invoice_id: "CD-" + paymentId,
        description: "Clinica Digitale - piano " + targetPlan,
        amount: { currency_code: "EUR", value: (cents / 100).toFixed(2) },
      }],
      payment_source: { paypal: { experience_context: { shipping_preference: "NO_SHIPPING", user_action: "PAY_NOW" } } },
    },
  });

  const orderId = String(order.id || "");
  if (!orderId) throw new Error("paypal_order_missing");
  await env.DB.prepare(
    "UPDATE payments SET provider_order_id=?2,status='created',updated_at=?3 WHERE id=?1"
  ).bind(paymentId, orderId, new Date().toISOString()).run();
  const approveUrl = (order.links || []).find(link => link.rel === "payer-action" || link.rel === "approve")?.href || "";
  return json({ ok: true, paymentId, orderId, approveUrl, plan: targetPlan, amount: (cents / 100).toFixed(2), currency: "EUR" });
}

async function confirmPayPalCapture(env, captureId) {
  const id = String(captureId || "");
  if (!id) throw new Error("capture_id_missing");
  return paypalApi(env, "/v2/payments/captures/" + encodeURIComponent(id));
}

async function activatePaidEntitlement(env, payment, capture) {
  const captureId = String(capture?.id || "");
  const captureStatus = String(capture?.status || "");
  const customId = String(capture?.custom_id || "");
  const cents = amountCents(capture?.amount?.value);
  const currency = String(capture?.amount?.currency_code || "");
  if (captureStatus !== "COMPLETED") throw new Error("capture_not_completed");
  if (customId && customId !== payment.id) throw new Error("capture_payment_mismatch");
  if (cents !== Number(payment.amount_cents) || currency !== String(payment.currency)) throw new Error("capture_amount_mismatch");

  const now = new Date().toISOString();
  const current = await env.DB.prepare("SELECT * FROM entitlements WHERE dossier_id=?1").bind(payment.dossier_id).first();
  const currentPlan = (!current || current.status !== "active" || expired(current.valid_until))
    ? "FREE"
    : String(current.plan || "FREE").toUpperCase();

  await env.DB.prepare(
    "UPDATE payments SET provider_capture_id=?2,status='completed',seller_protection=?3,updated_at=?4 WHERE id=?1"
  ).bind(payment.id, captureId, String(capture?.seller_protection?.status || ""), now).run();

  if (PLAN_RANK[currentPlan] > PLAN_RANK[payment.target_plan] && String(current?.source_ref || "") !== payment.id) {
    await env.DB.prepare(
      "INSERT INTO entitlement_audit(dossier_id,action,plan,source,note,created_at) VALUES(?1,'payment_completed_no_downgrade',?2,'paid',?3,?4)"
    ).bind(payment.dossier_id, payment.target_plan, "Pagamento " + payment.id + " acquisito senza abbassare un piano superiore già attivo.", now).run();
    return;
  }

  const licenseId = current?.license_id || crypto.randomUUID();
  const createdAt = current?.created_at || now;
  await env.DB.prepare(`
    INSERT INTO entitlements(dossier_id,license_id,account_email,plan,status,source,note,valid_until,created_at,updated_at,source_ref)
    VALUES(?1,?2,NULL,?3,'active','paid',?4,NULL,?5,?6,?7)
    ON CONFLICT(dossier_id) DO UPDATE SET
      plan=excluded.plan,status='active',source='paid',source_ref=excluded.source_ref,
      note=excluded.note,valid_until=NULL,updated_at=excluded.updated_at
  `).bind(payment.dossier_id, licenseId, payment.target_plan, "Pagamento PayPal confermato", createdAt, now, payment.id).run();
  await env.DB.prepare(
    "INSERT INTO entitlement_audit(dossier_id,action,plan,source,note,created_at) VALUES(?1,'payment_grant',?2,'paid',?3,?4)"
  ).bind(payment.dossier_id, payment.target_plan, "Payment " + payment.id + " / capture " + captureId, now).run();
}

async function capturePayPalOrder(request, env) {
  await ensurePaymentSchema(env);
  if (!paypalReady(env)) return json({ ok: false, error: "payments_not_enabled" }, 503);
  let body = {};
  try { body = await request.json(); } catch {}
  const paymentId = cleanPaymentId(body.paymentId);
  const installationId = cleanInstallationId(body.installationId);
  if (!paymentId || !installationId) return json({ ok: false, error: "invalid_input" }, 400);
  const payment = await env.DB.prepare("SELECT * FROM payments WHERE id=?1").bind(paymentId).first();
  if (!payment || payment.installation_id !== installationId) return json({ ok: false, error: "payment_not_found" }, 404);
  if (["refunded","reversed","disputed"].includes(String(payment.status))) return json({ ok: false, error: "payment_not_capturable" }, 409);
  if (payment.status === "completed" && payment.provider_capture_id) {
    return json({ ok: true, status: "COMPLETED", paymentId, captureId: payment.provider_capture_id });
  }
  const orderId = String(payment.provider_order_id || "");
  if (!orderId) return json({ ok: false, error: "paypal_order_missing" }, 409);

  const captured = await paypalApi(env, "/v2/checkout/orders/" + encodeURIComponent(orderId) + "/capture", {
    method: "POST",
    requestId: paymentId + "-capture",
    body: {},
  });
  const capture = captured?.purchase_units?.flatMap(unit => unit?.payments?.captures || [])[0];
  if (!capture?.id) return json({ ok: false, error: "paypal_capture_missing" }, 502);
  const verified = await confirmPayPalCapture(env, capture.id);
  await activatePaidEntitlement(env, payment, verified);
  return json({ ok: true, status: "COMPLETED", paymentId, captureId: String(verified.id || "") });
}

async function restorePreviousEntitlement(env, payment, status, reason) {
  const now = new Date().toISOString();
  await env.DB.prepare("UPDATE payments SET status=?2,updated_at=?3 WHERE id=?1")
    .bind(payment.id, status, now).run();
  const current = await env.DB.prepare("SELECT * FROM entitlements WHERE dossier_id=?1").bind(payment.dossier_id).first();
  if (!current || String(current.source || "") !== "paid" || String(current.source_ref || "") !== payment.id) {
    await env.DB.prepare(
      "INSERT INTO entitlement_audit(dossier_id,action,plan,source,note,created_at) VALUES(?1,?2,?3,'paid',?4,?5)"
    ).bind(payment.dossier_id, "payment_" + status + "_no_current_change", payment.target_plan, reason, now).run();
    return;
  }

  const previousPlan = String(payment.previous_plan || "FREE").toUpperCase();
  const previousStillValid = !payment.previous_valid_until || !expired(payment.previous_valid_until);
  if (PLAN_RANK[previousPlan] > 0 && String(payment.previous_status || "") === "active" && previousStillValid) {
    await env.DB.prepare(`
      UPDATE entitlements
      SET plan=?2,status='active',source=?3,source_ref=?4,valid_until=?5,note=?6,updated_at=?7
      WHERE dossier_id=?1
    `).bind(
      payment.dossier_id, previousPlan, payment.previous_source || "manual",
      payment.previous_source_ref || null, payment.previous_valid_until || null,
      reason, now
    ).run();
  } else {
    await env.DB.prepare(
      "UPDATE entitlements SET status='revoked',source_ref=NULL,note=?2,updated_at=?3 WHERE dossier_id=?1"
    ).bind(payment.dossier_id, reason, now).run();
  }
  await env.DB.prepare(
    "INSERT INTO entitlement_audit(dossier_id,action,plan,source,note,created_at) VALUES(?1,?2,?3,'paid',?4,?5)"
  ).bind(payment.dossier_id, "payment_" + status + "_revert", payment.target_plan, reason, now).run();
}

async function paymentFromResource(env, resource) {
  const customId = cleanPaymentId(resource?.custom_id);
  if (customId) {
    const byCustom = await env.DB.prepare("SELECT * FROM payments WHERE id=?1").bind(customId).first();
    if (byCustom) return byCustom;
  }
  const resourceId = String(resource?.id || "");
  if (resourceId) {
    const byCapture = await env.DB.prepare("SELECT * FROM payments WHERE provider_capture_id=?1").bind(resourceId).first();
    if (byCapture) return byCapture;
  }
  const related = resource?.supplementary_data?.related_ids || {};
  const captureId = String(related.capture_id || related.sale_id || "");
  if (captureId) {
    const byRelated = await env.DB.prepare("SELECT * FROM payments WHERE provider_capture_id=?1").bind(captureId).first();
    if (byRelated) return byRelated;
  }
  const orderId = String(related.order_id || "");
  if (orderId) {
    const byOrder = await env.DB.prepare("SELECT * FROM payments WHERE provider_order_id=?1").bind(orderId).first();
    if (byOrder) return byOrder;
  }
  const invoiceId = String(resource?.invoice_id || "");
  if (invoiceId.startsWith("CD-")) {
    const pid = cleanPaymentId(invoiceId.slice(3));
    if (pid) {
      const byInvoice = await env.DB.prepare("SELECT * FROM payments WHERE id=?1").bind(pid).first();
      if (byInvoice) return byInvoice;
    }
  }
  for (const link of resource?.links || []) {
    const match = String(link?.href || "").match(/\/captures\/([^/?#]+)/);
    if (match) {
      const byLink = await env.DB.prepare("SELECT * FROM payments WHERE provider_capture_id=?1").bind(match[1]).first();
      if (byLink) return byLink;
    }
  }
  return null;
}

async function verifyPayPalWebhook(request, env, event) {
  const webhookId = String(env.PAYPAL_WEBHOOK_ID || "");
  if (!webhookId) return false;
  const transmissionId = request.headers.get("paypal-transmission-id") || "";
  const transmissionTime = request.headers.get("paypal-transmission-time") || "";
  const transmissionSig = request.headers.get("paypal-transmission-sig") || "";
  const certUrl = request.headers.get("paypal-cert-url") || "";
  const authAlgo = request.headers.get("paypal-auth-algo") || "";
  if (!transmissionId || !transmissionTime || !transmissionSig || !certUrl || !authAlgo) return false;
  const result = await paypalApi(env, "/v1/notifications/verify-webhook-signature", {
    method: "POST",
    body: {
      transmission_id: transmissionId,
      transmission_time: transmissionTime,
      cert_url: certUrl,
      auth_algo: authAlgo,
      transmission_sig: transmissionSig,
      webhook_id: webhookId,
      webhook_event: event,
    },
  });
  return String(result.verification_status || "") === "SUCCESS";
}

async function disputePayment(env, resource) {
  const disputeId = String(resource?.dispute_id || resource?.id || "");
  if (!disputeId) return null;
  const details = await paypalApi(env, "/v1/customer/disputes/" + encodeURIComponent(disputeId));
  const transactions = Array.isArray(details?.disputed_transactions) ? details.disputed_transactions : [];
  for (const tx of transactions) {
    const sellerId = String(tx?.seller_transaction_id || tx?.seller_transaction?.transaction_id || tx?.seller_transaction?.id || "");
    if (!sellerId) continue;
    const payment = await env.DB.prepare("SELECT * FROM payments WHERE provider_capture_id=?1").bind(sellerId).first();
    if (payment) return { payment, details };
  }
  return { payment: null, details };
}

async function processPayPalWebhookEvent(env, event) {
  const type = String(event?.event_type || "");
  const resource = event?.resource || {};
  if (!PAYPAL_SECURITY_EVENTS.has(type)) return "ignored_event";

  if (type === "PAYMENT.CAPTURE.COMPLETED") {
    const capture = await confirmPayPalCapture(env, resource.id);
    const payment = await paymentFromResource(env, capture);
    if (!payment) return "completed_unmatched";
    if (["refunded","reversed","disputed"].includes(String(payment.status))) return "completed_after_block_ignored";
    await activatePaidEntitlement(env, payment, capture);
    return "completed_activated";
  }

  if (type === "PAYMENT.CAPTURE.REFUNDED" || type === "PAYMENT.CAPTURE.REVERSED") {
    const payment = await paymentFromResource(env, resource);
    if (!payment) return "refund_or_reversal_unmatched";
    const state = type.endsWith("REFUNDED") ? "refunded" : "reversed";
    await restorePreviousEntitlement(env, payment, state, "PayPal " + state + ": piano a pagamento ritirato automaticamente.");
    return state + "_reverted";
  }

  if (type === "CUSTOMER.DISPUTE.CREATED" || type === "CUSTOMER.DISPUTE.UPDATED") {
    const linked = await disputePayment(env, resource);
    if (!linked?.payment) return "dispute_unmatched";
    await restorePreviousEntitlement(env, linked.payment, "disputed", "Contestazione PayPal aperta: piano a pagamento sospeso automaticamente.");
    return "dispute_suspended";
  }

  if (type === "CUSTOMER.DISPUTE.RESOLVED") {
    const linked = await disputePayment(env, resource);
    if (!linked?.payment) return "resolved_dispute_unmatched";
    const outcome = String(linked.details?.outcome_code || linked.details?.dispute_outcome?.outcome_code || "");
    if (["RESOLVED_SELLER_FAVOUR","CANCELED_BY_BUYER"].includes(outcome) && linked.payment.provider_capture_id) {
      const capture = await confirmPayPalCapture(env, linked.payment.provider_capture_id);
      if (String(capture.status || "") === "COMPLETED") {
        await activatePaidEntitlement(env, linked.payment, capture);
        return "dispute_resolved_reactivated";
      }
    }
    await restorePreviousEntitlement(env, linked.payment, "disputed", "Contestazione PayPal risolta senza esito idoneo alla riattivazione automatica.");
    return "dispute_resolved_kept_suspended";
  }

  if (type === "PAYMENT.CAPTURE.DENIED" || type === "CHECKOUT.PAYMENT-APPROVAL.REVERSED") {
    const payment = await paymentFromResource(env, resource);
    if (payment) await env.DB.prepare("UPDATE payments SET status='failed',updated_at=?2 WHERE id=?1")
      .bind(payment.id, new Date().toISOString()).run();
    return "payment_failed";
  }

  return "pending_no_activation";
}

async function paypalWebhook(request, env) {
  await ensurePaymentSchema(env);
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 1024 * 1024) return json({ ok: false, error: "payload_too_large" }, 413);
  let event = {};
  try { event = await request.json(); } catch { return json({ ok: false, error: "invalid_json" }, 400); }
  const eventId = String(event?.id || "");
  const eventType = String(event?.event_type || "");
  if (!eventId || !eventType) return json({ ok: false, error: "invalid_webhook" }, 400);
  if (!PAYPAL_SECURITY_EVENTS.has(eventType)) return json({ ok: true, ignored: true });
  if (!String(env.PAYPAL_CLIENT_ID || "") || !String(env.PAYPAL_CLIENT_SECRET || "") || !String(env.PAYPAL_WEBHOOK_ID || "")) {
    return json({ ok: false, error: "paypal_not_configured" }, 503);
  }
  const verified = await verifyPayPalWebhook(request, env, event);
  if (!verified) return json({ ok: false, error: "invalid_webhook_signature" }, 401);

  const now = new Date().toISOString();
  const transmissionId = request.headers.get("paypal-transmission-id") || "";
  const resourceId = String(event?.resource?.id || event?.resource?.dispute_id || "");
  const inserted = await env.DB.prepare(`
    INSERT OR IGNORE INTO payment_events(event_id,event_type,transmission_id,resource_id,result,received_at)
    VALUES(?1,?2,?3,?4,'processing',?5)
  `).bind(eventId, eventType, transmissionId, resourceId, now).run();
  if (Number(inserted?.meta?.changes || 0) === 0) return json({ ok: true, duplicate: true });

  try {
    const result = await processPayPalWebhookEvent(env, event);
    await env.DB.prepare(
      "UPDATE payment_events SET result=?2,processed_at=?3 WHERE event_id=?1"
    ).bind(eventId, result, new Date().toISOString()).run();
    return json({ ok: true });
  } catch (error) {
    await env.DB.prepare("DELETE FROM payment_events WHERE event_id=?1").bind(eventId).run().catch(() => {});
    throw error;
  }
}


function payhipReady(env) {
  return paymentModel(env) === "payhip"
    && String(env.PAYHIP_API_KEY || "")
    && String(env.PAYHIP_MEDIUM_PRODUCT_KEY || "")
    && String(env.PAYHIP_FULL_PRODUCT_KEY || "");
}

function payhipProductKey(env, plan) {
  if (plan === "MEDIUM") return String(env.PAYHIP_MEDIUM_PRODUCT_KEY || "").trim();
  if (plan === "FULL") return String(env.PAYHIP_FULL_PRODUCT_KEY || "").trim();
  return "";
}

async function sha256Hex(value) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(String(value || "")));
  return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, "0")).join("");
}

function safeEqualText(a, b) {
  const x = String(a || "");
  const y = String(b || "");
  if (!x || x.length !== y.length) return false;
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x.charCodeAt(i) ^ y.charCodeAt(i);
  return diff === 0;
}

async function verifyPayhipWebhookSignature(env, event) {
  const apiKey = String(env.PAYHIP_API_KEY || "");
  if (!apiKey) return false;
  const expected = await sha256Hex(apiKey);
  return safeEqualText(String(event?.signature || "").toLowerCase(), expected.toLowerCase());
}

async function createPayhipCheckout(request, env) {
  await ensurePaymentSchema(env);
  if (!payhipReady(env)) return json({ ok: false, error: "payments_not_enabled" }, 503);

  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  const installationId = cleanInstallationId(body.installationId);
  const targetPlan = String(body.plan || "").toUpperCase();
  if (!dossierId || !installationId || !["MEDIUM", "FULL"].includes(targetPlan)) {
    return json({ ok: false, error: "invalid_input" }, 400);
  }
  if (!await paymentIdentityAllowed(env, dossierId, installationId)) {
    return json({ ok: false, error: "installation_not_recognized" }, 403);
  }
  if (!await paymentThrottleAllowed(env, dossierId)) {
    return json({ ok: false, error: "too_many_payment_attempts" }, 429);
  }

  const current = await env.DB.prepare(
    "SELECT dossier_id, license_id, plan, status, source, source_ref, valid_until, created_at FROM entitlements WHERE dossier_id=?1"
  ).bind(dossierId).first();
  const currentPlan = !current || current.status !== "active" || expired(current.valid_until)
    ? "FREE"
    : (PLANS.has(String(current.plan || "").toUpperCase()) ? String(current.plan).toUpperCase() : "FREE");

  if (PLAN_RANK[currentPlan] >= PLAN_RANK[targetPlan]) {
    return json({ ok: false, error: "plan_already_active" }, 409);
  }
  if (currentPlan === "MEDIUM" && targetPlan === "FULL") {
    return json({ ok: false, error: "medium_to_full_price_not_defined" }, 409);
  }

  const pricing = planPricing(env);
  const cents = amountCents(pricing.plans[targetPlan]?.current);
  const productKey = payhipProductKey(env, targetPlan);
  if (cents <= 0 || !productKey) return json({ ok: false, error: "price_not_available" }, 503);

  const paymentId = crypto.randomUUID();
  const now = new Date().toISOString();
  await env.DB.prepare(`
    INSERT INTO payments(
      id, provider, dossier_id, installation_id, target_plan,
      previous_plan, previous_status, previous_source, previous_source_ref, previous_valid_until,
      amount_cents, currency, status, created_at, updated_at
    ) VALUES(?1,'payhip',?2,?3,?4,?5,?6,?7,?8,?9,?10,'EUR','created',?11,?11)
  `).bind(
    paymentId, dossierId, installationId, targetPlan,
    currentPlan, String(current?.status || ""), String(current?.source || ""),
    String(current?.source_ref || ""), current?.valid_until || null,
    cents, now
  ).run();

  const checkout = new URL("https://payhip.com/buy");
  checkout.searchParams.set("link", productKey);
  checkout.searchParams.set("metadata[cd_payment]", paymentId);

  return json({
    ok: true,
    paymentId,
    checkoutUrl: checkout.toString(),
    plan: targetPlan,
    amount: (cents / 100).toFixed(2),
    currency: "EUR",
  });
}

async function payhipPaymentStatus(request, env) {
  await ensurePaymentSchema(env);
  let body = {};
  try { body = await request.json(); } catch {}
  const paymentId = cleanPaymentId(body.paymentId);
  const installationId = cleanInstallationId(body.installationId);
  if (!paymentId || !installationId) return json({ ok: false, error: "invalid_input" }, 400);
  const payment = await env.DB.prepare(
    "SELECT id,installation_id,target_plan,status,updated_at FROM payments WHERE id=?1 AND provider='payhip'"
  ).bind(paymentId).first();
  if (!payment || String(payment.installation_id) !== installationId) {
    return json({ ok: false, error: "payment_not_found" }, 404);
  }
  return json({
    ok: true,
    paymentId,
    plan: payment.target_plan,
    status: payment.status,
    updatedAt: payment.updated_at,
  });
}

async function activatePayhipEntitlement(env, payment, event) {
  const transactionId = String(event?.id || "").trim();
  if (!transactionId) throw new Error("payhip_transaction_missing");
  const currency = String(event?.currency || "").toUpperCase();
  const paidCents = Number(event?.price);
  if (currency !== String(payment.currency || "EUR")) throw new Error("payhip_currency_mismatch");
  if (!Number.isFinite(paidCents) || paidCents < Number(payment.amount_cents)) {
    throw new Error("payhip_amount_mismatch");
  }

  const items = Array.isArray(event?.items) ? event.items : [];
  if (items.length !== 1) throw new Error("payhip_item_count_mismatch");
  const item = items[0] || {};
  const expectedProductKey = payhipProductKey(env, String(payment.target_plan || "").toUpperCase());
  if (!expectedProductKey || String(item.product_key || "") !== expectedProductKey) {
    throw new Error("payhip_product_mismatch");
  }
  if (Number(item.quantity || 1) !== 1) throw new Error("payhip_quantity_mismatch");

  const existingTx = await env.DB.prepare(
    "SELECT id FROM payments WHERE provider='payhip' AND provider_order_id=?1 LIMIT 1"
  ).bind(transactionId).first();
  if (existingTx && String(existingTx.id) !== String(payment.id)) throw new Error("payhip_transaction_reused");

  const now = new Date().toISOString();
  const current = await env.DB.prepare("SELECT * FROM entitlements WHERE dossier_id=?1")
    .bind(payment.dossier_id).first();
  const currentPlan = (!current || current.status !== "active" || expired(current.valid_until))
    ? "FREE"
    : String(current.plan || "FREE").toUpperCase();

  await env.DB.prepare(
    "UPDATE payments SET provider_order_id=?2,status='completed',updated_at=?3 WHERE id=?1"
  ).bind(payment.id, transactionId, now).run();

  if (PLAN_RANK[currentPlan] > PLAN_RANK[payment.target_plan] && String(current?.source_ref || "") !== payment.id) {
    await env.DB.prepare(
      "INSERT INTO entitlement_audit(dossier_id,action,plan,source,note,created_at) VALUES(?1,'payment_completed_no_downgrade',?2,'paid',?3,?4)"
    ).bind(payment.dossier_id, payment.target_plan, "Pagamento Payhip acquisito senza abbassare un piano superiore già attivo.", now).run();
    return;
  }

  const licenseId = current?.license_id || crypto.randomUUID();
  const createdAt = current?.created_at || now;
  await env.DB.prepare(`
    INSERT INTO entitlements(dossier_id,license_id,account_email,plan,status,source,note,valid_until,created_at,updated_at,source_ref)
    VALUES(?1,?2,NULL,?3,'active','paid',?4,NULL,?5,?6,?7)
    ON CONFLICT(dossier_id) DO UPDATE SET
      plan=excluded.plan,status='active',source='paid',source_ref=excluded.source_ref,
      note=excluded.note,valid_until=NULL,updated_at=excluded.updated_at
  `).bind(payment.dossier_id, licenseId, payment.target_plan, "Pagamento Payhip confermato", createdAt, now, payment.id).run();

  await env.DB.prepare(
    "INSERT INTO entitlement_audit(dossier_id,action,plan,source,note,created_at) VALUES(?1,'payment_grant',?2,'paid',?3,?4)"
  ).bind(payment.dossier_id, payment.target_plan, "Payhip transaction " + transactionId, now).run();
}

function payhipPaymentIdFromEvent(event) {
  const metadata = event?.metadata && typeof event.metadata === "object" ? event.metadata : {};
  return cleanPaymentId(metadata.cd_payment || metadata.payment_intent || "");
}

async function processPayhipWebhookEvent(env, event) {
  const type = String(event?.type || "");
  const transactionId = String(event?.id || "").trim();
  if (!["paid", "refunded"].includes(type)) return "ignored_event";
  if (!transactionId) throw new Error("payhip_transaction_missing");

  if (type === "paid") {
    const paymentId = payhipPaymentIdFromEvent(event);
    if (!paymentId) return "paid_unmatched";
    const payment = await env.DB.prepare(
      "SELECT * FROM payments WHERE id=?1 AND provider='payhip'"
    ).bind(paymentId).first();
    if (!payment) return "paid_unmatched";
    if (["refunded","reversed","disputed"].includes(String(payment.status))) return "paid_after_block_ignored";
    await activatePayhipEntitlement(env, payment, event);
    return "paid_activated";
  }

  const payment = await env.DB.prepare(
    "SELECT * FROM payments WHERE provider='payhip' AND provider_order_id=?1 LIMIT 1"
  ).bind(transactionId).first();
  if (!payment) return "refund_unmatched";
  const refunded = Number(event?.amount_refunded || 0);
  if (!Number.isFinite(refunded) || refunded <= 0) return "refund_zero_ignored";
  await restorePreviousEntitlement(
    env,
    payment,
    "refunded",
    "Rimborso Payhip rilevato: piano a pagamento ritirato automaticamente."
  );
  return refunded >= Number(event?.price || payment.amount_cents)
    ? "full_refund_reverted"
    : "partial_refund_reverted";
}

async function payhipWebhook(request, env) {
  await ensurePaymentSchema(env);
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 256 * 1024) return json({ ok: false, error: "payload_too_large" }, 413);

  let event = {};
  try { event = await request.json(); } catch { return json({ ok: false, error: "invalid_json" }, 400); }
  const type = String(event?.type || "");
  if (!["paid", "refunded"].includes(type)) return json({ ok: true, ignored: true });
  if (!payhipReady(env)) return json({ ok: false, error: "payhip_not_configured" }, 503);
  if (!await verifyPayhipWebhookSignature(env, event)) {
    return json({ ok: false, error: "invalid_webhook_signature" }, 401);
  }

  const transactionId = String(event?.id || "").trim();
  if (!transactionId) return json({ ok: false, error: "invalid_webhook" }, 400);
  const eventMoment = type === "refunded"
    ? String(event?.date_refunded || "") + ":" + String(event?.amount_refunded || "")
    : String(event?.date || "");
  const eventId = "payhip:" + type + ":" + transactionId + ":" + eventMoment;
  const now = new Date().toISOString();

  const inserted = await env.DB.prepare(`
    INSERT OR IGNORE INTO payment_events(event_id,event_type,transmission_id,resource_id,result,received_at)
    VALUES(?1,?2,'',?3,'processing',?4)
  `).bind(eventId, "PAYHIP." + type.toUpperCase(), transactionId, now).run();
  if (Number(inserted?.meta?.changes || 0) === 0) return json({ ok: true, duplicate: true });

  try {
    const result = await processPayhipWebhookEvent(env, event);
    await env.DB.prepare(
      "UPDATE payment_events SET result=?2,processed_at=?3 WHERE event_id=?1"
    ).bind(eventId, result, new Date().toISOString()).run();
    return json({ ok: true });
  } catch (error) {
    await env.DB.prepare("DELETE FROM payment_events WHERE event_id=?1").bind(eventId).run().catch(() => {});
    throw error;
  }
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
    "http://127.0.0.1:8895",
    "http://localhost:8895",
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
  await ensurePaymentSchema(env);
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
      source_ref=NULL,
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
  await ensurePaymentSchema(env);
  let body = {};
  try { body = await request.json(); } catch {}
  const dossierId = cleanDossierId(body.dossierId);
  const note = String(body.note || "").trim().slice(0, 500);
  if (!dossierId) return json({ ok: false, error: "dossier_id_invalid" }, 400);
  const now = new Date().toISOString();
  await env.DB.prepare("UPDATE entitlements SET status='revoked', source_ref=NULL, note=?2, updated_at=?3 WHERE dossier_id=?1")
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
  body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#f4f7f6;color:#17342e;margin:0}.wrap{max-width:960px;margin:40px auto;padding:0 20px}.card{background:#fff;border:1px solid #d9e7e2;border-radius:18px;padding:22px;margin:16px 0}label{display:grid;gap:6px;font-weight:700;margin:12px 0}input,select,textarea,button{font:inherit;padding:11px 12px;border-radius:10px;border:1px solid #bfd3cc}button{cursor:pointer;font-weight:800;background:#2f796d;color:#fff;border:0}.danger{background:#b42318}.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}.search-block{display:grid;gap:6px}.search-block>label{margin:0}.search-controls{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:stretch}.search-controls input,.search-controls button{height:44px;box-sizing:border-box;margin:0}.search-controls button{display:flex;align-items:center;justify-content:center;white-space:nowrap}.status{display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:12px;font-weight:800;margin:14px 0}.status.hidden{display:none}.status.ok{background:#e7f6ec;color:#166534;border:1px solid #a7dfb7}.status.err{background:#fdeaea;color:#991b1b;border:1px solid #efb0b0}.lamp{width:14px;height:14px;border-radius:50%;flex:0 0 14px;background:#9ca3af}.status.ok .lamp{background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.14)}.status.err .lamp{background:#ef4444;box-shadow:0 0 0 4px rgba(239,68,68,.14)}details{margin-top:12px}.out{white-space:pre-wrap;background:#10231f;color:#dff3ed;padding:16px;border-radius:12px;min-height:80px;max-height:360px;overflow:auto;font-size:13px}.usage-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:14px 0}.usage-kpi{background:#f4f7f6;border:1px solid #d9e7e2;border-radius:12px;padding:12px}.usage-kpi small{display:block;color:#5d746d}.usage-kpi strong{font-size:24px}.usage-filter{display:flex;align-items:end;gap:12px;margin:12px 0}.usage-filter label{margin:0;gap:4px;font-size:12px}.usage-filter select{min-width:130px;padding:7px 9px;font-size:12px}.usage-filter-total{display:flex;align-items:center;gap:6px;min-height:34px;padding:0 10px;border:1px solid #d9e7e2;border-radius:10px;background:#f4f7f6;font-size:12px;white-space:nowrap}.usage-filter-total strong{font-size:16px}.usage-table-wrap{overflow:hidden}.usage-table{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;font-size:9.8px}.usage-table th,.usage-table td{padding:6px 4px;text-align:left;white-space:nowrap;border-right:1px solid rgba(191,211,204,.45);border-bottom:1px solid rgba(191,211,204,.65);background:linear-gradient(to bottom,#ffffff 0%,#ffffff 72%,#f4f8f6 100%);overflow:hidden;text-overflow:clip}.usage-table th{font-size:9.8px;font-weight:800;background:linear-gradient(to bottom,#ffffff 0%,#f7faf9 100%)}.usage-table th:nth-child(1),.usage-table td:nth-child(1){width:28%}.usage-table th:nth-child(2),.usage-table td:nth-child(2){width:6%}.usage-table th:nth-child(3),.usage-table td:nth-child(3){width:14%}.usage-table th:nth-child(4),.usage-table td:nth-child(4){width:14%}.usage-table th:nth-child(5),.usage-table td:nth-child(5){width:5%}.usage-table th:nth-child(6),.usage-table td:nth-child(6){width:9%}.usage-table th:nth-child(7),.usage-table td:nth-child(7){width:7%}.usage-table th:nth-child(8),.usage-table td:nth-child(8){width:11%}.usage-table th:nth-child(9),.usage-table td:nth-child(9){width:6%;text-align:center}.usage-table th:last-child,.usage-table td:last-child{border-right:0}.usage-table tbody tr:last-child td{border-bottom:0}.badge{display:inline-block;padding:3px 6px;border-radius:999px;font-weight:800;font-size:9.4px}.badge.ok{background:#e7f6ec;color:#166534}.badge.warn{background:#fff3cd;color:#7a5600}.badge.off{background:#fdeaea;color:#991b1b}.usage-dot{display:inline-block;width:13px;height:13px;border-radius:50%;vertical-align:middle;box-shadow:0 0 0 2px rgba(23,52,46,.08)}.usage-dot.red{background:#dc2626}.usage-dot.yellow{background:#f2b705}.usage-dot.green{background:#22a447}@media(max-width:700px){.row{grid-template-columns:1fr}.search-controls{grid-template-columns:1fr}.search-controls button{width:100%}.usage-summary{grid-template-columns:1fr 1fr}}
  </style><div class="wrap"><h1>Gestore licenze Clinica Digitale</h1><p>Il token amministratore non viene salvato dal browser.</p><div class="card"><label>Token amministratore<input id="key" type="password" autocomplete="off"></label><div class="row"><label>ID Dossier<input id="dossier"></label><label>E-mail account<input id="email" type="email"></label></div><div class="row"><label>Piano<select id="plan"><option>FREE</option><option>MEDIUM</option><option>FULL</option></select></label><label>Origine<select id="source"><option value="manual">Manuale</option><option value="gift">Omaggio</option><option value="tester">Tester</option><option value="staff">Staff</option><option value="promo">Promozione</option><option value="paid">Pagamento</option></select></label></div><label>Validità fino a (opzionale)<input id="until" type="datetime-local"></label><label>Nota<textarea id="note" rows="3"></textarea></label><p><button id="grant">Assegna / aggiorna</button> <button id="revoke" class="danger">Revoca</button></p></div><div class="card"><div class="search-block"><label for="q">Cerca</label><div class="search-controls"><input id="q"><button id="search">Cerca licenze</button></div></div><div id="status" class="status hidden"><span class="lamp"></span><span id="statusText"></span></div><details id="technical"><summary>Dettagli tecnici</summary><div id="out" class="out"></div></details></div><div class="card"><div class="card-title-row"><div><h2>Utilizzo dei Dossier</h2><p>Solo dati tecnici anonimi: nessun documento o dato sanitario.</p></div><button id="usageRefresh">Aggiorna utilizzo</button></div><div class="usage-summary"><div class="usage-kpi"><small>Dossier rilevati</small><strong id="usageTotal">0</strong></div><div class="usage-kpi"><small>Attivi ≤ 7 giorni</small><strong id="usageActive">0</strong></div><div class="usage-kpi"><small>Solo 1 avvio</small><strong id="usageSingle">0</strong></div><div class="usage-kpi"><small>Inattivi &gt; 7 giorni</small><strong id="usageInactive">0</strong></div></div><div class="usage-filter"><label for="usageFilter">Selezione<select id="usageFilter"><option value="all">Tutti</option><option value="red">Rosso</option><option value="yellow">Giallo</option><option value="green">Verde</option></select></label><div class="usage-filter-total">Totale: <strong id="usageFilterTotal">0</strong></div></div><div class="usage-table-wrap"><table class="usage-table"><thead><tr><th>Dossier</th><th>Piano</th><th>Primo utilizzo</th><th>Ultimo utilizzo</th><th>Avvii</th><th>Installazioni</th><th>Versione</th><th>Stato</th><th>Uso</th></tr></thead><tbody id="usageBody"><tr><td colspan="9">Premi “Aggiorna utilizzo”.</td></tr></tbody></table></div></div></div><script>
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
  const fmtDate=value=>{if(!value)return'';try{return new Date(value).toLocaleString('it-IT')}catch{return value}};
  function escHtml(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function activityHtml(row){
    if(row.activity==='single_launch')return '<span class="badge warn">Solo 1 avvio</span>';
    if(row.activity==='active')return '<span class="badge ok">'+(row.daysInactive===0?'Usato oggi':'Attivo · '+row.daysInactive+' gg')+'</span>';
    return '<span class="badge off">Inattivo da '+(row.daysInactive??'?')+' gg</span>';
  }
  let usageRows=[];
  function usageLevel(row){
    const n=Number(row.launch_count||0);
    if(n<=1)return 'red';
    if(n<=10)return 'yellow';
    return 'green';
  }
  function usageDot(row){
    const level=usageLevel(row);
    const label=level==='red'?'Rosso':level==='yellow'?'Giallo':'Verde';
    return '<span class="usage-dot '+level+'" title="'+label+'" aria-label="'+label+'"></span>';
  }
  function renderUsageRows(){
    const filter=$('usageFilter').value;
    const rows=filter==='all'?usageRows:usageRows.filter(row=>usageLevel(row)===filter);
    $('usageFilterTotal').textContent=rows.length;
    $('usageBody').innerHTML=rows.length?rows.map(row=>'<tr><td><strong>'+escHtml(row.dossier_id)+'</strong></td><td>'+escHtml(row.plan)+'</td><td>'+escHtml(fmtDate(row.first_seen))+'</td><td>'+escHtml(fmtDate(row.last_seen))+'</td><td>'+escHtml(row.launch_count)+'</td><td>'+escHtml(row.installations)+'</td><td>'+escHtml(row.app_version||'')+'</td><td>'+activityHtml(row)+'</td><td>'+usageDot(row)+'</td></tr>').join(''):'<tr><td colspan="9">Nessun Dossier per questa selezione.</td></tr>';
  }
  async function refreshUsage(){
    try{
      const res=await fetch('/v1/admin/usage',{headers:headers()});
      const data=await res.json();
      if(!res.ok||!data.ok)throw new Error(data.error||'lettura_non_disponibile');
      $('usageTotal').textContent=data.summary?.dossiers??0;
      $('usageActive').textContent=data.summary?.active7d??0;
      $('usageSingle').textContent=data.summary?.singleLaunch??0;
      $('usageInactive').textContent=data.summary?.inactiveOver7d??0;
      usageRows=Array.isArray(data.usage)?data.usage:[];
      renderUsageRows();
    }catch(e){
      usageRows=[];
      $('usageFilterTotal').textContent='0';
      $('usageBody').innerHTML='<tr><td colspan="9">Impossibile leggere le statistiche: '+escHtml(e.message)+'</td></tr>';
    }
  }
  $('usageRefresh').onclick=refreshUsage;
  $('usageFilter').onchange=renderUsageRows;
  </script></html>`;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(request, env) });
    let response;
    try {
      if (request.method === "GET" && url.pathname === "/health") response = json({ ok: true, service: "clinica-digitale-licenze", build: String(env.BUILD_ID || "unknown"), payments: paymentModel(env) === "payhip" ? "payhip" : (paymentModel(env) === "one_time" ? String(env.PAYPAL_ENVIRONMENT || "sandbox") : "disabled") });
      else if (request.method === "GET" && url.pathname === "/v1/public/plans") response = json(planPricing(env));
      else if (request.method === "GET" && url.pathname === "/admin") response = new Response(adminHtml(), { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", ...securityHeaders(), "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'" } });
      else if (request.method === "POST" && url.pathname === "/v1/license/resolve") response = await resolveLicense(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/usage/ping") response = await usagePing(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/payments/payhip/create-checkout") response = await createPayhipCheckout(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/payments/payhip/status") response = await payhipPaymentStatus(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/payments/payhip/webhook") response = await payhipWebhook(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/payments/paypal/create-order") response = await createPayPalOrder(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/payments/paypal/capture-order") response = await capturePayPalOrder(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/payments/paypal/webhook") response = await paypalWebhook(request, env);
      else if (request.method === "GET" && url.pathname === "/v1/admin/usage") response = await listUsage(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/admin/entitlements") response = await grantEntitlement(request, env);
      else if (request.method === "POST" && url.pathname === "/v1/admin/revoke") response = await revokeEntitlement(request, env);
      else if (request.method === "GET" && url.pathname === "/v1/admin/entitlements") response = await listEntitlements(request, env);
      else response = json({ ok: false, error: "not_found" }, 404);
    } catch (error) {
      console.error("worker_error", String(error?.message || error));
      response = json({ ok: false, error: "internal_error" }, 500);
    }
    const headers = corsHeaders(request, env);
    for (const [k, v] of Object.entries(headers)) response.headers.set(k, v);
    return response;
  },
};
