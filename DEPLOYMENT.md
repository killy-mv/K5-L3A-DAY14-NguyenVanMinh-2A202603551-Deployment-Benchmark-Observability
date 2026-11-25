# Deployment Information

## Public URL

Chưa có — chờ đăng nhập Railway và triển khai.

## Platform

Railway (dự kiến). Deploy 06-lab-complete/, không dùng app mẫu Part 3.

## Trạng thái

- CP5: PASS 12/12 local, 43/43 checks.
- Railway CLI: 5.75.0.
- railway whoami: Unauthorized; cần railway login.
- Cloud Redis, agent và public domain: chưa tạo.

## Environment Variables

Các biến dự kiến đặt trên Railway, chưa xác nhận đã đặt: PORT (platform), REDIS_URL (Redis service), AGENT_API_KEY (secret), ENVIRONMENT=production, RATE_LIMIT_PER_MINUTE=10, MONTHLY_BUDGET_USD=10.

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

Kỳ vọng lần lượt 200, 200, 401, 200; chưa chạy trên cloud.

## Screenshots

Chưa có dashboard.png, running.png, test.png. Chỉ bổ sung sau deployment thật.
