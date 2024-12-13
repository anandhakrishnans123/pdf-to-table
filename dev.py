# -*- coding: utf-8 -*-
import streamlit as st
from pdf2image import convert_from_path
import tempfile
import os
import time
from img2table.ocr import AzureOCR
from img2table.document import Image
import numpy as np
import cv2
from PIL import Image as PILImage

# Azure OCR credentials (replace with your actual key and endpoint)
subscription_key = "YOUR_AZURE_OCR_KEY"
endpoint = "YOUR_AZURE_OCR_ENDPOINT"

# Initialize AzureOCR
azure_ocr = AzureOCR(subscription_key=subscription_key, endpoint=endpoint)

# Retry logic for Azure OCR calls
def extract_table_with_retry(image, retries=3, delay=2):
    for attempt in range(retries):
        try:
            return image.extract_tables(
                ocr=azure_ocr,
                implicit_rows=True,
                borderless_tables=False,
                min_confidence=30
            )
        except Exception as e:
            if 'Too Many Requests' in str(e):
                st.warning(f"Rate limit exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                time.sleep(delay)
            else:
                raise e
    raise Exception("Max retries exceeded for Azure OCR.")

# Streamlit app layout
st.title("PDF to Image Conversion and Table Extraction")
st.markdown("Upload a PDF, which will be converted to images and processed.")

# Upload PDF file
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    # Save the uploaded PDF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_file:
        tmp_pdf_file.write(uploaded_file.getvalue())
        tmp_pdf_path = tmp_pdf_file.name

    # Convert PDF to images (one image per page)
    try:
        pdf_images = convert_from_path(tmp_pdf_path)
        st.success(f"Successfully converted {len(pdf_images)} pages to images.")

        # Display images
        for i, img in enumerate(pdf_images):
            st.image(img, caption=f"Page {i + 1}", use_column_width=True)
        
            # Convert the image to a format suitable for OCR
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img_file:
                img.save(tmp_img_file, "PNG")
                tmp_img_path = tmp_img_file.name

            # Process the image for table extraction using Azure OCR
            img_for_ocr = Image(src=tmp_img_path)
            try:
                extracted_tables = extract_table_with_retry(img_for_ocr, retries=3, delay=5)
                if extracted_tables:
                    for j, table in enumerate(extracted_tables):
                        st.markdown(f"### Extracted Table from Page {i + 1}, Table {j + 1}")
                        st.markdown(table.html_repr(title=f"Extracted Table {j + 1}"), unsafe_allow_html=True)
                else:
                    st.warning(f"No tables detected on page {i + 1}.")
            except Exception as e:
                st.error(f"Failed to extract tables from page {i + 1}: {e}")
            finally:
                os.remove(tmp_img_path)  # Clean up the temporary image file

    except Exception as e:
        st.error(f"Error occurred while processing the PDF: {e}")
    finally:
        os.remove(tmp_pdf_path)  # Clean up the temporary PDF file
