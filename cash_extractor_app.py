import streamlit as st
from pdf2image import convert_from_bytes
import pytesseract
import re
import pandas as pd
from io import BytesIO

# Configure Tesseract path (macOS)
pytesseract.pytesseract.tesseract_cmd = r"/usr/local/bin/tesseract"

# Extract 5-digit invoice number (with fuzzy prefix handling)
def extract_invoice_number(text):
    match = re.search(r"(bill|bil)[^\w]{0,3}[#hA]?[a-z]?\d{5}", text)
    if match:
        number = re.findall(r"[a-z]?\d{5}", match.group())
        return number[0] if number else ''
    else:
        return ''

# Extract Talipapa fields
def extract_talipapa_fields(text):
    fields = {}
    cleaned = re.sub(r"\s+", " ", text).lower()

    # Date
    date_match = re.search(r"\b(\d{2}[-/]\d{2}[-/]\d{4})\b", cleaned)
    fields['Date'] = date_match.group(1) if date_match else ''

    # Invoice Number
    fields['Invoice Number'] = extract_invoice_number(cleaned)

    # Amount
    amount_match = re.search(r"cash\s*out?\s*[-:]?\s*-?([0-9]+\.\d{2})", cleaned)
    fields['Amount'] = f"-{amount_match.group(1)}" if amount_match else ''

    # Remarks
    remarks_match = re.search(r"remarks\s*[:\-]?\s*([a-z0-9 ,.\-]{5,30})", cleaned)
    fields['Remarks'] = remarks_match.group(1).strip() if remarks_match else ''

    # Status
    if '' in [fields['Date'], fields['Invoice Number'], fields['Amount'], fields['Remarks']]:
        fields['Status'] = 'Check Needed'
    else:
        fields['Status'] = 'OK'

    return fields

# OCR for uploaded PDF
def ocr_pdf(file_bytes):
    try:
        images = convert_from_bytes(file_bytes.read(), dpi=300, poppler_path="/usr/local/bin")
        full_text = ""
        for img in images:
            full_text += pytesseract.image_to_string(img)
        return full_text
    except Exception as e:
        st.error(f"❌ OCR failed: {e}")
        return ""

# Streamlit UI
st.set_page_config(page_title="Talipapa Invoice Extractor", layout="wide")
st.title("📄 Talipapa Cash Invoice Extractor")

uploaded_files = st.file_uploader("Upload one or more scanned PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    extracted_data = []
    for uploaded_file in uploaded_files:
        st.write(f"📥 Processing: {uploaded_file.name}")
        ocr_text = ocr_pdf(uploaded_file)
        fields = extract_talipapa_fields(ocr_text)
        fields['File Name'] = uploaded_file.name
        extracted_data.append(fields)

    df = pd.DataFrame(extracted_data)
    st.success("✅ Extraction complete!")
    st.dataframe(df)

    # Download Excel
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button("⬇️ Download Excel", data=buffer, file_name="talipapa_output.xlsx", mime="application/vnd.ms-excel")
