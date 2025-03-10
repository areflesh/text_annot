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
if 'current_sentence_index' not in st.session_state:
    st.session_state.current_sentence_index = 0
if 'annotations' not in st.session_state:
    st.session_state.annotations = {}
if 'annotated_indices' not in st.session_state:
    st.session_state.annotated_indices = set()
if 'file_uploaded' not in st.session_state:
    st.session_state.file_uploaded = False
if 'filename' not in st.session_state:
    st.session_state.filename = ""


# Function to split text into captions and sentences
def split_text_into_captions(text):
    # First split by lines to get captions
    captions = [line.strip() for line in text.split('\n') if line.strip()]

    # Process each caption to split into sentences and store both
    processed_captions = []
    for caption in captions:
        # Add the full caption as a unit
        processed_captions.append({
            'full_caption': caption,
            'sentences': split_into_sentences(caption)
        })

    return processed_captions


# Function to split a caption into sentences
def split_into_sentences(text):
    # Basic sentence splitting using regex
    # This handles common sentence endings (.!?) with space after
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter out empty sentences
    return [s.strip() for s in sentences if s.strip()]


# Function to load annotations from disk
def load_annotations():
    try:
        if os.path.exists('./.streamlit/annotations.json'):
            with open('./.streamlit/annotations.json', 'r') as f:
                data = json.load(f)
                st.session_state.annotations = data.get('annotations', {})

                # Convert the composite keys into tuples for the annotated_indices set
                st.session_state.annotated_indices = set()
                for composite_idx in st.session_state.annotations.keys():
                    if '_' in composite_idx:  # New format with caption_idx_sentence_idx
                        caption_idx, sentence_idx = map(int, composite_idx.split('_'))
                        st.session_state.annotated_indices.add((caption_idx, sentence_idx))
                    else:  # Old format with just caption_idx
                        # For backward compatibility
                        st.session_state.annotated_indices.add((int(composite_idx), 0))

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
    caption_idx = st.session_state.current_index
    sentence_idx = st.session_state.current_sentence_index

    # First try to go to next sentence in current caption
    if sentence_idx < len(st.session_state.captions[caption_idx]['sentences']) - 1:
        st.session_state.current_sentence_index += 1
    # If no more sentences, go to next caption
    elif caption_idx < len(st.session_state.captions) - 1:
        st.session_state.current_index += 1
        st.session_state.current_sentence_index = 0

    # Clear the form fields when navigating
    st.session_state.subject = ""
    st.session_state.predicate = ""
    st.session_state.object = ""


def go_to_prev():
    caption_idx = st.session_state.current_index
    sentence_idx = st.session_state.current_sentence_index

    # First try to go to previous sentence in current caption
    if sentence_idx > 0:
        st.session_state.current_sentence_index -= 1
    # If at first sentence, go to previous caption
    elif caption_idx > 0:
        st.session_state.current_index -= 1
        # Go to last sentence of previous caption
        st.session_state.current_sentence_index = len(st.session_state.captions[caption_idx - 1]['sentences']) - 1

    # Clear the form fields when navigating
    st.session_state.subject = ""
    st.session_state.predicate = ""
    st.session_state.object = ""


def go_to_index(idx):
    if 0 <= idx < len(st.session_state.captions):
        st.session_state.current_index = idx
        st.session_state.current_sentence_index = 0
        # Clear the form fields when navigating
        st.session_state.subject = ""
        st.session_state.predicate = ""
        st.session_state.object = ""


