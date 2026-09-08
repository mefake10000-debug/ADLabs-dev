#!/bin/sh
set -e

echo "[RTSP Simulator] Starting MediaMTX RTSP Server..."
/usr/local/bin/mediamtx &
MEDIAMTX_PID=$!

echo "[RTSP Simulator] Waiting for MediaMTX to bind port 8554..."
sleep 3

# Function to loop a video stream to RTSP
stream_video() {
    STREAM_PATH=$1
    VIDEO_FILE=$2
    if [ -f "$VIDEO_FILE" ]; then
        echo "[RTSP Simulator] Streaming $VIDEO_FILE to rtsp://localhost:8554/$STREAM_PATH ..."
        ffmpeg -re -stream_loop -1 -i "$VIDEO_FILE" -c:v libx264 -preset ultrafast -tune zerolatency -b:v 1500k -r 15 -f rtsp -rtsp_transport tcp "rtsp://localhost:8554/$STREAM_PATH" > /dev/null 2>&1 &
    else
        echo "[RTSP Simulator] Warning: $VIDEO_FILE not found. Creating a synthetic color-test feed for $STREAM_PATH..."
        ffmpeg -re -f lavfi -i "testsrc=size=1280x720:rate=15" -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp -rtsp_transport tcp "rtsp://localhost:8554/$STREAM_PATH" > /dev/null 2>&1 &
    fi
}

# Start streaming feeds
stream_video "entrance" "/app/data/sample_videos/entrance_sample.mp4"
stream_video "checkout" "/app/data/sample_videos/checkout_sample.mp4"

echo "[RTSP Simulator] Streams are live at:"
echo "  - rtsp://localhost:8554/entrance"
echo "  - rtsp://localhost:8554/checkout"

# Wait on MediaMTX
wait $MEDIAMTX_PID

