# Nghiên cứu Khoa học Sinh viên: Gián đoạn Vận tải Biển Đỏ & Thương mại Hàng hóa Việt Nam - EU (2022–2024)

Dự án phân tích định lượng tác động của cú sốc tuyến Biển Đỏ – Suez đến kim ngạch và khối lượng nhập khẩu hàng hóa có xuất xứ Việt Nam vào Liên minh Châu Âu (EU27), đối chiếu với các thị trường so sánh (New Zealand, Nhật Bản).

---

## 📌 1. Cấu trúc Kho lưu trữ (Repository Structure)

```text
├── README.md                                       # Tài liệu hướng dẫn tổng quan và tái lập
├── .gitignore                                      # Loại bỏ file rác và file zip thô quá lớn
├── analysis.do                                     # Do-file Stata chạy hồi quy (reghdfe & ppmlhdfe)
│
├── common_hs4_eu_japan_newzealand_2022.csv         # Danh mục 509 mã HS4 cố định (chọn năm 2022)
├── eu27_hs4_by_country_2022.csv                    # Dữ liệu xuất hiện dương tại EU27 năm 2022
├── japan_hs4_from_official_csv_2022.csv            # Dữ liệu xuất hiện dương tại Nhật Bản năm 2022
├── newzealand_hs4_from_vietnam_2022.csv            # Dữ liệu xuất hiện dương tại New Zealand 2022
├── data-demo.xlsx                                  # Bản thiết kế cấu trúc panel mẫu
├── De cuong chi tiet NCKH sinh vien Giai doan van tai Bien Do.docx # Đề cương chi tiết
│
├── scripts/                                        # Pipeline Python thu thập và làm sạch tự động
│   ├── 01_download_ecb_exchange_rates.py           # Tải chuỗi tỷ giá tham chiếu ECB (JPY, NZD -> EUR)
│   ├── 02_process_stats_nz.py                      # Tải và xử lý số liệu Stats NZ (2022-2024)
│   ├── 03_download_eurostat_comext.py              # Kéo tự động dữ liệu Eurostat Comext DS-059334
│   ├── 04_build_master_panel.py                    # Hợp nhất bảng Panel, tính S1, S2, Post, in_sample
│   └── 05_generate_audit_reports.py                # Sinh bảng kiểm tra phục vụ nghiệm thu
│
├── manifests/                                      # Audit Trail: Chứng minh tính toàn vẹn dữ liệu
│   ├── manifest_eurostat.json                      # Ghi URL, timestamp, SHA-256 từng batch Eurostat
│   └── manifest_nz.json                            # Ghi URL, timestamp, SHA-256 từng file Stats NZ
│
├── processed_data/                                 # DỮ LIỆU ĐÃ LÀM SẠCH (READY FOR ANALYSIS)
│   ├── master_panel_stata.dta                      # File dữ liệu Stata hoàn chỉnh (217.249 dòng)
│   ├── master_panel.xlsx                           # File Excel bảng Panel & Bảng S1, S2
│   ├── master_panel.csv                            # File CSV bảng Panel đầy đủ
│   ├── HS4_2022_characteristics.csv                # Bảng giá trị S1 (share sea) & S2 (ln kg/EUR) 2022
│   ├── audit_table_by_market.csv                   # Bảng kiểm số quan sát, số mã theo thị trường
│   ├── audit_table_by_month.csv                    # Bảng kiểm diễn biến 36 tháng
│   └── audit_summary.json                          # Tóm tắt số liệu kiểm toán
│
└── raw_data/                                       # Dữ liệu thô tải từ các cổng thống kê chính thức
    ├── ecb/                                        # Tỷ giá gốc ECB
    ├── eurostat/                                   # 34 batch raw CSV từ Eurostat
    └── new_zealand/                                # 3 file zip gốc từ Stats NZ
```

---

## 📊 2. Quy ước Biến số trong Dataset (`master_panel_stata.dta`)

Được chuẩn hóa nghiêm ngặt theo chỉ dẫn của Giảng viên hướng dẫn:

| Tên biến | Kiểu | Ý nghĩa và Công thức tính |
| :--- | :---: | :--- |
| `HS4` | String | Mã HS 4 chữ số (chuỗi 4 ký tự, giữ số 0 đầu: `'0303'`, `'0901'`...). |
| `Market` | String | Tên thị trường nhập khẩu (từng nước trong EU27, EU27 (Total), New Zealand). |
| `Group` | String | Nhóm thị trường: `'EU'` hoặc `'Comparison'`. |
| `Year`, `Month` | Integer | Năm (2022–2024) và Tháng (1–12), tổng cộng 36 tháng. |
| `EU` | 0/1 | Biến chỉ thị: `= 1` nếu là thị trường EU, `= 0` nếu là thị trường đối chứng. |
| `Post` | 0/1 | Biến thời kỳ: `= 0` (1/2022–10/2023), `= 1` (1/2024–12/2024). |
| `Excl_1112_2023`| 0/1 | Cửa sổ làm sạch: `= 1` với tháng 11 và 12/2023 (loại khỏi mẫu hồi quy chính). |
| `Status` | String | Trạng thái ô: `positive` (có số dương), `reported_zero` (nguồn báo 0). **Không tự ý gán 0 cho ô vắng**. |
| `CIF_EUR` | Float | Giá trị CIF tính bằng EUR (NZD được đổi bằng tỷ giá trung bình tháng ECB). |
| `KG` | Float | Khối lượng hàng hóa (kg). |
| `Currency_goc`| String | Đơn vị tiền tệ gốc của hải quan sở tại (`EUR`, `NZD`, `JPY`). |
| `S1_sea_2022` | Float | Tỷ trọng giá trị nhập khẩu bằng đường biển tại biên giới EU năm 2022 của mã HS4. |
| `S2_lnkgeur_2022`| Float | $\ln(\text{tổng kg 2022} / \text{tổng CIF EUR 2022})$ của mã HS4. |
| `ln_CIF` | Float | $\ln(\text{CIF\_EUR})$ cho các ô có giá trị CIF dương. |
| `in_sample` | 0/1 | `= 1` khi `Excl_1112_2023 == 0` và `Status == 'positive'`. Mẫu sạch cho hồi quy. |
| `EUxPostxS1` | Float | Tương tác chính: $\text{EU} \times \text{Post} \times S_1$. |
| `EUxPostxS2` | Float | Tương tác chính: $\text{EU} \times \text{Post} \times S_2$. |
| `kg_per_EUR_obs`| Float | $\text{KG} / \text{CIF\_EUR}$ (nghịch đảo của đơn giá EUR/kg). |

---

## 🔬 3. Hướng dẫn chạy Hồi quy trên Stata

Bạn chỉ cần mở Stata, điều hướng đến thư mục dự án và chạy `analysis.do`:

```stata
cd "processed_data"
use "master_panel_stata.dta", clear

* Khai báo panel (Sản phẩm x Thị trường x Tháng)
egen panel_id = group(HS4 Market)
gen time_id = ym(Year, Month)
format time_id %tm
xtset panel_id time_id

* 1. Hồi quy chính với S1 (Tỷ trọng đường biển) trên mẫu sạch:
reghdfe ln_CIF EUxPostxS1 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)

* 2. Hồi quy chính với S2 (ln kg/EUR) trên mẫu sạch:
reghdfe ln_CIF EUxPostxS2 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)

* 3. Hồi quy đồng thời cả S1 và S2:
reghdfe ln_CIF EUxPostxS1 EUxPostxS2 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)

* 4. Kiểm tra độ nhạy với mô hình PPML (nếu có ppmlhdfe):
ppmlhdfe CIF_EUR EUxPostxS1 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
```

---

## 📈 4. Bảng kiểm Tra cứu & Nghiệm thu (Audit Summary)

Dữ liệu trích từ file `processed_data/audit_table_by_market.csv`:
* **Tổng số dòng panel**: 217.249 dòng
* **Mẫu hồi quy sạch (`in_sample == 1`)**: 205.056 dòng
* **Số lượng mã HS4 phân tích**: 509 mã
* **Thời gian**: 36 tháng liên tục (01/2022 – 12/2024)
* **Quy tắc phân định**:
  * Các ô `not_published` (ô trống) không bị điền số 0 tự tiện.
  * Toàn bộ mã băm SHA-256 của từng file thô được lưu trong `manifests/manifest_eurostat.json` và `manifests/manifest_nz.json`.
