import streamlit as st
import pandas as pd
import io
import zipfile
import re

st.set_page_config(page_title="Cetak TUL VI-01 PLN ULP Tulung", layout="wide")

st.title("⚡ Aplikasi Cetak TUL VI-01 (Presisi & Rata Kanan)")
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
        "Epson LQ-2190 (Standar Blangko 15 CPI - ESC g)",
        "Epson LX-310 / LX-300+II (9-Pin Condensed 17 CPI)",
        "Epson LX-310 / LX-300+II (9-Pin Elite 12 CPI)"
    ],
    help="Jika memakai kertas blangko lama, SELALU pilih opsi LQ-2190 meskipun printer fisiknya LX-310."
)

st.sidebar.header("📐 2. Kalibrasi Posisi Kertas (Global)")
geser_kanan = st.sidebar.number_input("Geser Kanan/Kiri Semua Teks (Spasi):", min_value=-15, max_value=30, value=0)
geser_bawah = st.sidebar.number_input("Geser Turun/Naik Semua Teks (Baris):", min_value=-5, max_value=10, value=0)
tinggi_halaman = st.sidebar.number_input("Jumlah Baris per Lembar:", min_value=30, max_value=66, value=44)

st.sidebar.header("✍️ 3. Pengaturan Tanda Tangan")
cetak_kota_jabatan = st.sidebar.checkbox("Cetak tulisan Kota (TULUNG,) & Jabatan (MANAGER)", value=False)
geser_tgl = st.sidebar.number_input("Geser Kiri/Kanan KHUSUS Tanggal (Spasi):", min_value=-30, max_value=30, value=8)

kota_cetak = st.sidebar.text_input("Kota", value="TULUNG")
tgl_cetak = st.sidebar.text_input("Tanggal Cetak", value="05-10-2026")
jabatan = st.sidebar.text_input("Jabatan", value="MANAGER")
nama_manager = st.sidebar.text_input("Nama Manager (Dicetak Tebal)", value="MARTONO AJI PRABOWO")


# ================= 2. FUNGSI EKSTRAKSI DATA DARI .ICONPRN =================
def tentukan_petugas(idpel, tarif_daya, kddk):
    daya = 0
    match_daya = re.search(r'/(\d+)', str(tarif_daya))
    if match_daya: daya = int(match_daya.group(1))
    if daya > 33000: return "PLN"
    
    idpel_khusus = {
        "524051069054": "c28", "524051263717": "c36", "524051265123": "c36", 
        "524051104194": "c04", "524051000615": "c08", "524050867033": "c08"
    }
    if str(idpel) in idpel_khusus: return idpel_khusus[str(idpel)]
        
    if len(str(kddk)) >= 6:
        kode_mid = str(kddk)[3:6].upper()
        mapping_kddk = {
            "JCA": "c01", "TAA": "c02", "JCB": "c03", "JCC": "c04", "NCD": "c05",
            "KBA": "c06", "TAB": "c07", "JCE": "c08", "TAC": "c09", "MBB": "c10",
            "KAD": "c11", "TAE": "c12", "KCF": "c13", "JCG": "c14", "TAF": "c15",
            "KAG": "c16", "BBC": "c17", "TAH": "c18", "BCK": "c19", "NCH": "c20",
            "JBE": "c21", "MBF": "c22", "MBG": "c23", "KBH": "c24", "KBI": "c25",
            "KAI": "c26", "MCI": "c27", "KBJ": "c28", "JCJ": "c29", "TAJ": "c30",
            "MBK": "c31", "KBL": "c32", "TAK": "c33", "KAL": "c34", "JCL": "c35",
            "MBD": "c36", "KCJ": "c29", "NBJ": "c28", "TAI": "c26", "BBD": "c19",
            "KCG": "c29", "MBM": "c23"
        }
        return mapping_kddk.get(kode_mid, "BARU")
    return "BARU"

