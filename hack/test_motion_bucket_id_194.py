import logging
import time
import requests
import base64
import io
from PIL import Image
import datetime
import os
import concurrent.futures
import threading
import numpy as np
from dotenv import load_dotenv

load_dotenv()

motion_bucket_id = 194
text_prompt = "elon musk and beyonce on stage dancing, super realistic, full hd"

def text_to_image(text_prompt):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    body = {
        "steps": 40,
        "width": 1024,
        "height": 1024,
        "sampler": "K_DPM_2_ANCESTRAL",
        "seed": 0,
        "cfg_scale": 6,
        "samples": 1,
        "style_preset": "cinematic",
        "text_prompts": [{"text": text_prompt, "weight": 1}, {"text": "bad anatomy, bad hands, three hands, three legs, bad arms, missing legs, missing arms, poorly drawn face, bad face, fused face, cloned face, worst face, three crus, extra crus, fused crus, worst feet, three feet, fused feet, fused thigh, three thigh, fused thigh, extra thigh, worst thigh, missing fingers, extra fingers, ugly fingers, long fingers, horn, extra eyes, huge eyes, 2girl, amputation, disconnected limbs, cartoon, cg, 3d, unreal, animate, cameras", "weight": -1}],
    }
    headers = {
        "Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}",
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.text}")

    data = response.json()
    img_data = base64.b64decode(data["artifacts"][0]["base64"])
    img = Image.open(io.BytesIO(img_data))
    img = img.resize((768, 768))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def image_to_video(buffer, cfg_scale):
    url = "https://api.stability.ai/v2alpha/generation/image-to-video"
    body = {"seed": 0, "cfg_scale": cfg_scale, "motion_bucket_id": motion_bucket_id}
    files = {"image": buffer}
    headers = {"Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}"}
    print(f'Processing generation index: {cfg_scale}')
    response = requests.post(url, headers=headers, files=files, data=body)
    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.text}")
    data = response.json()
    return data["id"]

def check_video_status(generation_id):
    while True:
        response = requests.get(
            f"https://api.stability.ai/v2alpha/generation/image-to-video/result/{generation_id}",
            headers={'authorization': f"Bearer {os.getenv('STABILITY_API_KEY')}"}
        )
        if response.status_code == 202:
            time.sleep(5)
        elif response.status_code == 200:
            return response.content
        else:
            raise Exception(response.json())

def process_cfg_scale(cfg_scale, text_prompt, save_dir):
    try:
        image_buffer = text_to_image(text_prompt)
        video_generation_id = image_to_video(image_buffer, cfg_scale)  
        video_content = check_video_status(video_generation_id)
        with open(os.path.join(save_dir, f"{cfg_scale}_video.mp4"), 'wb') as file:
            file.write(video_content)
            print(f"Video saved to {os.path.join(save_dir, f'{cfg_scale}_video.mp4')}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

def handle_message(text_prompt) -> None:
    # The start time of the batch job
    start_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    # The directory to save all videos
    save_dir = os.path.join(os.getcwd(), start_time) + f"_bucket_id_{motion_bucket_id}"
    print(f"Saving videos to {save_dir}")
    # Create the directory if it does not exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for i in np.arange(0, 7, 2):  # Adjusted start parameter to 0
        i = round(i, 1)  # Round to 1 decimal point
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Start a new thread for each cfg_scale in the current batch
            seq = np.round(np.arange(i, min(i+2, 7), 0.1), 1)  # Adjusted range to generate 20 numbers
            executor.map(process_cfg_scale, seq, [text_prompt]*len(seq), [save_dir]*len(seq))

if __name__ == "__main__":
    handle_message(text_prompt)