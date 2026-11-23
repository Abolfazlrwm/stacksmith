import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const baseUrl = __ENV.K6_BASE_URL || 'http://127.0.0.1:8090';
const failureRate = new Rate('health_check_failures');

export const options = {
  stages: [
    { duration: '10s', target: 20 },   // ramp to 20 VUs
    { duration: '20s', target: 50 },   // ramp to 50 VUs
    { duration: '30s', target: 50 },   // hold at 50 VUs
    { duration: '10s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],     // < 1% failures
    health_check_failures: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${baseUrl}/health/live/`);
  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'body has alive': (r) => r.json('status') === 'alive',
  });
  failureRate.add(!ok);
  sleep(0.1);
}