def baca_data_dari_iconprn(teks_mentah):
    hasil = []
    blok_halaman = re.split(r'PEMBERITAHUAN PELAKSANAAN PEMUTUSAN', teks_mentah)
    for blok in blok_halaman:
        if "ID. Pelanggan" not in blok: continue
        
        data = {
            'IDPEL': "", 'Nomor TUL': "", 'Nama': "", 'KDDK': "", 'Gardu/Tiang': "", 
            'Loket': "", 'Alamat': "", 'Nomor Meter': "", 'Tarif/Daya': "", 'Kelompok': "", 
            'Bulan Rekening': "", 'Bulan Keterlambatan': "", 'Jumlah Rekening': 0, 
            'Jumlah Denda': 0, 'Jumlah Tunggakan': 0, 'petugas': ""
        }
        
        idpel = re.search(r'ID\. Pelanggan\s*:\s*[^0-9]*(\d{11,13})', blok)
        if idpel: data['IDPEL'] = str(idpel.group(1).strip())

        tul = re.search(r'NO\. TUL\s*:\s*([A-Z0-9/\-]+)', blok)
        if tul: data['Nomor TUL'] = tul.group(1).strip()

        nama = re.search(r'Nama\s*:\s*(.+)', blok)
        if nama: data['Nama'] = nama.group(1).strip()

        kddk = re.search(r'Kode Kedudukan\s*:\s*([A-Z0-9]+)', blok)
        if kddk: data['KDDK'] = kddk.group(1).strip()

        gardu = re.search(r'Gardu\s*/?\s*Tiang\s*:\s*(.*?)(?=\s{2,}|\s+Loket\s*:|\n|\r|$)', blok, re.IGNORECASE)
        if gardu: data['Gardu/Tiang'] = gardu.group(1).strip()

        loket = re.search(r'Loket\s*:\s*(.*?)(?=\s{2,}|\s+Tarip|\s+Tarif|\s+Alamat|\s+Kelompok|\n|\r|$)', blok, re.IGNORECASE)
        if loket: 
            val_loket = loket.group(1).strip()
            if "Tarip" in val_loket or "Kelompok" in val_loket or "Daya" in val_loket: val_loket = ""
            data['Loket'] = val_loket

        alamat = re.search(r'Alamat\s*:\s*(.+)', blok)
        if alamat: data['Alamat'] = alamat.group(1).strip()

        meter = re.search(r'Nomor Meter\s*:\s*([A-Z0-9]+)', blok, re.IGNORECASE)
        if meter: data['Nomor Meter'] = str(meter.group(1).strip())

        tarif_match = re.search(r'Tarip / Daya\s*:\s*(.+?)\s+Kelompok\s*:\s*([^\n]+)', blok)
        if tarif_match:
            data['Tarif/Daya'] = tarif_match.group(1).strip()
            data['Kelompok'] = tarif_match.group(2).strip()
        else:
            tarif = re.search(r'Tarip / Daya\s*:\s*([A-Z0-9/ ]+)', blok)
            if tarif: data['Tarif/Daya'] = tarif.group(1).strip()
            data['Kelompok'] = "1"

        rek = re.search(r'Rekening\s*:\s*(.+?)\s*Rp\.\s*:\s*[^0-9]*([\d,]+)', blok)
        if rek:
            data['Bulan Rekening'] = rek.group(1).strip()
            val_rek = rek.group(2).replace(',', '').replace('.', '').strip()
            data['Jumlah Rekening'] = int(val_rek) if val_rek.isdigit() else 0

        denda = re.search(r'Jumlah Biaya Keterlambatan s\.d bulan\s*:\s*(.+?)\s*Rp\.\s*:\s*[^0-9]*([\d,]+)', blok)
        if denda:
            data['Bulan Keterlambatan'] = denda.group(1).strip()
            val_denda = denda.group(2).replace(',', '').replace('.', '').strip()
            data['Jumlah Denda'] = int(val_denda) if val_denda.isdigit() else 0

        tunggakan = re.search(r'Jumlah Tunggakan.*?Rp\.\s*:\s*[^0-9]*([\d,]+)', blok)
        if tunggakan:
            val_tung = tunggakan.group(1).replace(',', '').replace('.', '').strip()
            data['Jumlah Tunggakan'] = int(val_tung) if val_tung.isdigit() else 0

        data['petugas'] = tentukan_petugas(data['IDPEL'], data['Tarif/Daya'], data['KDDK'])
        hasil.append(data)
    return hasil

