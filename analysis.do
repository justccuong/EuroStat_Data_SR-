********************************************************************************
* ĐỀ TÀI NCKH: GIÁN ĐOẠN VẬN TẢI BIỂN ĐỎ VÀ THƯƠNG MẠI VIỆT NAM - EU (2022-2024)
* DO-FILE HỒI QUY CHÍNH VÀ KIỂM TRA ĐỘ NHẠY TRÊN STATA
* Tuân thủ hướng dẫn đề cương chi tiết của Giảng viên hướng dẫn
********************************************************************************

clear all
set more off
cap log close

* 1. Nạp dữ liệu Master Panel (Tự động thích ứng thư mục hiện hành)
cap use "processed_data/master_panel_stata.dta", clear
if _rc != 0 {
    cap use "master_panel_stata.dta", clear
}

describe
summarize

* 2. Khai báo cấu trúc Panel (Sản phẩm HS4 x Thị trường x Tháng)
egen panel_id = group(HS4 Market)
gen time_id = ym(Year, Month)
format time_id %tm
xtset panel_id time_id

* 3. Thống kê mô tả rổ hàng và mẫu nghiên cứu
tab Market Group if Year == 2022 & Month == 1
tab Year Post
tab Status in_sample

* 4. MÔ HÌNH HỒI QUY CHÍNH (BASELINE DDD WITH REGHDFE)
* Mẫu sạch: in_sample == 1 (đã loại trừ 2 tháng quá độ 11-12/2023)
* Cụm sai số chuẩn (cluster) theo cặp Sản phẩm - Thị trường (panel_id)

* (A) Đặc tả cơ sở: Cố định hiệu ứng Sản phẩm - Thị trường (panel_id) và Thời gian (time_id)
* Mô hình với S1 (Tỷ trọng đường biển tại biên giới EU năm 2022)
reghdfe ln_CIF EUxPostxS1 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
eststo m1_s1

* Mô hình với S2 (ln kg/EUR năm 2022)
reghdfe ln_CIF EUxPostxS2 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
eststo m2_s2

* Mô hình đồng thời cả S1 và S2
reghdfe ln_CIF EUxPostxS1 EUxPostxS2 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
eststo m3_s1_s2

* (B) Đặc tả kiểm soát ngặt nghèo (High-dimensional multi-way FE theo Mục 5.2 đề cương):
* Cố định hiệu ứng HS4 x Market, HS4 x time_id, và Market x time_id
* reghdfe ln_CIF EUxPostxS1 if in_sample == 1, absorb(HS4#Market HS4#time_id Market#time_id) cluster(panel_id)
* eststo m_fe_strict

* 5. KIỂM TRA ĐỘ NHẠY VỚI BIẾN KẾT QUẢ KHỐI LƯỢNG (KG)
gen ln_KG = ln(KG) if KG > 0 & in_sample == 1
reghdfe ln_KG EUxPostxS1 if in_sample == 1 & !missing(ln_KG), absorb(panel_id time_id) cluster(panel_id)
eststo m4_kg_s1

* 6. KIỂM ĐỊNH GIẢ DƯỢC TRƯỚC SỰ KIỆN (PRE-SHOCK PLACEBO TEST TRONG NĂM 2022-2023)
* Mục tiêu: Kiểm tra xem xu hướng trước cú sốc có song song/ổn định hay không
* Giả định cú sốc giả nổ ra vào tháng 6/2023 trong giai đoạn tiền sự kiện (1/2022 - 10/2023)
gen fake_post_2023 = (Year == 2023 & Month >= 6 & Month <= 10) if Year == 2022 | (Year == 2023 & Month <= 10)
gen EUxfakePostxS1 = EU * fake_post_2023 * S1_sea_2022
reghdfe ln_CIF EUxfakePostxS1 if (Year == 2022 | (Year == 2023 & Month <= 10)) & Status == "positive", absorb(panel_id time_id) cluster(panel_id)
eststo m5_placebo_s1

* 7. MÔ HÌNH PPML TRÊN Ô DƯƠNG (NẾU ĐÃ CÀI ĐẶT LỆNH ppmlhdfe)
* Cài đặt lệnh nếu chưa có: ssc install ppmlhdfe
cap which ppmlhdfe
if _rc == 0 {
    ppmlhdfe CIF_EUR EUxPostxS1 if in_sample == 1, absorb(panel_id time_id) cluster(panel_id)
    eststo m6_ppml_s1
}

* 8. Xuất bảng tổng hợp kết quả
esttab m1_s1 m2_s2 m3_s1_s2 m4_kg_s1 m5_placebo_s1, b(%9.4f) se(%9.4f) star(* 0.10 ** 0.05 *** 0.01) title("Ket qua hoi quy tham do Red Sea Shock (Stata)")
