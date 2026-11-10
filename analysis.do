********************************************************************************
* ĐỀ TÀI NCKH: GIÁN ĐOẠN VẬN TẢI BIỂN ĐỎ VÀ THƯƠNG MẠI VIỆT NAM - EU (2022-2024)
* DO-FILE HỒI QUY CHÍNH VÀ KIỂM TRA ĐỘ NHẠY TRÊN STATA
********************************************************************************

clear all
set more off
cap log close

* 1. Cấu hình đường dẫn thư mục
* Hãy thay đổi đường dẫn này theo máy tính của bạn nếu cần:
cd "processed_data"

* 2. Nạp dữ liệu Master Panel
use "master_panel_stata.dta", clear

describe
summarize

* 3. Khai báo cấu trúc Panel (Sản phẩm x Thị trường x Tháng)
egen panel_id = group(HS4 Market)
gen time_id = ym(Year, Month)
format time_id %tm
xtset panel_id time_id

* 4. Thống kê mô tả rổ hàng
tab Market Group if Year == 2022 & Month == 1
tab Year Post

* 5. MÔ HÌNH HỒI QUY CHÍNH (BASELINE DDD WITH REGHDFE)
* Mẫu sạch: in_sample == 1 (đã loại trừ 2 tháng quá độ 11-12/2023)

* (A) Mô hình với S1 (Tỷ trọng đường biển tại biên giới EU năm 2022)
* Cố định hiệu ứng sản phẩm-thị trường (panel_id) và hiệu ứng thời gian (time_id)
reghdfe ln_CIF EUxPostxS1 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
eststo m1_s1

* (B) Mô hình với S2 (ln kg/EUR năm 2022)
reghdfe ln_CIF EUxPostxS2 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
eststo m2_s2

* (C) Mô hình đồng thời cả S1 và S2
reghdfe ln_CIF EUxPostxS1 EUxPostxS2 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
eststo m3_s1_s2

* 6. KIỂM TRA ĐỘ NHẠY VỚI BIẾN KẾT QUẢ KHỐI LƯỢNG (KG)
gen ln_KG = ln(KG) if KG > 0 & in_sample == 1
reghdfe ln_KG EUxPostxS1 if in_sample == 1 & !missing(ln_KG), absorb(panel_id time_id) cluster(panel_id)
eststo m4_kg_s1

* 7. MÔ HÌNH PPML (NẾU ĐÃ CÀI ĐẶT LỆNH ppmlhdfe)
* net install ppmlhdfe, from("https://raw.githubusercontent.com/sergiocorreia/ppmlhdfe/master/src/")
cap which ppmlhdfe
if _rc == 0 {
    ppmlhdfe CIF_EUR EUxPostxS1 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
    eststo m5_ppml_s1
}

* 8. Xuất bảng kết quả tóm tắt
esttab m1_s1 m2_s2 m3_s1_s2 m4_kg_s1, b(%9.4f) se(%9.4f) star(* 0.10 ** 0.05 *** 0.01) title("Ket qua hoi quy tham do Red Sea Shock")
