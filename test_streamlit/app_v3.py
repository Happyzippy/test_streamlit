"""Video transforms with OpenCV"""

import streamlit as st
from brevettiai.platform import PlatformAPI

with st.form(key="platform-login"):
    user = st.text_input("User")
    password = st.text_input("Enter a password", type="password")
    st.form_submit_button("Login")

web = PlatformAPI(username=user, password=password)

datasets = list(sorted(filter(lambda d: not d.locked, web.get_dataset()), key=lambda d: d.created, reverse=True))[:5]
datasets = {k.name: k for k in datasets}
dataset_name = st.selectbox("Datasets", options=datasets.keys())

dataset = datasets[dataset_name]

file = st.file_uploader("Upload")
if file:
    dataset.resolve_access_rights()
    dataset.io.write_file(dataset.get_location("", file.name), file)