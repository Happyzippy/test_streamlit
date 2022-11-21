import time

import streamlit as st
import numpy as np
import cv2
import threading
from brevettiai.platform import PlatformAPI
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av

lock = threading.Lock()
img_container = {"img": None}

if False:
    with st.form(key="platform-login"):
        user = st.text_input("User")
        password = st.text_input("Enter a password", type="password")
        st.form_submit_button("Login")

    web = PlatformAPI(username=user, password=password)
    dataset = st.selectbox("Datasets", options=[x.name for x in web.get_dataset()[:5]])

camera_info = st.empty()


def video_frame_callback(frame):
    img = frame.to_ndarray(format="rgb24")
    with lock:
        img_container["img"] = img
    frame = av.VideoFrame.from_ndarray(img.mean(-1).astype(np.uint8), format="gray8")
    #return frame

#st.camera_input("Take a picture")
st.file_uploader("TEST")

quit()
streamer = webrtc_streamer(
    key="example",
    #video_frame_callback=None,
    mode=WebRtcMode.RECVONLY,
    media_stream_constraints={"video": True},
    video_frame_callback=video_frame_callback,
    # desired_playing_state=True,
    # media_stream_constraints={
    #     "video": {
    #         "width": {"min": 800, "ideal": 1920, "max": 1920},
    #     }
    # },
)

# capture_button = st.button("Take image")
#
# while capture_button and streamer.state.playing:
#     with lock:
#         img = img_container["img"]
#         if img is not None:
#             print(img.shape)
#             st.image(img)
#             break
#     time.sleep(0.1)


#
#
# img_file_buffer = st.camera_input("Take a picture")
#
# if img_file_buffer is not None:
#     print("HERE")
#     # To read image file buffer with OpenCV:
#     bytes_data = img_file_buffer.getvalue()
#     img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)[..., ::-1]
#     FRAME_WINDOW = st.image(img)
