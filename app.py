import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Image Description Annotation Tool",
    page_icon="📝",
    layout="wide"
)

# Initialize session state variables if they don't exist
if 'captions' not in st.session_state:
    st.session_state.captions = []
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'annotations' not in st.session_state:
    st.session_state.annotations = {}
if 'annotated_indices' not in st.session_state:
    st.session_state.annotated_indices = set()
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'filename' not in st.session_state:
    st.session_state.filename = ""


# Function to split text into captions
def split_text_into_captions(text):
    # This is a simple splitter - customize based on your text format
    # Here we're assuming each line is a separate caption
    captions = [line.strip() for line in text.split('\n') if line.strip()]
    return captions


# Function to load annotations from disk
def load_annotations():
    try:
        if os.path.exists('./.streamlit/annotations.json'):
            with open('./.streamlit/annotations.json', 'r') as f:
                data = json.load(f)
                st.session_state.annotations = data.get('annotations', {})
                st.session_state.annotated_indices = set(int(idx) for idx in st.session_state.annotations.keys())
                return True
        return False
    except Exception as e:
        st.error(f"Error loading annotations: {e}")
        return False


# Function to save annotations to disk
def save_annotations():
    try:
        os.makedirs('./.streamlit', exist_ok=True)
        with open('./.streamlit/annotations.json', 'w') as f:
            json.dump({
                'filename': st.session_state.filename,
                'annotations': st.session_state.annotations,
                'last_updated': datetime.now().isoformat()
            }, f)
        return True
    except Exception as e:
        st.error(f"Error saving annotations: {e}")
        return False


# Function to handle navigation
def go_to_next():
    if st.session_state.current_index < len(st.session_state.captions) - 1:
        st.session_state.current_index += 1
        # Clear the form fields when navigating
        st.session_state.subject = ""
        st.session_state.predicate = ""
        st.session_state.object = ""


def go_to_prev():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1
        # Clear the form fields when navigating
        st.session_state.subject = ""
        st.session_state.predicate = ""
        st.session_state.object = ""


def go_to_index(idx):
    if 0 <= idx < len(st.session_state.captions):
        st.session_state.current_index = idx
        # Clear the form fields when navigating
        st.session_state.subject = ""
        st.session_state.predicate = ""
        st.session_state.object = ""


# Function to save current annotation
def save_current_annotation():
    idx = str(st.session_state.current_index)
    subject = st.session_state.get('subject', '')
    predicate = st.session_state.get('predicate', '')
    object = st.session_state.get('object', '')

    if subject and predicate and object:
        st.session_state.annotations[idx] = {
            'caption': st.session_state.captions[st.session_state.current_index],
            'subject': subject,
            'predicate': predicate,
            'object': object,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.annotated_indices.add(st.session_state.current_index)
        save_annotations()
        st.success("Annotation saved!")
    else:
        st.warning("Please fill all fields before saving.")


# Function to handle file upload
def process_uploaded_file(uploaded_file):
    try:
        content = uploaded_file.getvalue().decode('utf-8')
        captions = split_text_into_captions(content)

        if captions:
            st.session_state.captions = captions
            st.session_state.current_index = 0
            st.session_state.file_uploaded = True
            st.session_state.filename = uploaded_file.name

            # Check if we have existing annotations for this file
            if load_annotations():
                st.success(
                    f"Loaded existing annotations with {len(st.session_state.annotated_indices)} annotated captions.")
            else:
                st.session_state.annotations = {}
                st.session_state.annotated_indices = set()
                st.success(f"Loaded {len(captions)} captions for annotation.")

            return True
        else:
            st.error("No captions found in the uploaded file.")
            return False
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return False


# Function to export annotations
def export_annotations():
    if not st.session_state.annotations:
        st.warning("No annotations to export.")
        return

    try:
        export_data = {
            'filename': st.session_state.filename,
            'total_captions': len(st.session_state.captions),
            'annotated_captions': len(st.session_state.annotated_indices),
            'annotations': st.session_state.annotations
        }

        # Convert to DataFrame for display
        annotations_list = []
        for idx, anno in st.session_state.annotations.items():
            annotations_list.append({
                'Index': int(idx),
                'Caption': anno['caption'],
                'Subject': anno['subject'],
                'Predicate': anno['predicate'],
                'Object': anno['object']
            })

        df = pd.DataFrame(annotations_list)
        df = df.sort_values('Index')

        # For download as JSON
        json_data = json.dumps(export_data, indent=2)

        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name=f"annotations_{st.session_state.filename.split('.')[0]}.json",
            mime="application/json"
        )

        # Display as table
        st.dataframe(df)

    except Exception as e:
        st.error(f"Error exporting annotations: {e}")


