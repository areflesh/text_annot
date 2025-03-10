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
if 'current_caption_index' not in st.session_state:
    st.session_state.current_caption_index = 0
if 'sentences' not in st.session_state:
    st.session_state.sentences = []
if 'current_sentence_index' not in st.session_state:
    st.session_state.current_sentence_index = 0
if 'annotations' not in st.session_state:
    st.session_state.annotations = {}
if 'annotated_keys' not in st.session_state:
    st.session_state.annotated_keys = set()
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'filename' not in st.session_state:
    st.session_state.filename = ""


# Function to split text into captions
def split_text_into_captions(text):
    # First split by lines
    captions = [line.strip() for line in text.split('\n') if line.strip()]
    return captions


# Function to split caption into sentences
def split_caption_into_sentences(caption):
    # Using regex to split on sentence boundaries
    # This handles periods, question marks, and exclamation points
    sentences = re.split(r'(?<=[.!?])\s+', caption)
    # Remove any empty sentences
    return [s.strip() for s in sentences if s.strip()]


# Function to load annotations from disk
def load_annotations():
    try:
        if os.path.exists('./.streamlit/annotations.json'):
            with open('./.streamlit/annotations.json', 'r') as f:
                data = json.load(f)
                st.session_state.annotations = data.get('annotations', {})
                st.session_state.annotated_keys = set(st.session_state.annotations.keys())
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
def go_to_next_sentence():
    # First check if we can move to the next sentence in current caption
    if st.session_state.current_sentence_index < len(st.session_state.sentences) - 1:
        st.session_state.current_sentence_index += 1
    # Otherwise move to the next caption
    elif st.session_state.current_caption_index < len(st.session_state.captions) - 1:
        st.session_state.current_caption_index += 1
        st.session_state.sentences = split_caption_into_sentences(
            st.session_state.captions[st.session_state.current_caption_index])
        st.session_state.current_sentence_index = 0

    # Clear the form fields when navigating
    st.session_state.subject = ""
    st.session_state.predicate = ""
    st.session_state.object = ""


def go_to_prev_sentence():
    # First check if we can move to the previous sentence in current caption
    if st.session_state.current_sentence_index > 0:
        st.session_state.current_sentence_index -= 1
    # Otherwise move to the previous caption
    elif st.session_state.current_caption_index > 0:
        st.session_state.current_caption_index -= 1
        st.session_state.sentences = split_caption_into_sentences(
            st.session_state.captions[st.session_state.current_caption_index])
        st.session_state.current_sentence_index = len(st.session_state.sentences) - 1

    # Clear the form fields when navigating
    st.session_state.subject = ""
    st.session_state.predicate = ""
    st.session_state.object = ""


def go_to_caption(caption_idx):
    if 0 <= caption_idx < len(st.session_state.captions):
        st.session_state.current_caption_index = caption_idx
        st.session_state.sentences = split_caption_into_sentences(st.session_state.captions[caption_idx])
        st.session_state.current_sentence_index = 0

        # Clear the form fields when navigating
        st.session_state.subject = ""
        st.session_state.predicate = ""
        st.session_state.object = ""


