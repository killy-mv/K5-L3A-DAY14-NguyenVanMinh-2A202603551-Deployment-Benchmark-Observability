# Deployment Information

## Public URL

https://agent-production-37de1463.up.railway.app

## Platform

Railway (trial). Deploy 06-lab-complete/, không dùng app mẫu Part 3.

## Trạng thái

- CP5: PASS 12/12 local, 43/43 checks.
- Railway CLI: 5.75.0.
- Railway authentication: thành công.
- Cloud Redis và agent: SUCCESS. Public domain HTTPS đã tạo.

## Environment Variables

Đã xác nhận các biến trên Railway: PORT (platform), REDIS_URL (Redis service), AGENT_API_KEY (secret), ENVIRONMENT=production, RATE_LIMIT_PER_MINUTE=10, MONTHLY_BUDGET_USD=10.

## Test Commands

Sau khi có public URL, đặt BASE và AGENT_API_KEY trong terminal (không ghi key vào Git).

```bash
curl -sS -o /dev/null -w '%{http_code}
' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}
' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}
' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}
' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Kết quả thực tế ngày 25/11/2026: 200, 200, 401, 200. Ba test đầu chạy curl; test có key chạy Python urllib thông qua railway run --service agent --no-local, không in secret.

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png) — agent và Redis Online.
- [Service running](screenshots/running.png) — Active, Deployment successful.
- [Test results](screenshots/test.png) — học viên tự chạy curl: 200, 200, 401, 200; không hiển thị key.
