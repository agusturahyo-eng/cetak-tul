import streamlit as st
import pandas as pd
import io
import zipfile

st.set_page_config(page_title="Cetak TUL VI-01 PLN ULP Tulung", layout="wide")

st.title("⚡ Aplikasi Cetak TUL VI-01 (Super Cepat)")
st.caption("PT. PLN (PERSERO) UID JAWA TENGAH DAN DIY - UP3 KLATEN - ULP TULUNG")

# ================= 1. SIDEBAR PENGATURAN =================
st.sidebar.header("🖨️ 1. Pengaturan Cetak & Printer")

mode_cetak = st.sidebar.radio(
    "Pilih Tahap Pencetakan:",
    [
        "Tahap 2: Isi Blangko Saja (Pengganti Mail Merge)",
        "Tahap 1 & 2 Sekaligus: Blangko + Isi Data",
        "Tahap 1 Saja: Cetak Blangko Kosong"
    ],
    index=0
)

tipe_printer = st.sidebar.selectbox(
    "Pilih Printer yang Digunakan:",
    [
        "Epson LQ-2190 (Standar 15 CPI - ESC g)",
        "Epson LX-310 / LX-300+II (9-Pin Condensed 17 CPI)",
        "Epson LX-310 / LX-300+II (9-Pin Elite 12 CPI)"
    ],
    help="Pilih sesuai printer agar ukuran huruf tidak membesar/melebar."
)

st.sidebar.header("📐 2. Kalibrasi Posisi Kertas")
geser_kanan = st.sidebar.number_input("Geser Kanan/Kiri (Spasi):", min_value=-15, max_value=30, value=0)
geser_bawah = st.sidebar.number_input("Geser Turun/Naik (Baris):", min_value=-5, max_value=10, value=0)
tinggi_halaman = st.sidebar.number_input("Jumlah Baris per Lembar:", min_value=30, max_value=66, value=44)

st.sidebar.header("✍️ 3. Data Penandatangan")
kota_cetak = st.sidebar.text_input("Kota", value="TULUNG")
tgl_cetak = st.sidebar.text_input("Tanggal Cetak", value="05-10-2026")
jabatan = st.sidebar.text_input("Jabatan", value="MANAGER")
nama_manager = st.sidebar.text_input("Nama Manager", value="MARTONO AJI PRABOWO")

# ================= 2. FUNGSI DETEKSI KOLOM PINTAR =================
STANDAR_KOLOM = {
    "IDPEL": ["idpel", "id pelanggan", "id_pelanggan", "no pelanggan"],
    "Nomor TUL": ["nomor tul", "no tul", "no. tul", "nomor_tul"],
    "Nama": ["nama", "nama pelanggan", "nama_pelanggan"],
    "KDDK": ["kddk", "kode kedudukan", "kedudukan"],
    "Gardu/Tiang": ["gardu/tiang", "gardu", "nama gardu/tiang", "gardutiang", "tiang"],
    "Loket": ["loket", "kode loket"],
    "Alamat": ["alamat", "alamat pelanggan"],
    "Nomor Meter": ["nomor meter", "no meter", "nomor_meter", "nomormeter"],
    "Tarif/Daya": ["tarif/daya", "tarip / daya", "tarifdaya", "tarif", "daya"],
    "Kelompok": ["kelompok", "klp"],
    "Bulan Rekening": ["bulan rekening", "bulan_rekening", "rekening", "blth"],
    "Bulan Keterlambatan": ["bulan keterlambatan", "bulan_keterlambatan", "keterlambatan"],
    "Jumlah Rekening": ["jumlah rekening", "jumlah_rekening", "jumlah_rekening_", "rp rekening", "tagihan"],
    "Jumlah Denda": ["jumlah denda", "jumlah_denda", "jumlah_denda_", "denda", "bk", "biaya keterlambatan"],
    "Jumlah Tunggakan": ["jumlah tunggakan", "jumlah_tunggakan", "jumlah_tunggakan_", "total", "total tunggakan"],
    "petugas": ["petugas", "kode petugas", "nama petugas", "cater"]
}

