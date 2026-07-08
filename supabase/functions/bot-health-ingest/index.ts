import { createClient } from "npm:@supabase/supabase-js@2";

type HealthPayload = Record<string, unknown>;

const BOT_ID = "bota-termux-primary";
const MAX_TEXT = 240;

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
    },
  });
}

function getEnv(name: string): string {
  return Deno.env.get(name) ?? "";
}

function getSupabaseAdminKey(): string {
  const legacy = getEnv("SUPABASE_SERVICE_ROLE_KEY");
  if (legacy) return legacy;

  const singleSecretKey = getEnv("SUPABASE_SECRET_KEY");
  if (singleSecretKey) return singleSecretKey;

  const secretKeys = getEnv("SUPABASE_SECRET_KEYS");
  if (!secretKeys) return "";

  try {
    const parsed = JSON.parse(secretKeys) as Record<string, string>;
    return parsed.default ?? parsed.service_role ?? "";
  } catch {
    return "";
  }
}

function safeEqual(a: string, b: string): boolean {
  const aa = new TextEncoder().encode(a);
  const bb = new TextEncoder().encode(b);

  if (aa.length !== bb.length) return false;

  let diff = 0;
  for (let i = 0; i < aa.length; i += 1) {
    diff |= aa[i] ^ bb[i];
  }
  return diff === 0;
}

function sanitizeText(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;

  let s = String(value).slice(0, MAX_TEXT);

  s = s.replace(/Bearer\s+[A-Za-z0-9._-]+/gi, "Bearer [redacted]");
  s = s.replace(/eyJ[A-Za-z0-9._-]{20,}/g, "[redacted-jwt]");
  s = s.replace(/SUPABASE_[A-Z_]+/g, "[redacted-env-name]");
  s = s.replace(/TELEGRAM_[A-Z_]+/g, "[redacted-env-name]");
  s = s.replace(/\/data\/data\/com\.termux\/files\/home\/BotA/g, "$BOTA_ROOT");

  return s;
}

function parseNonNegativeInt(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;

  const n = Number(value);
  if (!Number.isFinite(n)) return null;

  const i = Math.trunc(n);
  if (i < 0) return null;
  if (i > 100000) return 100000;

  return i;
}

function parseTimestamp(value: unknown): string | null {
  if (typeof value !== "string" || value.trim() === "") return null;

  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;

  return d.toISOString();
}

function parseBotMode(value: unknown): "HEALTHY" | "DEGRADED" | "UNKNOWN" {
  if (value === "HEALTHY" || value === "DEGRADED" || value === "UNKNOWN") {
    return value;
  }
  return "UNKNOWN";
}

function buildRow(payload: HealthPayload): Record<string, unknown> {
  const details = {
    payload_version: sanitizeText(payload.payload_version) ?? "v1",
    client_observed_at_utc: parseTimestamp(payload.observed_at_utc),
  };

  return {
    bot_id: BOT_ID,
    source: "termux",
    observed_at_utc: new Date().toISOString(),

    bot_mode: parseBotMode(payload.bot_mode),
    last_supervisor_run_utc: parseTimestamp(payload.last_supervisor_run_utc),

    watcher_log_age_min: parseNonNegativeInt(payload.watcher_log_age_min),
    updater_log_age_min: parseNonNegativeInt(payload.updater_log_age_min),
    closer_log_age_min: parseNonNegativeInt(payload.closer_log_age_min),
    shadow_log_age_min: parseNonNegativeInt(payload.shadow_log_age_min),

    eurusd_m15_cache_age_min: parseNonNegativeInt(payload.eurusd_m15_cache_age_min),
    gbpusd_m15_cache_age_min: parseNonNegativeInt(payload.gbpusd_m15_cache_age_min),
    eurusd_h1_cache_age_min: parseNonNegativeInt(payload.eurusd_h1_cache_age_min),
    gbpusd_h1_cache_age_min: parseNonNegativeInt(payload.gbpusd_h1_cache_age_min),

    failure_reasons: sanitizeText(payload.failure_reasons),
    last_degraded_utc: parseTimestamp(payload.last_degraded_utc),
    last_degraded_reason: sanitizeText(payload.last_degraded_reason),
    last_healthy_utc: parseTimestamp(payload.last_healthy_utc),

    details,
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }

  if (req.method !== "POST") {
    return jsonResponse({ ok: false, error: "method_not_allowed" }, 405);
  }

  const expectedSecret = getEnv("BOTA_HEALTH_INGEST_SECRET");
  if (!expectedSecret) {
    return jsonResponse({ ok: false, error: "server_not_configured" }, 500);
  }

  const providedSecret = req.headers.get("x-bota-health-secret") ?? "";
  if (!providedSecret || !safeEqual(providedSecret, expectedSecret)) {
    return jsonResponse({ ok: false, error: "unauthorized" }, 401);
  }

  let payload: HealthPayload;
  try {
    payload = await req.json();
  } catch {
    return jsonResponse({ ok: false, error: "invalid_json" }, 400);
  }

  if (payload.bot_id !== BOT_ID) {
    return jsonResponse({ ok: false, error: "invalid_bot_id" }, 400);
  }

  const supabaseUrl = getEnv("SUPABASE_URL");
  const supabaseAdminKey = getSupabaseAdminKey();

  if (!supabaseUrl || !supabaseAdminKey) {
    return jsonResponse({ ok: false, error: "supabase_admin_not_configured" }, 500);
  }

  const supabase = createClient(supabaseUrl, supabaseAdminKey, {
    auth: { persistSession: false },
  });

  const row = buildRow(payload);

  const { error } = await supabase
    .from("bot_runtime_health")
    .upsert(row, { onConflict: "bot_id" });

  if (error) {
    return jsonResponse({ ok: false, error: "upsert_failed" }, 500);
  }

  return jsonResponse({
    ok: true,
    bot_id: BOT_ID,
    observed_at_utc: row.observed_at_utc,
  });
});
