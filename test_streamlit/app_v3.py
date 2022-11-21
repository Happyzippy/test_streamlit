"""Video transforms with OpenCV"""

import streamlit as st
from brevettiai.platform import PlatformAPI
from uuid import uuid1
from hashlib import md5
import re

st.set_page_config(
   page_title="Brevettiai Upload",
   page_icon="⬆",
)

st.title("Brevettiai dataset upload")

if "uploadhashes" not in st.session_state:
    st.session_state.uploadhashes = set()

def set_web(user, password):
    try:
        web = PlatformAPI(username=user, password=password)
        st.session_state.web = web
    except Exception:
        st.error("Loginerror")


if "web" not in st.session_state:
    user = st.text_input("User")
    password = st.text_input("Enter a password", type="password")
    st.button("Login", on_click=set_web, args=(user, password))
else:
    print("Web in session_state")
    web = st.session_state.web

    datasets = list(sorted(filter(lambda d: not d.locked, web.get_dataset()), key=lambda d: d.created, reverse=True))[:5]
    datasets = {k.name: k for k in datasets}
    dataset_name = st.selectbox("Datasets", options=datasets.keys())
    dataset = datasets[dataset_name]
    st.write(f"[See dataset](https://platform.brevetti.ai/data/{dataset.id})")

    category = st.text_input("Folder to upload into")
    category = re.split(r'/|\\', category)
    files = st.file_uploader("Upload", accept_multiple_files=True, type=['png', 'jpg', 'bmp'])

    upload_status = st.empty()
    for i, file in enumerate(files, start=1):
        dataset.resolve_access_rights()
        checksum = md5(file.getbuffer()).hexdigest()
        if checksum not in st.session_state.uploadhashes:
            upload_status.write(f"Uploading: {i}/{len(files)}")
            ftype = file.name.rsplit(".", -1)[-1]
            fname = f"{uuid1()}.{ftype}"
            dataset.io.write_file(dataset.get_location("", *category, fname), file)
            st.session_state.uploadhashes.add(checksum)
    if files:
        upload_status.write(f"Upload complete")