def deteksi_kolom_otomatis(df_cols):
    mapping = {}
    cols_lower = {c.strip().lower(): c for c in df_cols}
    for target, kandidat_list in STANDAR_KOLOM.items():
        found = None
        for k in kandidat_list:
            if k in cols_lower:
                found = cols_lower[k]
                break
        if not found:
            for c_low, c_orig in cols_lower.items():
                if any(k in c_low for k in kandidat_list):
                    found = c_orig
                    break
        mapping[target] = found
    return mapping

# ================= 3. FUNGSI GENERATOR FILE .ICONPRN =================
def get_printer_init_code(printer_choice):
    ESC = "\x1b"
    if "LQ-2190" in printer_choice:
        return f"{ESC}g{ESC}0"         # 15 CPI (24-pin) + 1/8 inch
    elif "17 CPI" in printer_choice:
        return f"{ESC}P\x0f{ESC}0"     # 17 CPI Condensed (9-pin) + 1/8 inch
    else:
        return f"{ESC}M\x12{ESC}0"     # 12 CPI Elite (9-pin) + 1/8 inch

def format_rupiah(val):
    try:
        if pd.isna(val) or str(val).strip() == "":
            return "0"
        bersih = str(val).replace(".", "").replace(",", "").strip()
        return f"{int(float(bersih)):,}".replace(",", ".")
    except Exception:
        return str(val)

def shift_line(text, offset_x):
    if not text:
        return ""
    if offset_x > 0:
        return (" " * offset_x) + text
    elif offset_x < 0:
        leading = len(text) - len(text.lstrip(" "))
        return text[min(abs(offset_x), leading):]
    return text

def ambil_nilai(row, col_map, key, default=""):
    nama_kolom = col_map.get(key)
    if nama_kolom and nama_kolom in row and pd.notna(row[nama_kolom]):
        return str(row[nama_kolom]).strip()
    return default

def buat_isian_blangko(row, col_map, init_code, kota, tgl, jab, manager, offset_x=0, offset_y=0, page_lines=44):
    """Mencetak HANYA ISIAN DATA persis di koordinat BLANKO.iconprn"""
    # KODE BOLD DIHAPUS AGAR CETAK 1-PASS (SUPER NGEBUT)
    BOLD_ON = ""
    BOLD_OFF = ""

    no_tul = ambil_nilai(row, col_map, "Nomor TUL")
    nama = ambil_nilai(row, col_map, "Nama")[:33]
    idpel = ambil_nilai(row, col_map, "IDPEL")
    kddk = ambil_nilai(row, col_map, "KDDK")
    alamat = ambil_nilai(row, col_map, "Alamat")[:50]
    no_meter = ambil_nilai(row, col_map, "Nomor Meter")
    gardu = ambil_nilai(row, col_map, "Gardu/Tiang")
    loket = ambil_nilai(row, col_map, "Loket")
    tarif = ambil_nilai(row, col_map, "Tarif/Daya")
    kelompok = ambil_nilai(row, col_map, "Kelompok", "0")
    bln_rek = ambil_nilai(row, col_map, "Bulan Rekening")
    bln_lambat = ambil_nilai(row, col_map, "Bulan Keterlambatan")

    rp_rek = format_rupiah(ambil_nilai(row, col_map, "Jumlah Rekening", "0")).rjust(12)
    rp_denda = format_rupiah(ambil_nilai(row, col_map, "Jumlah Denda", "0")).rjust(12)
    rp_total = format_rupiah(ambil_nilai(row, col_map, "Jumlah Tunggakan", "0")).rjust(12)

    raw_lines = [""] * page_lines

    def set_line(idx, content):
        target = idx + offset_y
        if 0 <= target < page_lines:
            raw_lines[target] = shift_line(content, offset_x)

    set_line(1,  f"{'':<73}{BOLD_ON}{no_tul}{BOLD_OFF}")
    set_line(7,  f"{'':<21}{BOLD_ON}{nama}{BOLD_OFF}")
    set_line(8,  f"{'':<21}{BOLD_ON}{idpel:<57}{kddk}{BOLD_OFF}")
    set_line(9,  f"{'':<21}{BOLD_ON}{alamat}{BOLD_OFF}")
    set_line(10, f"{'':<21}{BOLD_ON}{no_meter}{BOLD_OFF}")
    set_line(11, f"{'':<21}{BOLD_ON}{gardu:<58}{loket}{BOLD_OFF}")
    set_line(12, f"{'':<21}{BOLD_ON}{tarif:<58}{kelompok}{BOLD_OFF}")
    set_line(14, f"{'':<18}{BOLD_ON}{bln_rek:<55}{rp_rek}{BOLD_OFF}")
    set_line(15, f"{'':<39}{BOLD_ON}{bln_lambat:<34}{rp_denda}{BOLD_OFF}")
    set_line(17, f"{'':<73}{BOLD_ON}{rp_total}{BOLD_OFF}")
    set_line(30, f"{'':<64}{kota}, {BOLD_ON}{tgl}{BOLD_OFF}")
    set_line(31, f"{'':<69}{jab}")
    set_line(36, f"{'':<64}{BOLD_ON}{manager}{BOLD_OFF}")

    raw_lines[0] = init_code + raw_lines[0]
    return "\r\n".join(raw_lines) + "\r\n"

