import streamlit as st
import numpy as np
import cv2

img_file_buffer = st.camera_input("Take a picture")

if img_file_buffer is not None:
    print("HERE")
    # To read image file buffer with OpenCV:
    bytes_data = img_file_buffer.getvalue()
    img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)[..., ::-1]
    FRAME_WINDOW = st.image(img)