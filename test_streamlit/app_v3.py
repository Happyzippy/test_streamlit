import streamlit as st
import numpy as np
import cv2
from brevettiai.platform import PlatformAPI

user = st.text_input("User")
password = st.text_input("Enter a password", type="password")

web = PlatformAPI(username=user, password=password)
dataset = st.selectbox("Datasets", options=[x.name for x in web.get_dataset()[:5]])

img_file_buffer = st.camera_input("Take a picture")

if img_file_buffer is not None:
    print("HERE")
    # To read image file buffer with OpenCV:
    bytes_data = img_file_buffer.getvalue()
    img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)[..., ::-1]
    FRAME_WINDOW = st.image(img)