def buat_blangko_dan_isi(row, col_map, init_code, kota, tgl, jab, manager, page_lines=44):
    """Mencetak Blangko + Isian sekaligus dalam 1x jalan"""
    BOLD_ON = ""
    BOLD_OFF = ""

    no_tul = ambil_nilai(row, col_map, "Nomor TUL")
    nama = ambil_nilai(row, col_map, "Nama")[:33]
    idpel = ambil_nilai(row, col_map, "IDPEL")
    kddk = ambil_nilai(row, col_map, "KDDK")
    alamat = ambil_nilai(row, col_map, "Alamat")[:50]
    no_meter = ambil_nilai(row, col_map, "Nomor Meter")
    gardu = ambil_nilai(row, col_map, "Gardu/Tiang")
    loket = ambil_nilai(row, col_map, "Loket")
    tarif = ambil_nilai(row, col_map, "Tarif/Daya")
    kelompok = ambil_nilai(row, col_map, "Kelompok", "0")
    bln_rek = ambil_nilai(row, col_map, "Bulan Rekening")
    bln_lambat = ambil_nilai(row, col_map, "Bulan Keterlambatan")

    rp_rek = format_rupiah(ambil_nilai(row, col_map, "Jumlah Rekening", "0")).rjust(12)
    rp_denda = format_rupiah(ambil_nilai(row, col_map, "Jumlah Denda", "0")).rjust(12)
    rp_total = format_rupiah(ambil_nilai(row, col_map, "Jumlah Tunggakan", "0")).rjust(12)

    lines = [
        f"{init_code}{BOLD_ON}PT. PLN (PERSERO) UID JAWA TENGAH DAN DIY{BOLD_OFF}",
        f"UP3 KLATEN                                                    NO. TUL :  {BOLD_ON}{no_tul}{BOLD_OFF}",
        "ULP TULUNG",
        "",
        "             PEMBERITAHUAN PELAKSANAAN PEMUTUSAN SEMENTARA SAMBUNGAN TENAGA LISTRIK             ",
        "             ======================================================================             ",
        "Kepada Yth. ",
        f"Nama              :  {BOLD_ON}{nama:<48}{BOLD_OFF}",
        f"ID. Pelanggan     :  {BOLD_ON}{idpel:<41}{BOLD_OFF}Kode Kedudukan : {BOLD_ON}{kddk}{BOLD_OFF}",
        f"Alamat            :  {BOLD_ON}{alamat:<48}{BOLD_OFF}",
        f"Nomor Meter       :  {BOLD_ON}{no_meter:<62}{BOLD_OFF}",
        f"Nama Gardu/Tiang  :  {BOLD_ON}{gardu:<41}{BOLD_OFF}Loket    :       {BOLD_ON}{loket}{BOLD_OFF}",
        f"Tarip / Daya      :  {BOLD_ON}{tarif:<41}{BOLD_OFF}Kelompok :       {BOLD_ON}{kelompok}{BOLD_OFF}",
        "",
        f"Rekening :        {BOLD_ON}{bln_rek:<49}{BOLD_OFF}Rp. : {BOLD_ON}{rp_rek}{BOLD_OFF}",
        f"Jumlah Biaya Keterlambatan s.d bulan : {BOLD_ON}{bln_lambat:<28}{BOLD_OFF}Rp. : {BOLD_ON}{rp_denda}{BOLD_OFF}",
        "                                                                        ---------------",
        f"Jumlah Tunggakan (belum termasuk biaya Administrasi)               Rp. : {BOLD_ON}{rp_total}{BOLD_OFF}",
        "",
        "   Dengan ini diberitahukan dengan hormat bahwa pada hari ini aliran listrik di rumah/alamat seperti tersebut diatas   ",
        "terpaksa diputus untuk sementara karena rekening listrik belum dilunasi pada waktu yang telah ditetapkan.",
        "Penyambungan kembali akan dilakukan pada setiap hari jam kerja apabila rekening serta biaya keterlambatan dilunasi",
        "di tempat penerimaan pembayaran rekening listrik, kantor pos, atau bank yang ditunjuk oleh PLN.                       ",
        "   Apabila dalam jangka waktu 60 hari terhitung sejak dilakukan pemutusan sementara tunggakan belum dilunasi,         ",
        "maka instalasi milik PLN akan dibongkar, dan penyambungan kembali dapat dilaksanakan setelah Saudara menyelesaikan    ",
        "Biaya Penyambungan yang diperlakukan sebagai sambungan baru serta tetap diwajibkan membayar tagihan listrik           ",
        "yang belum dilunasi beserta dendanya.                     ",
        "",
        "UNTUK MENGHINDARI RESIKO, MOHON TIDAK TITIP PEMBAYARAN REKENING KEPADA PETUGAS",
        "",
        f"                                                                {kota}, {BOLD_ON}{tgl}{BOLD_OFF}",
        f"                                                                     {jab}",
        "",
        "|------------------------------------------------------|",
        "|       PADA WAKTU MELAKUKAN PEMBAYARAN DIMOHON        |",
        "|         MENUNJUKKAN SURAT PEMBERITAHUAN INI          |",
        f"|------------------------------------------------------|        {BOLD_ON}{manager}{BOLD_OFF}",
        "                              TGL  STAND PUTUS  PELANGGAN        ",
        "",
        "A5 TUL VI-01/PETUGAS PEMUTUS...... ... ... ... ...........                   ",
        "ABAIKAN PEMBERITAHUAN INI JIKA SUDAH MEMBAYAR TAGIHAN"
    ]
    while len(lines) < page_lines:
        lines.append("")
    return "\r\n".join(lines[:page_lines]) + "\r\n"