# ================= 2A. FUNGSI DETEKSI KOLOM EXCEL PINTAR =================
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
    if "LQ-2190" in printer_choice: return f"{ESC}g{ESC}0"
    elif "17 CPI" in printer_choice: return f"{ESC}P\x0f{ESC}0"
    else: return f"{ESC}M\x12{ESC}0"

def format_rupiah(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return "0"
        bersih = str(val).replace(".", "").replace(",", "").strip()
        return f"{int(float(bersih)):,}".replace(",", ".")
    except Exception:
        return str(val)

def shift_line(text, offset_x):
    if not text: return ""
    if offset_x > 0: return (" " * offset_x) + text
    elif offset_x < 0:
        leading = len(text) - len(text.lstrip(" "))
        return text[min(abs(offset_x), leading):]
    return text

def ambil_nilai(row, col_map, key, default=""):
    if col_map is None: return str(row.get(key, default)).strip()
    nama_kolom = col_map.get(key)
    if nama_kolom and nama_kolom in row and pd.notna(row[nama_kolom]):
        return str(row[nama_kolom]).strip()
    return default

def buat_isian_blangko(row, col_map, init_code, kota, tgl, jab, manager, is_cetak_kota, geser_tgl, offset_x=0, offset_y=0, page_lines=44):
    """Mencetak ISIAN DATA persis di koordinat BLANKO.iconprn dengan RUPIAH RATA KANAN"""
    ESC = "\x1b"
    BOLD_ON = f"{ESC}E"  
    BOLD_OFF = f"{ESC}F" 

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

    # FORMAT RUPIAH DIBUAT RATA KANAN (15 Karakter)
    rp_rek = format_rupiah(ambil_nilai(row, col_map, "Jumlah Rekening", "0")).rjust(15)
    rp_denda = format_rupiah(ambil_nilai(row, col_map, "Jumlah Denda", "0")).rjust(15)
    rp_total = format_rupiah(ambil_nilai(row, col_map, "Jumlah Tunggakan", "0")).rjust(15)

    raw_lines = [""] * page_lines

    def set_line(idx, content):
        target = idx + offset_y
        if 0 <= target < page_lines:
            raw_lines[target] = shift_line(content, offset_x)

    set_line(1,  f"{'':<73}{no_tul}")
    set_line(7,  f"{'':<21}{nama}")
    set_line(8,  f"{'':<21}{idpel:<58}{kddk}")         
    set_line(9,  f"{'':<21}{alamat}")
    set_line(10, f"{'':<21}{no_meter}")
    set_line(11, f"{'':<21}{gardu:<53}{loket}")        
    set_line(12, f"{'':<21}{tarif:<53}{kelompok}")     
    
    # Bulan Rekening Mepet Kiri, Rupiah Jatuh di Spasi ke-74 dan Rata Kanan
    set_line(14, f"{'':<12}{bln_rek:<62}{rp_rek}")
    set_line(15, f"{'':<39}{bln_lambat:<35}{rp_denda}")
    set_line(17, f"{'':<74}{rp_total}")
    
    str_kota = f"{kota}, " if is_cetak_kota else ""
    str_jabatan = jab if is_cetak_kota else ""
    
    posisi_tgl = max(0, 64 + geser_tgl)
    set_line(30, f"{'':<{posisi_tgl}}{str_kota}{tgl}")
    set_line(31, f"{'':<69}{str_jabatan}")
    set_line(36, f"{'':<64}{BOLD_ON}{manager}{BOLD_OFF}")

    raw_lines[0] = init_code + raw_lines[0]
    return "\r\n".join(raw_lines) + "\r\n"

def buat_blangko_dan_isi(row, col_map, init_code, kota, tgl, jab, manager, page_lines=44):
    """Mencetak Blangko + Isian sekaligus dalam 1x jalan (Rupiah Rata Kanan)"""
    ESC = "\x1b"
    BOLD_ON = f"{ESC}E"
    BOLD_OFF = f"{ESC}F"

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

    rp_rek = format_rupiah(ambil_nilai(row, col_map, "Jumlah Rekening", "0")).rjust(15)
    rp_denda = format_rupiah(ambil_nilai(row, col_map, "Jumlah Denda", "0")).rjust(15)
    rp_total = format_rupiah(ambil_nilai(row, col_map, "Jumlah Tunggakan", "0")).rjust(15)

    lines = [
        f"{init_code}PT. PLN (PERSERO) UID JAWA TENGAH DAN DIY",
        f"UP3 KLATEN                                                    NO. TUL :  {no_tul}",
        "ULP TULUNG",
        "",
        "             PEMBERITAHUAN PELAKSANAAN PEMUTUSAN SEMENTARA SAMBUNGAN TENAGA LISTRIK             ",
        "             ======================================================================             ",
        "Kepada Yth. ",
        f"Nama              :  {nama}",
        f"ID. Pelanggan     :  {idpel:<42}Kode Kedudukan : {kddk}",
        f"Alamat            :  {alamat}",
        f"Nomor Meter       :  {no_meter}",
        f"Nama Gardu/Tiang  :  {gardu:<44}Loket    : {loket}",
        f"Tarip / Daya      :  {tarif:<42}Kelompok : {kelompok}",
        "",
        f"Rekening :  {bln_rek:<55}Rp. : {rp_rek}",
        f"Jumlah Biaya Keterlambatan s.d bulan : {bln_lambat:<28}Rp. : {rp_denda}",
        "                                                                       ---------------",
        f"Jumlah Tunggakan (belum termasuk biaya Administrasi)               Rp. : {rp_total}",
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
        f"                                                                {kota}, {tgl}",
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
    lines = [
        f"{init_code}PT. PLN (PERSERO) UID JAWA TENGAH DAN DIY",
        "UP3 KLATEN                                                    NO. TUL :  ",
        "ULP TULUNG", "",
        "             PEMBERITAHUAN PELAKSANAAN PEMUTUSAN SEMENTARA SAMBUNGAN TENAGA LISTRIK             ",
        "             ======================================================================             ",
        "Kepada Yth. ",
        "Nama              :                                                  ",
        "ID. Pelanggan     :  \t\t                              Kode Kedudukan :     ",
        "Alamat            :                                                  ",
        "Nomor Meter       :                                                                ",
        "Nama Gardu/Tiang  :  \t                                      Loket    :              ",
        "Tarip / Daya      :  \t                                      Kelompok :               ", "",
        "Rekening :        \t\t\t\t                   Rp. :  ",
        "Jumlah Biaya Keterlambatan s.d bulan :                             Rp. :  ",
        "                                                                        ---------------",
        "Jumlah Tunggakan (belum termasuk biaya Administrasi)               Rp. :  ", "",
        "   Dengan ini diberitahukan dengan hormat bahwa pada hari ini aliran listrik di rumah/alamat seperti tersebut diatas   ",
        "terpaksa diputus untuk sementara karena rekening listrik belum dilunasi pada waktu yang telah ditetapkan.",
        "Penyambungan kembali akan dilakukan pada setiap hari jam kerja apabila rekening serta biaya keterlambatan dilunasi",
        "di tempat penerimaan pembayaran rekening listrik, kantor pos, atau bank yang ditunjuk oleh PLN.                       ",
        "   Apabila dalam jangka waktu 60 hari terhitung sejak dilakukan pemutusan sementara tunggakan belum dilunasi,         ",
        "maka instalasi milik PLN akan dibongkar, dan penyambungan kembali dapat dilaksanakan setelah Saudara menyelesaikan    ",
        "Biaya Penyambungan yang diperlakukan sebagai sambungan baru serta tetap diwajibkan membayar tagihan listrik           ",
        "yang belum dilunasi beserta dendanya.                     ", "",
        "UNTUK MENGHINDARI RESIKO, MOHON TIDAK TITIP PEMBAYARAN REKENING KEPADA PETUGAS", "",
        "                                                                           ",
        "                                                                               ", "",
        "|------------------------------------------------------|",
        "|       PADA WAKTU MELAKUKAN PEMBAYARAN DIMOHON        |",
        "|         MENUNJUKKAN SURAT PEMBERITAHUAN INI          |",
        "|------------------------------------------------------|",
        "                              TGL  STAND PUTUS  PELANGGAN        ", "",
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
    # MULTI-UPLOAD: Bisa nge-blok puluhan file sekaligus!
    uploaded_files = st.file_uploader(
        "📂 Upload File Data (.xlsx, .xls, .iconprn, atau .zip)", 
        type=["xlsx", "xls", "iconprn", "prn", "zip"], 
        accept_multiple_files=True
    )

    if uploaded_files:
        df = None
        col_map_final = None 
        semua_data_iconprn = []
        excel_uploaded = False

        with st.spinner("Memproses file masukan..."):
            for uploaded_file in uploaded_files:
                nama_file = uploaded_file.name.lower()
                
                # Cek jika ada Excel
                if nama_file.endswith(('.xlsx', '.xls')):
                    excel_uploaded = True
                # Ekstrak file ZIP
                elif nama_file.endswith('.zip'):
                    with zipfile.ZipFile(uploaded_file, 'r') as z:
                        for z_name in z.namelist():
                            if z_name.lower().endswith(('.iconprn', '.prn', '.txt')):
                                teks_mentah = z.read(z_name).decode('latin1', errors='ignore')
                                semua_data_iconprn.extend(baca_data_dari_iconprn(teks_mentah))
                # Ekstrak file ICONPRN lepas
                else:
                    teks_mentah = uploaded_file.getvalue().decode('latin1', errors='ignore')
                    semua_data_iconprn.extend(baca_data_dari_iconprn(teks_mentah))
                    
        # Logika jika yang di-upload berupa Excel
        if excel_uploaded:
            file_excel = next(f for f in uploaded_files if f.name.lower().endswith(('.xlsx', '.xls')))
            xls = pd.ExcelFile(file_excel)
            pilih_sheet = st.selectbox("Pilih Sheet Excel:", xls.sheet_names) if len(xls.sheet_names) > 1 else xls.sheet_names[0]
            df_excel = pd.read_excel(file_excel, sheet_name=pilih_sheet)
            
            auto_map = deteksi_kolom_otomatis(df_excel.columns.tolist())
            kolom_hilang = [k for k, v in auto_map.items() if v is None]

            # MENU PENCOCOKAN KOLOM DIKEMBALIKAN!
            with st.expander("🔗 Pengaturan Pencocokan Kolom Excel", expanded=len(kolom_hilang) > 0):
                if kolom_hilang:
                    st.warning(f"⚠️ Ada nama kolom yang berbeda: **{', '.join(kolom_hilang)}**. Silakan pilih manual:")
                else:
                    st.success("✅ Semua kolom Excel otomatis dikenali!")

                opsi_kolom = ["(Kosongkan)"] + df_excel.columns.tolist()
                col_map_final = {}
                cols_ui = st.columns(4)
                for idx, (field_blangko, terdeteksi) in enumerate(auto_map.items()):
                    with cols_ui[idx % 4]:
                        idx_default = opsi_kolom.index(terdeteksi) if terdeteksi in opsi_kolom else 0
                        col_map_final[field_blangko] = st.selectbox(f"Isian [{field_blangko}]:", opsi_kolom, index=idx_default)
                        if col_map_final[field_blangko] == "(Kosongkan)": col_map_final[field_blangko] = None
            df = df_excel

        # Logika jika hanya ICONPRN / ZIP yang di-upload
        else:
            if semua_data_iconprn:
                df = pd.DataFrame(semua_data_iconprn)
                
        # --- PROSES LANJUTAN UNTUK CETAK ---
        if df is not None and len(df) > 0:
            st.success(f"✅ Berhasil memuat {len(df)} tagihan pelanggan!")
            
            kol_petugas = col_map_final.get("petugas") if col_map_final else "petugas"
            
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
                        hasil_iconprn += buat_isian_blangko(baris, col_map_final, init_esc, kota_cetak, tgl_cetak, jabatan, nama_manager, cetak_kota_jabatan, geser_tgl, geser_kanan, geser_bawah, tinggi_halaman)
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
                            for kode_p, grp in df_cetak.groupby(kol_petugas):
                                teks_p = ""
                                for _, r in grp.iterrows():
                                    if "Tahap 2" in mode_cetak:
                                        teks_p += buat_isian_blangko(r, col_map_final, init_esc, kota_cetak, tgl_cetak, jabatan, nama_manager, cetak_kota_jabatan, geser_tgl, geser_kanan, geser_bawah, tinggi_halaman)
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
