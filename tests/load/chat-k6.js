import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Load test for POST /api/chat/ — the real business endpoint.
//
// Unlike tests/load/health.js (which probes /health/live/), this exercises
// the full chat pipeline: JSON parse → RAG retrieval over pgvector → LLM
// call → citation mapping → DB write. It is the closest thing we have to a
// real-user load test.
//
// The chat endpoint calls the configured LLM provider, so by default this
// test will fail unless either:
//   - DOCUBOT_LLM_PROVIDER=stub  (returns a fixed string, no API call) — set
//     this in CI so the load test runs without LLM credentials.
//   - DOCUBOT_LLM_PROVIDER=ollama and an Ollama instance is up — used in
//     self-hosted prod load tests.
//   - DOCUBOT_LLM_PROVIDER=openai/anthropic and credentials are set — used
//     for real capacity planning; watch the bill.
//
// The corpus must be seeded before this test runs. Use:
//   python3 scripts/demo.py --owner loadtest
// to ingest the demo corpus under owner "loadtest", then point K6 at the
// same owner so retrieval finds the seeded chunks.

const baseUrl = __ENV.K6_BASE_URL || 'http://127.0.0.1:8090';
const owner = __ENV.K6_OWNER || 'loadtest';

const failureRate = new Rate('chat_failures');
const answerLatency = new Trend('chat_answer_latency', true);

// A small pool of questions that match the demo corpus. Cycling through
// them warms the embedding cache and exercises different retrieval paths.
const questions = [
  'What is docubot?',
  'What does StackSmith include?',
  'How is multi-user isolation enforced?',
  'What are the SLO targets?',
  'How much does it cost to run?',
  'What embedding model is used?',
  'Describe the disaster recovery drill.',
  'What containers make up the prod stack?',
];

export const options = {
  stages: [
    { duration: '10s', target: 5 },    // gentle ramp — chat is expensive
    { duration: '30s', target: 10 },   // hold at 10 VUs
    { duration: '10s', target: 0 },    // ramp down
  ],
  thresholds: {
    // Chat is allowed to be slower than /health/ — it does real work.
    // The SLO is P99 < 500ms; under load we assert P95 < 2.5s to leave
    // headroom for the LLM round-trip.
    http_req_duration: ['p(95)<2500'],
    http_req_failed: ['rate<0.02'],     // < 2% transport failures
    chat_failures: ['rate<0.05'],       // < 5% business failures
  },
};

export default function () {
  const q = questions[__ITER % questions.length];
  const res = http.post(
    `${baseUrl}/api/chat/`,
    JSON.stringify({ question: q, top_k: 5 }),
    {
      headers: {
        'Content-Type': 'application/json',
        'X-Docubot-Owner': owner,
      },
      timeout: '30s',
    },
  );
  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'has answer': (r) => {
      try { return r.json('answer') && r.json('answer').length > 0; }
      catch (_) { return false; }
    },
    'has citations': (r) => {
      try { return Array.isArray(r.json('citations')); }
      catch (_) { return false; }
    },
  });
  failureRate.add(!ok);
  if (ok) answerLatency.add(res.timings.duration);
  // Pacing — chat users don't fire 50 req/s each.
  sleep(1);
}

export function handleSummary(data) {
  // Emit a tiny summary to stderr so it shows up in the workflow log.
  const p95 = data.metrics.chat_answer_latency
    ? data.metrics.chat_answer_latency.values['p(95)'] : 'n/a';
  console.log(`\n[chat-k6] p95 answer latency: ${p95} ms`);
  return {};
}
