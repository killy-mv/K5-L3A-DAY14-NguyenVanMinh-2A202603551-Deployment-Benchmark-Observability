# Benchmark & Observability Report — Day 14

> Copy file này thành `BENCHMARK_REPORT.md` trong repo của bạn và điền đầy đủ.
> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Nguyen Van Minh
**Ngày chạy:** 25/11/2026
**Môi trường:** Windows / Ubuntu 24.04 WSL2; AMD Ryzen 5 5600H, 12 logical CPUs, 7.5 GiB RAM khả dụng cho WSL; Python 3.12.3, Mock LLM small. CP7 local, không dùng cloud; CP8 Docker Desktop, Python 3.11-slim, mỗi agent giới hạn 0.5 CPU / 256 MiB, mock LLM.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của load_test.py; phản ánh trải nghiệm phần lớn request. |
| Error rate `/ask` | ≤ 2% | Cho phép lỗi upstream nhỏ, vẫn đạt ít nhất 98% HTTP 200. |
| Accuracy trên golden dataset | ≥ 100% (gate cuối) | Theo CP7: 23/23 câu, không regression; baseline dùng ngưỡng mặc định 80%. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.51 | 189.8 | 218.2 | 1697.4 | 2.00% | PASS |
| 10 | 42.45 | 188.8 | 217.2 | 1673.4 | 0.67% | PASS |
| 50 | 105.88 | 194.0 | 261.3 | 1695.5 | 0.33% | PASS |
| 100 | 62.53 | 321.2 | 2737.6 | 3091.2 | 0.67% | FAIL |

**Nhận xét:** RPS không tăng tuyến tính: từ 4.51 lên 42.45 và 105.88, rồi giảm còn 62.53 ở concurrency 100. p95 tăng lên 2737.6 ms, vi phạm SLO; dấu hiệu bão hòa/overhead kết nối, scheduling hoặc logging, chưa có profiling để kết luận nguyên nhân. Mỗi mức 300 requests, MOCK_SLOW_RATE=0.03, MOCK_ERROR_RATE=0.01, mặc định latency/jitter, loại warm-up; latency chỉ tính HTTP 200 theo script. Giữ cả kết quả FAIL, không chạy chọn lọc.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 188.4 | 219.0 | 224.8 |
| 0.03 (mặc định) | 259.0 | 232.0 | 1696.7 |
| 0.1 | 329.6 | 1685.9 | 1705.4 |

**Nhận xét:** p99 tăng từ 224.8 lên 1696.7 ms khi slow rate 3%, p95 vẫn 232.0 ms. Ở 10%, p95 tăng 1685.9 ms và FAIL dù avg chỉ 329.6 ms. p99 nhạy với tail latency, p95 phản ánh slow request khi tỷ lệ đủ lớn. Mỗi lần restart v2, 300 requests, concurrency 20, các tham số khác giữ mặc định như trên.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100.0% (23/23) |
| Avg tokens / câu | 56.9 | 109.1 | 114.5 |
| Tổng cost (USD) | 0.000402 | 0.000762 | 0.000798 |
| Cost / câu đúng (USD) | 0.00040155 | 0.00003627 | 0.00003469 |
| Quality gate | FAIL | PASS | PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu JWT và so sánh API key. |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu Kubernetes HPA với 3 nhóm chỉ số. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

Retrieval tăng token và tổng chi phí nhưng tăng accuracy từ 1/23 lên 21/23 rồi 23/23. Cost/câu đúng giảm rõ rệt, phản ánh chi phí tạo kết quả hữu ích tốt hơn cost/câu. p95 eval v1/v2/fixed lần lượt 182.7/222.2/218.3 ms; chỉ 23 câu, không đủ mẫu kết luận hiệu năng. Chi phí đều mô phỏng. Keyword gate chỉ đo coverage bộ 23 câu; sửa KB theo bộ này không chứng minh tổng quát hóa. Không sửa golden_dataset.jsonl hay script eval.

**CI quality gate:** sau khi khởi động agent v2 candidate trong CI, chạy python eval/run_eval.py --url http://localhost:8002 --min-accuracy 1.0 --baseline reports/eval_v2.json --out reports/eval_v2_fixed.json (từ develop/). Script exit 1 nếu accuracy dưới ngưỡng hoặc câu baseline đúng thành sai; đặt required status check cho branch main để chặn merge, không dùng continue-on-error. Exit 0 cho phép bước tiếp theo. Baseline phải là artifact phiên bản đã duyệt, không tự ghi đè.

---

## 4. Observability stack (production)

Project Compose: k5-day14-observability. Sửa home user agent trong Dockerfile thành /home/agent và ENV HOME tương ứng do bản mẫu báo ModuleNotFoundError: uvicorn. Build lại thành công, /health và /ask HTTP 200, X-Trace-ID và X-Served-By có mặt, Nginx /metrics 404. promtool check rules: SUCCESS 4 rules; promtool test rules: SUCCESS.

### 4.1 Screenshot

- [x] [Grafana Golden Signals khi có tải](screenshots/grafana-dashboard.png).
- [x] [Jaeger slow trace](screenshots/jaeger-slow-trace.png).
- [x] [Jaeger error trace có event exception](screenshots/jaeger-error-trace.png).
- [x] [Prometheus: 3 alert đồng thời firing](screenshots/prometheus-alert-firing.png).

