import streamlit as st
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
import re
from supabase import create_client, Client
from io import BytesIO
import os

# 🛠️ Poppler path (edit if installed elsewhere)
POPPLER_PATH = r"C:\poppler\Library\bin"

# 🎯 Supabase config from secrets
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "documents"

# 🔗 Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_pdf_to_supabase(file):
    try:
        result = supabase.storage.from_(BUCKET_NAME).upload(file.name, file.getvalue())
        if hasattr(result, 'error') and result.error:
            if result.error.get('statusCode') == 409:
                st.warning(f"⚠️ File '{file.name}' already exists.")
                return True
            st.error(f"❌ Upload error: {result.error['message']}")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Upload exception: {e}")
        return False

def list_pdfs_from_supabase():
    try:
        files = supabase.storage.from_(BUCKET_NAME).list()
        return [f for f in files if f["name"].endswith(".pdf") and not f["name"].startswith(".emptyFolder")]
    except Exception as e:
        st.error(f"❌ Listing error: {e}")
        return []

def read_pdf_page(pdf_bytes, page_number):
    reader = PdfReader(pdf_bytes)
    return reader.pages[page_number].extract_text() or ""

def highlight_text(text, search_term):
    pattern = re.compile(rf'\b{re.escape(search_term)}\b', re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)

def main():
    st.set_page_config(page_title="📄 Multi-PDF Viewer & Search", layout="wide")
    st.title("📄 Multi-PDF Upload and Search with Supabase")

    uploaded_files = st.file_uploader("📤 Upload PDF files (max 10)", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files[:10]:
            success = upload_pdf_to_supabase(file)
            if success:
                st.success(f"✅ '{file.name}' uploaded successfully.")

    pdf_files = list_pdfs_from_supabase()
    if not pdf_files:
        st.info("📂 No PDFs found in Supabase storage.")
        return

    search_filter = st.sidebar.text_input("🔍 Filter filenames")
    filtered_files = [f for f in pdf_files if search_filter.lower() in f['name'].lower()]

    st.sidebar.markdown("### 📊 Info")
    st.sidebar.write(f"🗂️ Total files: {len(pdf_files)}")
    st.sidebar.write(f"🔎 Filtered: {len(filtered_files)}")

    for i, file_info in enumerate(filtered_files):
        st.markdown(f"---\n### 📘 File: {file_info['name']}")

        try:
            response = supabase.storage.from_(BUCKET_NAME).download(file_info["name"])
            if hasattr(response, 'error') and response.error:
                st.error(f"❌ Download error: {response.error['message']}")
                continue

            pdf_data = BytesIO(response)
            pdf_data.seek(0)

            reader = PdfReader(pdf_data)
            total_pages = len(reader.pages)

            selected_page = st.selectbox(f"Select page for {file_info['name']}", list(range(1, total_pages + 1)), key=f"sel_{i}") - 1

            # Reset stream for image preview
            pdf_data.seek(0)
            images = convert_from_bytes(pdf_data.read(), first_page=selected_page + 1, last_page=selected_page + 1, poppler_path=POPPLER_PATH)
            preview_image = images[0]

            col1, col2 = st.columns(2)
            col1.image(preview_image, caption=f"🖼️ Page {selected_page + 1}")

            # Reset stream for text
            pdf_data.seek(0)
            text = read_pdf_page(pdf_data, selected_page)

            search_term = col2.text_input(f"Search in {file_info['name']}", key=f"search_{i}")
            if search_term:
                highlighted_lines = []
                pattern = re.compile(rf'\b{re.escape(search_term)}\b', re.IGNORECASE)
                for line in text.splitlines():
                    if pattern.search(line):
                        highlighted_lines.append(highlight_text(line, search_term))
                if highlighted_lines:
                    col2.markdown("<br>".join(highlighted_lines), unsafe_allow_html=True)
                else:
                    col2.write("❌ No matches found.")
            else:
                col2.text_area("📜 Page Text", value=text, height=400, key=f"text_{i}")

        except Exception as e:
            st.error(f"❌ Error processing {file_info['name']}: {e}")

if __name__ == "__main__":
    main()