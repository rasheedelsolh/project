import streamlit as st
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
import re

def read_pdf_page(file, page_number):
    pdfReader = PdfReader(file)
    page = pdfReader.pages[page_number]
    return page.extract_text() or ""

def on_text_area_change():
    st.session_state.page_text = st.session_state.my_text_area

def highlight_text(text, search_term):
    pattern = re.compile(rf'\b{re.escape(search_term)}\b', re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)

def format_size(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def main():
    st.set_page_config(page_title="Multi-PDF Upload and Search", layout="wide")
    st.title("📄 Multi-PDF Upload and Search")

    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []

    # Sidebar filters
    st.sidebar.header("📊 Filters & Stats")
    global_search = st.sidebar.text_input("🔍 Global Search (filename)")
    min_size = st.sidebar.slider("Min file size (MB)", 0.0, 50.0, 0.0, 0.5)
    max_size = st.sidebar.slider("Max file size (MB)", 0.0, 100.0, 100.0, 0.5)

    # File uploader
    new_files = st.file_uploader(
        "Upload up to 10 PDF files",
        type=["pdf"],
        accept_multiple_files=True
    )

    # Allow repeated files
    if new_files:
        for new_file in new_files[:10]:
            st.session_state.uploaded_files.append(new_file)
            st.success(f"✅ File '{new_file.name}' uploaded.")

    # Filter
    filtered_files = []
    total_size = 0
    for f in st.session_state.uploaded_files:
        size_mb = f.size / (1024 * 1024)
        if global_search.lower() in f.name.lower() and min_size <= size_mb <= max_size:
            filtered_files.append(f)
            total_size += f.size

    # Stats
    st.sidebar.markdown("### ℹ️ Statistics")
    st.sidebar.write(f"**Total files:** {len(filtered_files)}")
    st.sidebar.write(f"**Total size:** {format_size(total_size)}")
    st.sidebar.write(f"**Estimated search time:** {len(filtered_files) * 0.5:.2f} sec")

    if not filtered_files:
        st.info("No files match the current filter. Try uploading or adjusting filters.")
        return

    # Display each PDF
    for i, pdf_file in enumerate(filtered_files):
        st.markdown(f"---\n### 📘 File: `{pdf_file.name}` ({format_size(pdf_file.size)})")

        pdfReader = PdfReader(pdf_file)
        page_numbers = list(range(1, len(pdfReader.pages) + 1))
        selected_page = st.selectbox(
            f"Select a page for {pdf_file.name}",
            page_numbers,
            key=f"page_{i}_{pdf_file.name}"
        )
        selected_page -= 1

        # Display image
        images = convert_from_bytes(pdf_file.getvalue())
        image = images[selected_page]

        col1, col2 = st.columns(2)
        col1.image(image, caption=f"Page {selected_page + 1}")

        page_text = read_pdf_page(pdf_file, selected_page)

        search_term = col2.text_input(
            f"Search in {pdf_file.name} (exact word)",
            key=f"search_{i}_{pdf_file.name}"
        )

        if search_term:
            pattern = re.compile(rf'\b{re.escape(search_term)}\b', re.IGNORECASE)
            matching_lines = [line for line in page_text.split('\n') if pattern.search(line)]

            if matching_lines:
                col2.write(f"Found {len(matching_lines)} result(s):")
                highlighted = [highlight_text(line, search_term) for line in matching_lines]
                col2.markdown("<br>".join(highlighted), unsafe_allow_html=True)
            else:
                col2.write("❌ No matches found.")
        else:
            col2.text_area(
                "Page Text",
                height=400,
                value=page_text,
                key=f"text_{i}_{pdf_file.name}"
            )

if __name__ == '__main__':
    main()