Ảnh chụp trực tiếp giao diện bằng Edge headless, không dựng ảnh.

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi đến khi quan sát firing | Panel rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | AgentHighErrorRate | 92.2 s | Error rate /ask |
| B | `MOCK_SLOW_RATE=0.3` | AgentHighLatencyP95 | 147.4 s | Latency p95/p99 |
| C | `LLM_MODEL=mock-llm-large` | LLMCostBurnRateHigh | 178.3 s | Cost burn rate USD/giờ |
| D | `docker pause` 1 instance | AgentInstanceDown | 45.2 s | Instances up: 3 → 2 |
| E | `AGENT_VERSION=v1` | Không firing tại thời điểm kiểm tra | Quan sát sau 55.0 s | Phiên bản đang chạy / retrieval hit ratio |

A–C chạy kết hợp trên 3 replicas với 30 users, spawn 5/s, 5 phút để quan sát đồng thời; không phải ba thử nghiệm cô lập. Thời gian tính từ lúc đổi cấu hình đến lần polling đầu thấy firing, bao gồm thời gian recreate container và độ trễ scrape/evaluation. Nguồn [alert observations](benchmark-results/fault-alert-observations.json). Khi 3 alert cùng firing, error rate 20.35%, p95 1.943 s, burn rate mô phỏng $11.56/giờ. Locust /ask 849/4109 lỗi 503 (20.66%).

D: [JSON](benchmark-results/fault-d-observation.json), [ảnh alert](benchmark-results/fault-d-alert.png), [dashboard](benchmark-results/fault-d-dashboard.png). Locust ghi 27 lỗi 504 và 15 lỗi 503; Grafana agent error rate tại thời điểm chụp chỉ 0.94%, vì lỗi gateway không nhất thiết được đếm ở agent. Pause giữ target DNS nhưng scrape thất bại; stop có thể loại target khỏi DNS. Đã unpause.

E: [JSON](benchmark-results/fault-e-observation.json), [ảnh alert](benchmark-results/fault-e-alert.png), [dashboard](benchmark-results/fault-e-dashboard.png). Cả 3 agent_info báo v1, Grafana error rate 0.70%, p95 198.62 ms, 4 alert inactive. Đây là quan sát trong thử nghiệm 90 giây, không chứng minh mọi thời điểm đều không có alert. Đã khôi phục v2/model nhỏ/slow 0.03/error 0.01.

**Phát hiện regression chất lượng:** theo dõi eval định kỳ trên golden dataset, quality gate CI/CD trước deploy, đánh giá mẫu câu trả lời thật, retrieval hit ratio và feedback người dùng. CP7 cho thấy v1 chỉ 1/23 đúng; hạ tầng xanh không đồng nghĩa câu trả lời đúng.

### 4.3 Debug bằng trace

Trace chậm nhất trong mẫu trace có log khớp lúc truy vấn (không khẳng định toàn bộ lịch sử):
- Trace ID: `e59a77510da63909a7f97225760a89db`
- Tổng thời gian: 2009.83 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-large` (1986.70 ms, 98.85%)
- Dòng log tương ứng:

```json
{"ts": "2026-11-25T09:44:36.334631+00:00", "level": "INFO", "service": "observable-agent", "instance": "56ca7d6f7770", "event": "llm_call", "trace_id": "e59a77510da63909a7f97225760a89db", "span_id": "e69fbd5f21f57e5b", "request_id": "146f5c0be2b4", "model": "mock-llm-large", "agent_version": "v2", "input_tokens": 74, "output_tokens": 37, "cost_usd": 0.000555, "llm_ms": 1985.8}
```

Trace lỗi: `504db7a0c03c5f9e73357fe8fd1dddff`, HTTP 503, tổng 955.79 ms, span chat 929.78 ms; event exception.type=utils.mock_llm.LLMError, exception.message=Upstream LLM error: 503 Service Unavailable (mock). Dòng log khớp:

```json
{"ts": "2026-11-25T09:44:33.461930+00:00", "level": "INFO", "service": "observable-agent", "instance": "56ca7d6f7770", "event": "llm_error", "trace_id": "504db7a0c03c5f9e73357fe8fd1dddff", "span_id": "b0da9187d737bb5d", "request_id": "4b692f39236a", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

Nguồn: [slow evidence](benchmark-results/jaeger-slow-evidence.json), [error evidence](benchmark-results/jaeger-error-evidence.json).

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 66.36 | 190 | 230 | 1700 | 63 |
| 3 | 66.00 | 190 | 220 | 1700 | 58 |

Dùng dòng Aggregated (bao gồm /ask và /health), nguồn [1 replica](benchmark-results/scale_1_stats.csv), [3 replicas](benchmark-results/scale_3_stats.csv). Tương ứng 7911 và 7869 requests; error rate 0.80% và 0.74%. Cả hai Locust exit 1 vì có lỗi 503 mô phỏng, không phải benchmark không chạy.

**Giải thích:** p95 giảm nhẹ 230→220 ms, p99 vẫn 1700 ms, RPS gần như không đổi. Workload 100 users với think time 0.5–2 s và độ trễ LLM mô phỏng nên 1 instance đã đáp ứng mức tải này; tăng instance không loại bỏ tail latency của LLM. Không đủ dữ liệu để khẳng định bottleneck CPU/network; cần tăng tải và profiling.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. p95/p99 phát hiện tail latency bị average che khuất.
  2. Throughput không nhất thiết tăng khi concurrency tăng; cần load test nhiều mức.
  3. Retrieval nâng chất lượng và giảm cost/câu đúng; quality gate ngăn regression.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Theo dõi p99, error budget burn rate, queue wait và CPU/memory để phân biệt bottleneck. Thêm synthetic check và metric 5xx/504 từ Nginx, kiểm tra chất lượng định kỳ; liên kết dashboard → trace → JSON log và sampling có ưu tiên lỗi/slow trace.
