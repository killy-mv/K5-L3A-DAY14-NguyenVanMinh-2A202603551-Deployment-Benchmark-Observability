# Benchmark & Observability Report — Day 14

> Copy file này thành `BENCHMARK_REPORT.md` trong repo của bạn và điền đầy đủ.
> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Nguyen Van Minh
**Ngày chạy:** 25/11/2026
**Môi trường:** Windows / Ubuntu 24.04 WSL2; AMD Ryzen 5 5600H, 12 logical CPUs, 7.5 GiB RAM khả dụng cho WSL; Python 3.12.3, Mock LLM small. CP7 local, không dùng cloud.

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

> CP8 chưa chạy; các mục bên dưới chờ số liệu và ảnh thực tế.

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

> CP8 chưa chạy; không điền số ước lượng.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

...

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. p95/p99 phát hiện tail latency bị average che khuất.
  2. Throughput không nhất thiết tăng khi concurrency tăng; cần load test nhiều mức.
  3. Retrieval nâng chất lượng và giảm cost/câu đúng; quality gate ngăn regression.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Theo dõi p99, error budget burn rate, queue wait và CPU/memory để phân biệt bottleneck. CP8 sẽ bổ sung kết luận observability thực tế.