def buat_blangko_kosong(init_code, jml_lembar=50, page_lines=44):
    BOLD_ON = ""
    BOLD_OFF = ""
    lines = [
        f"{init_code}{BOLD_ON}PT. PLN (PERSERO) UID JAWA TENGAH DAN DIY{BOLD_OFF}",
        "UP3 KLATEN                                                    NO. TUL :  ",
        "ULP TULUNG",
        "",
        "             PEMBERITAHUAN PELAKSANAAN PEMUTUSAN SEMENTARA SAMBUNGAN TENAGA LISTRIK             ",
        "             ======================================================================             ",
        "Kepada Yth. ",
        "Nama              :                                                  ",
        "ID. Pelanggan     :  \t\t                              Kode Kedudukan :     ",
        "Alamat            :                                                  ",
        "Nomor Meter       :                                                                ",
        "Nama Gardu/Tiang  :  \t                                      Loket    :              ",
        "Tarip / Daya      :  \t                                      Kelompok :               ",
        "",
        "Rekening :        \t\t\t\t                   Rp. :  ",
        "Jumlah Biaya Keterlambatan s.d bulan :                             Rp. :  ",
        "                                                                        ---------------",
        "Jumlah Tunggakan (belum termasuk biaya Administrasi)               Rp. :  ",
        "",
        "   Dengan ini diberitahukan dengan hormat bahwa pada hari ini aliran listrik di rumah/alamat seperti tersebut diatas   ",
        "terpaksa diputus untuk sementara karena rekening listrik belum dilunasi pada waktu yang telah ditetapkan.",
        "Penyambungan kembali akan dilakukan pada setiap hari jam kerja apabila rekening serta biaya keterlambatan dilunasi",
        "di tempat penerimaan pembayaran rekening listrik, kantor pos, atau bank yang ditunjuk oleh PLN.                       ",
        "   Apabila dalam jangka waktu 60 hari terhitung sejak dilakukan pemutusan sementara tunggakan belum dilunasi,         ",
        "maka instalasi milik PLN akan dibongkar, dan penyambungan kembali dapat dilaksanakan setelah Saudara menyelesaikan    ",
        "Biaya Penyambungan yang diperlakukan sebagai sambungan baru serta tetap diwajibkan membayar tagihan listrik           ",
        "yang belum dilunasi beserta dendanya.                     ",
        "",
        "UNTUK MENGHINDARI RESIKO, MOHON TIDAK TITIP PEMBAYARAN REKENING KEPADA PETUGAS",
        "",
        "                                                                           ",
        "                                                                               ",
        "",
        "|------------------------------------------------------|",
        "|       PADA WAKTU MELAKUKAN PEMBAYARAN DIMOHON        |",
        "|         MENUNJUKKAN SURAT PEMBERITAHUAN INI          |",
        "|------------------------------------------------------|",
        "                              TGL  STAND PUTUS  PELANGGAN        ",
        "",
        "A5 TUL VI-01/PETUGAS PEMUTUS...... ... ... ... ...........                   ",
        "ABAIKAN PEMBERITAHUAN INI JIKA SUDAH MEMBAYAR TAGIHAN"
    ]
    while len(lines) < page_lines:
        lines.append("")
    return ("\r\n".join(lines[:page_lines]) + "\r\n") * jml_lembar

