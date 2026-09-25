# Render Download Section
col_format, col_btn = st.columns([1.5, 2.5])

with col_format:
    export_format = st.selectbox(
        "Select Export Format:",
        ["PDF Document (.pdf)", "Microsoft Word (.docx)", "Markdown (.md)"],
        key="export_format_selector"
    )

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    if "PDF" in export_format:
        pdf_data = generate_pdf_brief(brief, st.session_state.get("executed_query", ""))
        st.download_button(
            label="💚 Download PDF Report",
            data=pdf_data,
            file_name="WWM_Executive_Brief.pdf",
            mime="application/pdf"
        )
    elif "Word" in export_format:
        docx_data = generate_docx_brief(brief, st.session_state.get("executed_query", ""))
        st.download_button(
            label="💚 Download Word Document",
            data=docx_data,
            file_name="WWM_Executive_Brief.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        md_data = generate_markdown_brief(brief, st.session_state.get("executed_query", ""))
        st.download_button(
            label="💚 Download Markdown (.md)",
            data=md_data,
            file_name="WWM_Executive_Brief.md",
            mime="text/markdown"
        )
