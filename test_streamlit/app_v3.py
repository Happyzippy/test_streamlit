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
    img = frame.to_ndarray(format="rgb24")
    with lock:
        img_container["img"] = img
    return av.VideoFrame.from_ndarray(img, format="rgb24")


streamer = webrtc_streamer(
    key="opencv-filter",
    mode=WebRtcMode.SENDRECV,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={
        "video": {
            "width": {"min": 800, "ideal": 1920, "max": 1920},
        },
        "audio": False
    },
    video_frame_callback=callback,
    async_processing=True,
)

capture_button = st.button("Take image")
st.file_uploader("Upload")
while capture_button and streamer.state.playing:
    with lock:
        img = img_container["img"]
        if img is not None:
            print(img.shape)
            st.image(img)
            break
    time.sleep(0.1)