# ================= 4. HALAMAN UTAMA APLIKASI =================
init_esc = get_printer_init_code(tipe_printer)

if "Tahap 1 Saja" in mode_cetak:
    st.subheader("📄 Cetak Blangko Kosong (.iconprn)")
    jml = st.number_input("Jumlah Lembar Blangko:", min_value=1, max_value=1000, value=50)
    raw_blanko = buat_blangko_kosong(init_esc, jml, tinggi_halaman)
    st.download_button(
        label=f"🖨️ Klik untuk Cetak / Download BLANKO_{jml}_LEMBAR.iconprn",
        data=raw_blanko.encode("latin1", errors="replace"),
        file_name=f"BLANKO_{jml}_LEMBAR.iconprn",
        mime="application/octet-stream"
    )
else:
    uploaded_file = st.file_uploader("📂 Upload File Excel Data Tagihan (.xlsx / .xls)", type=["xlsx", "xls"])

    if uploaded_file:
        xls = pd.ExcelFile(uploaded_file)
        pilih_sheet = st.selectbox("Pilih Sheet Excel:", xls.sheet_names) if len(xls.sheet_names) > 1 else xls.sheet_names[0]
        df = pd.read_excel(uploaded_file, sheet_name=pilih_sheet)

        auto_map = deteksi_kolom_otomatis(df.columns.tolist())
        kolom_hilang = [k for k, v in auto_map.items() if v is None]

        with st.expander("🔗 Pengaturan Pencocokan Kolom Excel (Otomatis Terhubung)", expanded=len(kolom_hilang) > 0):
            if kolom_hilang:
                st.warning(f"⚠️ Ada nama kolom di Excel yang berbeda dari biasanya: **{', '.join(kolom_hilang)}**. Silakan pilih pasangannya:")
            else:
                st.success("✅ Semua kolom Excel otomatis dikenali dan tersambung ke Blangko!")

            opsi_kolom = ["(Kosongkan)"] + df.columns.tolist()
            col_map_final = {}
            cols_ui = st.columns(4)
            for idx, (field_blangko, terdeteksi) in enumerate(auto_map.items()):
                with cols_ui[idx % 4]:
                    idx_default = opsi_kolom.index(terdeteksi) if terdeteksi in opsi_kolom else 0
                    pilihan = st.selectbox(f"Isian [{field_blangko}]:", opsi_kolom, index=idx_default)
                    col_map_final[field_blangko] = None if pilihan == "(Kosongkan)" else pilihan

        # Filter berdasarkan Petugas
        kol_petugas = col_map_final.get("petugas")
        if kol_petugas and kol_petugas in df.columns:
            df[kol_petugas] = df[kol_petugas].fillna("Tanpa_Petugas").astype(str)
            daftar_ptg = sorted(df[kol_petugas].unique().tolist())

            st.subheader("👷 Pilih Petugas & Urutan Cetak")
            c1, c2, c3 = st.columns(3)
            with c1:
                ptg_terpilih = st.multiselect("Pilih Kode Petugas:", daftar_ptg, default=[daftar_ptg[0]] if daftar_ptg else [])
            df_saring = df[df[kol_petugas].isin(ptg_terpilih)].reset_index(drop=True)
        else:
            st.subheader("📋 Rentang Urutan Cetak")
            c2, c3 = st.columns(2)
            ptg_terpilih = ["Semua"]
            df_saring = df.reset_index(drop=True)

        total_data = len(df_saring)
        with c2:
            urut_awal = st.number_input("Mulai Urutan ke-:", min_value=1, max_value=max(1, total_data), value=1)
        with c3:
            urut_akhir = st.number_input("Sampai Urutan ke-:", min_value=1, max_value=max(1, total_data), value=max(1, total_data))

        df_cetak = df_saring.iloc[urut_awal - 1 : urut_akhir]
        st.info(f"Siap mencetak **{len(df_cetak)} lembar** (Petugas: **{', '.join(ptg_terpilih)}**, Urutan {urut_awal} s/d {urut_akhir}).")
        st.dataframe(df_cetak, use_container_width=True, height=220)

        if len(df_cetak) > 0:
            hasil_iconprn = ""
            for _, baris in df_cetak.iterrows():
                if "Tahap 2" in mode_cetak:
                    hasil_iconprn += buat_isian_blangko(baris, col_map_final, init_esc, kota_cetak, tgl_cetak, jabatan, nama_manager, geser_kanan, geser_bawah, tinggi_halaman)
                else:
                    hasil_iconprn += buat_blangko_dan_isi(baris, col_map_final, init_esc, kota_cetak, tgl_cetak, jabatan, nama_manager, tinggi_halaman)

            nama_ptg_file = "_".join(ptg_terpilih)
            st.subheader("🖨️ Eksekusi Cetak ke Printer Dot Matrix")

            b1, b2 = st.columns(2)
            with b1:
                st.download_button(
                    label=f"🖨️ CETAK PETUGAS {nama_ptg_file} ({len(df_cetak)} Lbr)",
                    data=hasil_iconprn.encode("latin1", errors="replace"),
                    file_name=f"ISI_BLANGKO_{nama_ptg_file}_{urut_awal}_{urut_akhir}.iconprn",
                    mime="application/octet-stream",
                    type="primary",
                    use_container_width=True
                )
            
            with b2:
                if kol_petugas and kol_petugas in df.columns:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                        # KODE ZIP DIPERBAIKI: HANYA MENGAMBIL DARI df_cetak (YANG TAMPIL DI LAYAR SAJA)
                        for kode_p, grp in df_cetak.groupby(kol_petugas):
                            teks_p = ""
                            for _, r in grp.iterrows():
                                if "Tahap 2" in mode_cetak:
                                    teks_p += buat_isian_blangko(r, col_map_final, init_esc, kota_cetak, tgl_cetak, jabatan, nama_manager, geser_kanan, geser_bawah, tinggi_halaman)
                                else:
                                    teks_p += buat_blangko_dan_isi(r, col_map_final, init_esc, kota_cetak, tgl_cetak, jabatan, nama_manager, tinggi_halaman)
                            zf.writestr(f"PETUGAS_{kode_p}_{len(grp)}lembar.iconprn", teks_p.encode("latin1", errors="replace"))
                    
                    st.download_button(
                        label="📦 DOWNLOAD PAKET ZIP (Sesuai Tabel)",
                        data=buf.getvalue(),
                        file_name=f"PAKET_CETAK_{urut_awal}_sd_{urut_akhir}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
