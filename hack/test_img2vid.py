import logging
import time
import requests
from PIL import Image
import os
import io
from dotenv import load_dotenv

load_dotenv()

cfg_scale = 3.6
bucket_id = 156

def image_to_video(buffer, text_prompts):
    url = "https://api.stability.ai/v2alpha/generation/image-to-video"
    body = {"seed": 0, "cfg_scale": cfg_scale, "motion_bucket_id": bucket_id}
    files = {"image": buffer}
    headers = {"Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}"}
    print(f'Processing generation: {text_prompts}')
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

def resize_image(image):
    img = Image.open(image)
    img = img.resize((768, 768))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def process_generation(image_path, save_dir):
    try:
        with open(image_path, 'rb') as file:
            image_buffer = file.read()
            image_buffer = resize_image(image_path)

        video_generation_id = image_to_video(image_buffer, image_path)  
        video_content = check_video_status(video_generation_id)

        with open(os.path.join(save_dir, f"video.mp4"), 'wb') as file:
            file.write(video_content)
            print(f"Video saved to {os.path.join(save_dir, f'video.mp4')}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    process_generation('test/image.png', 'test/outputs/')