# Function to save current annotation
def save_current_annotation():
    # Create a composite key for the annotation (caption_index, sentence_index)
    caption_idx = st.session_state.current_index
    sentence_idx = st.session_state.current_sentence_index
    composite_idx = f"{caption_idx}_{sentence_idx}"

    subject = st.session_state.get('subject', '')
    predicate = st.session_state.get('predicate', '')
    object = st.session_state.get('object', '')

    if subject and predicate and object:
        current_caption = st.session_state.captions[caption_idx]['full_caption']
        current_sentence = st.session_state.captions[caption_idx]['sentences'][sentence_idx]

        st.session_state.annotations[composite_idx] = {
            'caption_index': caption_idx,
            'sentence_index': sentence_idx,
            'full_caption': current_caption,
            'sentence': current_sentence,
            'subject': subject,
            'predicate': predicate,
            'object': object,
            'timestamp': datetime.now().isoformat()
        }

        # Track that this specific sentence has been annotated
        key = (caption_idx, sentence_idx)
        if key not in st.session_state.annotated_indices:
            st.session_state.annotated_indices.add(key)

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
        # Count total sentences
        total_sentences = sum(len(caption['sentences']) for caption in st.session_state.captions)

        export_data = {
            'filename': st.session_state.filename,
            'total_captions': len(st.session_state.captions),
            'total_sentences': total_sentences,
            'annotated_sentences': len(st.session_state.annotated_indices),
            'annotations': st.session_state.annotations
        }

        # Convert to DataFrame for display
        annotations_list = []
        for composite_idx, anno in st.session_state.annotations.items():
            caption_idx, sentence_idx = anno['caption_index'], anno['sentence_index']
            annotations_list.append({
                'Caption_Index': caption_idx,
                'Sentence_Index': sentence_idx,
                'Full_Caption': anno['full_caption'],
                'Sentence': anno['sentence'],
                'Subject': anno['subject'],
                'Predicate': anno['predicate'],
                'Object': anno['object'],
                'Timestamp': anno['timestamp']
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
        # Create a list of all possible (caption_idx, sentence_idx) pairs
        all_pairs = []
        for cap_idx, caption in enumerate(st.session_state.captions):
            for sent_idx in range(len(caption['sentences'])):
                all_pairs.append((cap_idx, sent_idx))

        # Find the current position in the sequence
        current_position = (st.session_state.current_index, st.session_state.current_sentence_index)
        current_position_idx = all_pairs.index(current_position) if current_position in all_pairs else 0

        # Find all unannotated pairs after the current position
        unannotated = [
            pair for idx, pair in enumerate(all_pairs)
            if idx > current_position_idx and pair not in st.session_state.annotated_indices
        ]

        if unannotated:
            next_cap_idx, next_sent_idx = unannotated[0]
            st.session_state.current_index = next_cap_idx
            st.session_state.current_sentence_index = next_sent_idx
            # Clear form fields
            st.session_state.subject = ""
            st.session_state.predicate = ""
            st.session_state.object = ""
        else:
            st.sidebar.info("No more unannotated sentences after current position.")

# Main content area
st.title("Image Description Annotation Tool")

if st.session_state.file_uploaded and st.session_state.captions:
    current_caption_idx = st.session_state.current_index
    current_sentence_idx = st.session_state.current_sentence_index
    current_caption = st.session_state.captions[current_caption_idx]
    total_sentences = len(current_caption['sentences'])

    # Display current caption with index
    st.subheader(f"Caption #{current_caption_idx + 1} of {len(st.session_state.captions)}")

    # Show full caption (highlighted differently to distinguish from current sentence)
    st.markdown("**Full caption:**")
    st.markdown(
        f"<div style='background-color:#f8f9fa;padding:10px;border-radius:5px;margin-bottom:10px;'>{current_caption['full_caption']}</div>",
        unsafe_allow_html=True)

    # Display current sentence with index
    st.markdown(f"**Current sentence ({current_sentence_idx + 1} of {total_sentences}):**")

    current_sentence = current_caption['sentences'][current_sentence_idx]

    # Check if this specific sentence is already annotated
    is_annotated = (current_caption_idx, current_sentence_idx) in st.session_state.annotated_indices

    # Highlight if already annotated and show clickable text
    if is_annotated:
        bg_color = "#e6ffe6"  # light green for annotated
    else:
        bg_color = "#f0f0f0"  # light gray for not annotated

    # Create a clickable sentence that fills the form fields when clicked
    st.markdown(f"""
    <div style='background-color:{bg_color};padding:10px;border-radius:5px;margin-bottom:15px;' 
         onclick="
         const subjectInput = parent.document.querySelector('[data-testid=\\"stTextInput\\"] input[aria-label=\\"Subject\\"]');
         const predicateInput = parent.document.querySelector('[data-testid=\\"stTextInput\\"] input[aria-label=\\"Predicate\\"]');
         const objectInput = parent.document.querySelector('[data-testid=\\"stTextInput\\"] input[aria-label=\\"Object\\"]');

         // Store selection in temporary variables
         const selection = window.getSelection();
         const selectedText = selection.toString();

         // Only update if there's a selection
         if(selectedText) {{
             // Determine which field to fill based on which is empty or focused
             if(!subjectInput.value || document.activeElement === subjectInput) {{
                 subjectInput.value = selectedText;
                 subjectInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
             }} else if(!predicateInput.value || document.activeElement === predicateInput) {{
                 predicateInput.value = selectedText;
                 predicateInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
             }} else if(!objectInput.value || document.activeElement === objectInput) {{
                 objectInput.value = selectedText;
                 objectInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
             }}
         }}
         "
    >
        {current_sentence}
    </div>
    <script>
    // Make the sentence text selectable
    document.addEventListener('mouseup', function() {{
        const selection = window.getSelection();
        if(selection.toString().length > 0) {{
            // We'll handle the selection in the onclick handler above
        }}
    }});
    </script>
    """, unsafe_allow_html=True)

    # Sentence navigation
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if current_sentence_idx > 0:
            st.button("◀ Prev Sentence", key="prev_sentence",
                      on_click=lambda: setattr(st.session_state, 'current_sentence_index',
                                               st.session_state.current_sentence_index - 1))
    with col3:
        if current_sentence_idx < total_sentences - 1:
            st.button("Next Sentence ▶", key="next_sentence",
                      on_click=lambda: setattr(st.session_state, 'current_sentence_index',
                                               st.session_state.current_sentence_index + 1))

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