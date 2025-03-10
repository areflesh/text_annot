import streamlit as st
import pandas as pd
import os
import json
from streamlit_annotation_tools import text_labeler

# Define the path for storing annotations
ANNOTATION_FILE = 'annotations.json'

# Load existing annotations if available
if os.path.exists(ANNOTATION_FILE):
    with open(ANNOTATION_FILE, 'r') as f:
        annotations = json.load(f)
else:
    annotations = {}

# Function to save annotations
def save_annotations():
    with open(ANNOTATION_FILE, 'w') as f:
        json.dump(annotations, f, indent=4)

# Function to split text into captions (sentences)
def split_into_captions(text):
    return text.split('.')

st.title('Text Annotation Tool')

# File uploader
uploaded_file = st.file_uploader('Upload a text file', type=['txt'])

if uploaded_file:
    # Read and split the text into captions
    text = uploaded_file.read().decode('utf-8')
    captions = split_into_captions(text)
    st.session_state['captions'] = captions

# Display captions and annotation interface
if 'captions' in st.session_state:
    for i, caption in enumerate(st.session_state['captions']):
        if caption.strip():  # Skip empty captions
            st.subheader(f'Caption {i+1}')
            st.write(caption.strip())

            # Check if this caption has been annotated
            if caption in annotations:
                st.write('This caption has already been annotated.')
                st.json(annotations[caption])
            else:
                # Annotation interface
                labels = ['obj', 'pred', 'sub']
                annotation = text_labeler(caption.strip(), labels=labels)
                if annotation:
                    annotations[caption] = annotation
                    save_annotations()
                    st.success('Annotation saved.')

# Display all annotations
if annotations:
    st.subheader('All Annotations')
    st.json(annotations)
