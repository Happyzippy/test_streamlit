"""Video transforms with OpenCV"""
import threading
import av
#import cv2
import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
import time

lock = threading.Lock()
img_container = {"img": None}

def callback(frame: av.VideoFrame) -> av.VideoFrame:
    img = frame.to_ndarray(format="bgr24")
    with lock:
        img_container["img"] = img
    return av.VideoFrame.from_ndarray(img, format="bgr24")


streamer = webrtc_streamer(
    key="opencv-filter",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={
        "video": {
            "width": {"min": 800, "ideal": 1920, "max": 1920},
        }
    },
    video_frame_callback=callback,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

st.markdown(
    "This demo is based on "
    "https://github.com/aiortc/aiortc/blob/2362e6d1f0c730a0f8c387bbea76546775ad2fe8/examples/server/server.py#L34. "  # noqa: E501
    "Many thanks to the project."
)

capture_button = st.button("Take image")

while capture_button and streamer.state.playing:
    with lock:
        img = img_container["img"]
        if img is not None:
            print(img.shape)
            st.image(img)
            break
    time.sleep(0.1)