# Function to save current annotation
def save_current_annotation():
    caption_idx = st.session_state.current_caption_index
    sentence_idx = st.session_state.current_sentence_index

    # Create a unique key for this sentence
    key = f"{caption_idx}_{sentence_idx}"

    subject = st.session_state.get('subject', '')
    predicate = st.session_state.get('predicate', '')
    object = st.session_state.get('object', '')

    if subject and predicate and object:
        st.session_state.annotations[key] = {
            'caption_index': caption_idx,
            'sentence_index': sentence_idx,
            'caption': st.session_state.captions[caption_idx],
            'sentence': st.session_state.sentences[sentence_idx],
            'subject': subject,
            'predicate': predicate,
            'object': object,
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.annotated_keys.add(key)
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
            st.session_state.current_caption_index = 0

            # Split the first caption into sentences
            sentences = split_caption_into_sentences(captions[0])
            st.session_state.sentences = sentences
            st.session_state.current_sentence_index = 0

            st.session_state.file_uploaded = True
            st.session_state.filename = uploaded_file.name

            # Check if we have existing annotations for this file
            if load_annotations():
                st.success(
                    f"Loaded existing annotations with {len(st.session_state.annotated_keys)} annotated sentences.")
            else:
                st.session_state.annotations = {}
                st.session_state.annotated_keys = set()

                # Count total sentences
                total_sentences = sum(len(split_caption_into_sentences(caption)) for caption in captions)
                st.success(f"Loaded {len(captions)} captions with {total_sentences} sentences for annotation.")

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
        # Count total sentences
        total_sentences = 0
        for caption in st.session_state.captions:
            sentences = split_caption_into_sentences(caption)
            total_sentences += len(sentences)

        export_data = {
            'filename': st.session_state.filename,
            'total_captions': len(st.session_state.captions),
            'total_sentences': total_sentences,
            'annotated_sentences': len(st.session_state.annotated_keys),
            'annotations': st.session_state.annotations
        }

        # Convert to DataFrame for display
        annotations_list = []
        for key, anno in st.session_state.annotations.items():
            annotations_list.append({
                'Caption_Index': anno['caption_index'] + 1,  # Convert to 1-indexed for display
                'Sentence_Index': anno['sentence_index'] + 1,  # Convert to 1-indexed for display
                'Caption': anno['caption'],
                'Sentence': anno['sentence'],
                'Subject': anno['subject'],
                'Predicate': anno['predicate'],
                'Object': anno['object']
            })

        df = pd.DataFrame(annotations_list)
        if not df.empty:
            df = df.sort_values(['Caption_Index', 'Sentence_Index'])

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

    # Count total sentences across all captions
    total_sentences = 0
    sentences_per_caption = []
    for caption in st.session_state.captions:
        sentences = split_caption_into_sentences(caption)
        sentences_per_caption.append(len(sentences))
        total_sentences += len(sentences)

    annotated_count = len(st.session_state.annotated_keys)

    st.sidebar.progress(annotated_count / total_sentences if total_sentences > 0 else 0)
    st.sidebar.text(
        f"Annotated: {annotated_count}/{total_sentences} sentences ({int(annotated_count / total_sentences * 100) if total_sentences > 0 else 0}%)")

    # Current position info
    current_caption = st.session_state.current_caption_index
    current_sentence = st.session_state.current_sentence_index
    total_sentences_in_caption = len(st.session_state.sentences)

    st.sidebar.text(f"Caption: {current_caption + 1}/{total_captions}")
    st.sidebar.text(f"Sentence: {current_sentence + 1}/{total_sentences_in_caption}")

    # Navigation buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Previous", key="prev_btn"):
            go_to_prev_sentence()
    with col2:
        if st.button("Next", key="next_btn"):
            go_to_next_sentence()

    # Jump to specific caption
    jump_caption = st.sidebar.number_input("Jump to caption #", min_value=1, max_value=total_captions,
                                           value=current_caption + 1)
    if st.sidebar.button("Go to Caption"):
        go_to_caption(jump_caption - 1)  # Convert to 0-indexed

    # Jump to next unannotated sentence
    if st.sidebar.button("Next Unannotated"):
        # Find next unannotated sentence
        found = False

        # Check remaining sentences in current caption
        for s_idx in range(current_sentence + 1, len(st.session_state.sentences)):
            key = f"{current_caption}_{s_idx}"
            if key not in st.session_state.annotated_keys:
                st.session_state.current_sentence_index = s_idx
                found = True
                break

        # If not found, check subsequent captions
        if not found:
            for c_idx in range(current_caption + 1, len(st.session_state.captions)):
                sentences = split_caption_into_sentences(st.session_state.captions[c_idx])
                for s_idx in range(len(sentences)):
                    key = f"{c_idx}_{s_idx}"
                    if key not in st.session_state.annotated_keys:
                        go_to_caption(c_idx)
                        st.session_state.current_sentence_index = s_idx
                        found = True
                        break
                if found:
                    break

        if not found:
            st.sidebar.info("No more unannotated sentences.")

# Main content area
st.title("Image Description Annotation Tool")

if st.session_state.file_uploaded and st.session_state.captions:
    caption_idx = st.session_state.current_caption_index
    sentence_idx = st.session_state.current_sentence_index
    key = f"{caption_idx}_{sentence_idx}"

    # Display current caption and highlight current sentence
    st.subheader(f"Caption #{caption_idx + 1}")

    # Show the full caption with highlighted sentence
    sentences = st.session_state.sentences
    full_caption = st.session_state.captions[caption_idx]

    # Display the caption
    st.markdown("**Full caption:**")
    st.markdown(f"<div style='background-color:#f0f0f0;padding:10px;border-radius:5px;'>{full_caption}</div>",
                unsafe_allow_html=True)

    # Display current sentence
    current_sentence = sentences[sentence_idx]
    st.markdown("**Current sentence to annotate:**")

    # Highlight based on whether it's already annotated
    if key in st.session_state.annotated_keys:
        st.markdown(
            f"<div style='background-color:#e6ffe6;padding:10px;border-radius:5px;font-weight:bold;'>{current_sentence}</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div style='background-color:#fff0f0;padding:10px;border-radius:5px;font-weight:bold;'>{current_sentence}</div>",
            unsafe_allow_html=True)

    # Annotation form
    st.subheader("Subject-Predicate-Object Annotation")

    # Set default values for the form fields before rendering widgets
    if key in st.session_state.annotations:
        existing_anno = st.session_state.annotations[key]
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
        subject = st.text_input("Subject", key="subject", value=st.session_state.subject,
                                help="The entity that is doing something or being described")
    with col2:
        predicate = st.text_input("Predicate", key="predicate", value=st.session_state.predicate,
                                  help="The action or relationship between subject and object")
    with col3:
        object = st.text_input("Object", key="object", value=st.session_state.object,
                               help="The entity that the subject is acting upon or related to")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Save Annotation"):
            save_current_annotation()

    # Annotation stats and export
    st.subheader("Annotation Progress")

    # Count total sentences
    total_sentences = 0
    for caption in st.session_state.captions:
        sentences = split_caption_into_sentences(caption)
        total_sentences += len(sentences)

    if st.session_state.annotated_keys:
        st.info("Please upload a text file containing image descriptions to start annotation.")
    st.markdown("""
    ### Instructions:
    1. Upload a text file with image descriptions (one per line)
    2. Each caption will be split into sentences automatically
    3. Navigate between sentences using the sidebar controls
    4. For each sentence, annotate with Subject-Predicate-Object
    5. Save your annotations
    6. Export all annotations when done

    Your progress is automatically saved and will be available when you return.
    """)(
        f"You've annotated {len(st.session_state.annotated_keys)} out of {total_sentences} sentences across {len(st.session_state.captions)} captions.")

    if st.button("View & Export Annotations"):
        export_annotations()
else:
    st.info("No annotations saved yet. Start annotating sentences!")

else:
st.info

# Load annotations on initial page load
if not st.session_state.get('loaded_initial', False):
    load_annotations()
    st.session_state.loaded_initial = True