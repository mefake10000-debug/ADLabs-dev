import cv2
import numpy as np
import os
import math

def create_entrance_video(output_path: str, width: int = 1280, height: int = 720, fps: int = 15, duration_sec: int = 20):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = fps * duration_sec
    print(f"Generating entrance simulation video: {output_path} ({total_frames} frames)...")

    # Pedestrian paths (simulating people entering and exiting)
    pedestrians = [
        {"start_frame": 10, "start_pos": (640, 50), "end_pos": (640, 680), "color": (60, 60, 220), "label": "Shopper 1"},
        {"start_frame": 40, "start_pos": (500, 680), "end_pos": (500, 50), "color": (220, 60, 60), "label": "Shopper 2"},
        {"start_frame": 80, "start_pos": (700, 50), "end_pos": (700, 680), "color": (60, 180, 60), "label": "Shopper 3"},
        {"start_frame": 120, "start_pos": (580, 50), "end_pos": (580, 680), "color": (180, 60, 180), "label": "Shopper 4"},
        {"start_frame": 160, "start_pos": (620, 680), "end_pos": (620, 50), "color": (60, 180, 220), "label": "Shopper 5"},
        {"start_frame": 200, "start_pos": (750, 50), "end_pos": (750, 680), "color": (200, 200, 60), "label": "Shopper 6"},
    ]

    for frame_idx in range(total_frames):
        # Background: Store floor and doorway
        frame = np.full((height, width, 3), (235, 235, 235), dtype=np.uint8)

        # Entrance doorway visual guidelines
        cv2.rectangle(frame, (350, 0), (930, height), (210, 210, 210), -1)
        cv2.line(frame, (350, 0), (350, height), (170, 170, 170), 2)
        cv2.line(frame, (930, 0), (930, height), (170, 170, 170), 2)

        # Tripwire line reference (y=360)
        cv2.line(frame, (400, 360), (880, 360), (140, 220, 140), 2)
        cv2.putText(frame, "[Entrance Threshold]", (410, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 160, 100), 1)

        # Draw moving pedestrians
        for ped in pedestrians:
            if ped["start_frame"] <= frame_idx <= ped["start_frame"] + 90:
                progress = (frame_idx - ped["start_frame"]) / 90.0
                curr_x = int(ped["start_pos"][0] + progress * (ped["end_pos"][0] - ped["start_pos"][0]))
                curr_y = int(ped["start_pos"][1] + progress * (ped["end_pos"][1] - ped["start_pos"][1]))

                # Draw simulated pedestrian bounding box / body
                w, h = 60, 140
                top_left = (curr_x - w // 2, curr_y - h)
                bottom_right = (curr_x + w // 2, curr_y)

                # Simulated person torso & head
                cv2.rectangle(frame, top_left, bottom_right, ped["color"], -1)
                cv2.circle(frame, (curr_x, curr_y - h + 20), 18, (200, 180, 160), -1)
                cv2.putText(frame, ped["label"], (top_left[0], top_left[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)

        cv2.putText(frame, f"Frame: {frame_idx}/{total_frames} (Simulated Entrance CCTV)", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
        out.write(frame)

    out.release()
    print(f"Generated: {output_path}")

def create_checkout_video(output_path: str, width: int = 1280, height: int = 720, fps: int = 15, duration_sec: int = 20):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = fps * duration_sec
    print(f"Generating checkout simulation video: {output_path} ({total_frames} frames)...")

    # Fixed positions of customers standing in line waiting to pay
    queue_slots = [
        (650, 320, "Customer A"),
        (650, 420, "Customer B"),
        (650, 520, "Customer C"),
        (650, 620, "Customer D"),
    ]

    for frame_idx in range(total_frames):
        frame = np.full((height, width, 3), (240, 240, 240), dtype=np.uint8)

        # Cashier counter area
        cv2.rectangle(frame, (500, 120), (800, 220), (160, 130, 90), -1)
        cv2.putText(frame, "CASHIER COUNTER #1", (530, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Queue zone boundary guideline
        pts = np.array([[450, 250], [850, 250], [900, 650], [400, 650]], np.int32)
        cv2.polylines(frame, [pts], isClosed=True, color=(120, 180, 240), thickness=2)
        cv2.putText(frame, "[Checkout Queue Staging]", (410, 675), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 140, 200), 1)

        # Draw waiting customers with slight breathing/swaying motion
        num_customers = 4 if frame_idx > 30 else 2
        for i in range(num_customers):
            x, y, label = queue_slots[i]
            # Add small random sway
            sway_x = int(math.sin(frame_idx * 0.1 + i) * 3)
            sway_y = int(math.cos(frame_idx * 0.08 + i) * 2)

            curr_x = x + sway_x
            curr_y = y + sway_y
            w, h = 60, 130
            top_left = (curr_x - w // 2, curr_y - h)
            bottom_right = (curr_x + w // 2, curr_y)

            cv2.rectangle(frame, top_left, bottom_right, (180, 100, 50), -1)
            cv2.circle(frame, (curr_x, curr_y - h + 18), 16, (210, 190, 170), -1)
            cv2.putText(frame, f"{label} (Wait)", (top_left[0] - 10, top_left[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 40, 40), 1)

        cv2.putText(frame, f"Frame: {frame_idx}/{total_frames} (Simulated Cashier CCTV)", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
        out.write(frame)

    out.release()
    print(f"Generated: {output_path}")

if __name__ == "__main__":
    create_entrance_video("data/sample_videos/entrance_sample.mp4")
    create_checkout_video("data/sample_videos/checkout_sample.mp4")