# UI Components

# Sidebar
st.sidebar.title("Annotation Tool")

# File upload widget
uploaded_file = st.sidebar.file_uploader("Upload text file", type=["txt"])
if uploaded_file is not None and (
        not st.session_state.file_uploaded or uploaded_file.name != st.session_state.filename):
    process_uploaded_file(uploaded_file)

# Navigation controls in sidebar
st.sidebar.subheader("Navigation")
if st.session_state.file_uploaded:
    total_captions = len(st.session_state.captions)
    annotated_count = len(st.session_state.annotated_indices)

    st.sidebar.progress(annotated_count / total_captions if total_captions > 0 else 0)
    st.sidebar.text(
        f"Annotated: {annotated_count}/{total_captions} ({int(annotated_count / total_captions * 100) if total_captions > 0 else 0}%)")

    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Previous", key="prev_btn"):
            go_to_prev()
    with col2:
        if st.button("Next", key="next_btn"):
            go_to_next()

    # Jump to specific caption
    jump_index = st.sidebar.number_input("Jump to caption #", min_value=0, max_value=total_captions - 1,
                                         value=st.session_state.current_index)
    if st.sidebar.button("Go"):
        go_to_index(jump_index)

    # Jump to unannotated
    if st.sidebar.button("Next Unannotated"):
        unannotated = [i for i in range(total_captions) if i not in st.session_state.annotated_indices]
        unannotated = [i for i in unannotated if i > st.session_state.current_index]
        if unannotated:
            go_to_index(unannotated[0])
        else:
            st.sidebar.info("No more unannotated captions after current position.")

# Main content area
st.title("Image Description Annotation Tool")

if st.session_state.file_uploaded and st.session_state.captions:
    current_idx = st.session_state.current_index

    # Display current caption with index
    st.subheader(f"Caption #{current_idx + 1} of {len(st.session_state.captions)}")

    # Highlight if already annotated
    if current_idx in st.session_state.annotated_indices:
        st.markdown(
            f"<div style='background-color:#e6ffe6;padding:10px;border-radius:5px;'>{st.session_state.captions[current_idx]}</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div style='background-color:#f0f0f0;padding:10px;border-radius:5px;'>{st.session_state.captions[current_idx]}</div>",
            unsafe_allow_html=True)

    # Annotation form
    st.subheader("Annotation")

    # Set default values for the form fields before rendering widgets
    if str(current_idx) in st.session_state.annotations:
        existing_anno = st.session_state.annotations[str(current_idx)]
        if 'subject' not in st.session_state:
            st.session_state.subject = existing_anno['subject']
        if 'predicate' not in st.session_state:
            st.session_state.predicate = existing_anno['predicate']
        if 'object' not in st.session_state:
            st.session_state.object = existing_anno['object']
    else:
        # Initialize empty if not in session state
        if 'subject' not in st.session_state:
            st.session_state.subject = ""
        if 'predicate' not in st.session_state:
            st.session_state.predicate = ""
        if 'object' not in st.session_state:
            st.session_state.object = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.text_input("Subject", key="subject", value=st.session_state.subject)
    with col2:
        predicate = st.text_input("Predicate", key="predicate", value=st.session_state.predicate)
    with col3:
        object = st.text_input("Object", key="object", value=st.session_state.object)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Save Annotation"):
            save_current_annotation()

    # Annotation stats and export
    st.subheader("Annotation Progress")

    if st.session_state.annotated_indices:
        st.info(
            f"You've annotated {len(st.session_state.annotated_indices)} out of {len(st.session_state.captions)} captions.")

        if st.button("View & Export Annotations"):
            export_annotations()
    else:
        st.info("No annotations saved yet. Start annotating captions!")

else:
    st.info("Please upload a text file containing image descriptions to start annotation.")
    st.markdown("""
    ### Instructions:
    1. Upload a text file with image descriptions (one per line)
    2. Navigate between captions using the sidebar controls
    3. For each caption, annotate with Subject-Predicate-Object
    4. Save your annotations
    5. Export all annotations when done

    Your progress is automatically saved and will be available when you return.
    """)

# Load annotations on initial page load
if not st.session_state.get('loaded_initial', False):
    load_annotations()
    st.session_state.loaded_initial = True