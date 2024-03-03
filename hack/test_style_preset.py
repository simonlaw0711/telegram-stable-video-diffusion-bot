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
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

cfg_scale = 2.9
bucket_id = 156

# text_prompts = [
#     "a futuristic drone race at sunset on the planet mars",
#     "two golden retrievers podcasting on top of a mountain",
#     "an instructional cooking session for homemade gnocchi hosted by a grandmother social media influencer set in a rustic Tuscan country kitchen with cinematic lighting",
#     "the camera directly faces colorful buildings in burano italy. An adorable dalmation looks through a window on a building on the ground floor. Many people are walking and cycling along the canal streets in front of the buildings.",
#     "a litter of golden retriever puppies playing in the snow. Their heads pop out of the snow, covered in.",
#     "close-up shot of a chameleon showcases its striking color changing capabilities. The background is blurred, drawing attention to the animal's striking appearance.",
#     "a cat waking up its sleeping owner demanding breakfast. The owner tries to ignore the cat, but the cat tries new tactics and finally the owner pulls out a secret stash of treats from under the pillow to hold the cat off a little longer.",
#     "an adorable happy otter confidently stands on a surfboard wearing a yellow lifejacket, riding along turquoise tropical waters near lush tropical islands, 3D digital render art style.",
#     "a flock of paper airplanes flutters through a dense jungle, weaving around trees as if they were migrating birds.",
#     "a beautiful silhouette animation shows a wolf howling at the moon, feeling lonely, until it finds its pack.",
#     "a corgi vlogging itself in tropical Maui.",
#     "new York City submerged like Atlantis. Fish, whales, sea turtles and sharks swim through the streets of New York.",
#     "tour of an art gallery with many beautiful works of art in different styles.",
#     "a Chinese Lunar New Year celebration video with Chinese Dragon.",
#     "a Samoyed and a Golden Retriever dog are playfully romping through a futuristic neon city at night. The neon lights emitted from the nearby buildings glistens off of their fur.",
#     "the story of a robot's life in a cyberpunk setting.",
#     "a drone camera circles around a beautiful historic church built on a rocky outcropping along the Amalfi Coast, the view showcases historic and magnificent architectural details and tiered pathways and patios,the view is stunning captured with beautiful photography.",
#     "a white and orange tabby cat is seen happily darting through a dense garden, as if chasing something. its eyes are wide and happy as it jogs forward, scanning the branches, flowers, and leaves as it walks. the path is narrow as it makes its way between all the plants.",
#     "several giant wooly mammoths approach treading through a snowy meadow, their long wooly fur lightly blows in the wind as they walk, snow covered trees and dramatic snow capped mountains in the distance, mid afternoon light with wispy clouds and a sun high in the distance",
#     "A timelapse closeup of a 3D printer printing a small red cube in an office with dim lighting.",
#     "A young professional product reviewer in a well lit video studio is surrounded by gadgets and technology, sitting in front of a computer with two displays. He's holding a cinema camera as he ponders what video to make next. He is in focus",
#     "an older man with gray hair and glasses devours a delicious cheese burger. the bun is speckled with sesame seeds, fresh lettuce, a slice of cheese, and a golden brown beef patty. his eyes are closed in enjoyment as he takes a bite.",
#     "A stop motion Timelapse of a caterpillar's metamorphosis into a butterfly",
#     "A super car driving through city streets at night with heavy rain everywhere, shot from behind the car as it drives",
#     "golden retriever in sunglasses sunbathing on a beach in Hawaii",
#     "F1 Race Through San Francisco",
#     "a man BASE jumping over tropical hawaii waters. His pet macaw flies alongside him",
#     "A scuba diver discovers a hidden futuristic shipwreck, with cybernetic marine life and advanced alien technology",
#     "Monkey Playing Chess in a Park",
#     "a tortoise whose body is made of glass, with cracks that have been repaired using kintsugi, is walking on a black sand beach at sunset"
# ]

# text_prompts = [
#     "Realistic turtles swimming in the water with lots of Coral reef around",
#     "Super anime, super hd, samurai sitting on top of temple gazing into the city",
#     "Mario eating mushroom, getting high with rainbow everywhere",
#     "A gorgeously rendered papercraft world of a planet, rife with colorful stars",
#     "boy in bubble floating through space, bright stars and beautiful planets, super hd, super realistic",
#     "anime, hd, hard working blacksmith making a sword, in the hot mills",
#     "Super realistic, super hd, Pikachu hold bitcoin at a park",
#     "shiba inu wearing a chain with explosion in the background",
#     "the sun 4k hd high quality vibrant colors,  ultra realisticm cinematic",
#     "a sunset by the beach 4k hd high quality vibrant colors,  ultra realisticm cinematic",
#     "Super realistic, super hd, ethereum convention in Denver, ethereum futuristic logo in the center, full of business people sitting around chatting",
#     "Super cartoon, super hd, yeti riding a jet with sunglasses on",
#     "Super realistic, super hd, meteor strikes castle, castle is on fire",
#     "Super realistic, super hd, willy Wonka chocolate factory, tour inside with magical mushrooms, chocolate, lollipop, rainbows",
#     "Super realistic, super hd, pirate protecting his chest filled with bitcoins",
#     "Super realistic, super hd, lotus floating on water with rays of light beaming from the sky.",
#     "A movie trailer featuring the adventures of the 30 year old space man wearing a red wool knitted motorcycle helmet, blue sky, salt desert, cinematic style, shot on 35mm film, vivid colors.",
#     "A monkey with a gun made out of bananas on a mountain. 4k HD, high quality, bright colors",
#     "Lamborghini on a moon super HD high quality 4K r resolution vibrant color,  Super detailed",
#     "Joe Biden sitting on a pile of Bitcoin. Super HD and cartoon",
#     "Purple frog in a suit with a purple background. HD quality, high quality, 4D",
#     "dragon sleeping next to a pile of bitcoin and gold in HD high quality",
#     "super anime, super hd, samurai walking through a bamboo forest",
#     "super realistic, super hd, bitcoin floating in the air with 1000 people worshipping it",
#     "a rocketship flying around the sun. hyper realistic"
# ]

art_style = ["3d-model", "analog-film", "anime", "cinematic", "comic-book", "digital-art", "enhance", "fantasy-art", "isometric", "line-art", "low-poly", "modeling-compound", "neon-punk", "origami", "photographic", "pixel-art", "tile-texture"]

text_prompts = [
    "An underwater odyssey through a vibrant coral reef, teeming with colorful fish and gentle sea turtles."
]

async def text_to_image(text_prompt, style_preset):
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    headers = {
        "Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}",
    }
    
    body = {
        "steps": 40,
        "width": 1024,
        "height": 1024,
        "sampler": "K_DPM_2_ANCESTRAL",
        "seed": 0,
        "cfg_scale": 6,
        "samples": 1,
        "style_preset": style_preset,
        "text_prompts": [{"text": text_prompt, "weight": 1}, {"text": "bad anatomy, bad hands, three hands, three legs, bad arms, missing legs, missing arms, poorly drawn face, bad face, fused face, cloned face, worst face, three crus, extra crus, fused crus, worst feet, three feet, fused feet, fused thigh, three thigh, fused thigh, extra thigh, worst thigh, missing fingers, extra fingers, ugly fingers, long fingers, horn, extra eyes, huge eyes, 2girl, amputation, disconnected limbs, cartoon, cg, 3d, unreal, animate, ((cameras))", "weight": -1}],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=body) as response:
            if response.status != 200:
                raise Exception(f"Non-200 response: {response.text}")

            data = await response.json()
            img_data = base64.b64decode(data["artifacts"][0]["base64"])
            img = Image.open(io.BytesIO(img_data))
            img = img.resize((768, 768))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            return buffer.getvalue()

async def image_to_video(session, buffer, i):
    url = "https://api.stability.ai/v2alpha/generation/image-to-video"
    body = {"seed": 0, "cfg_scale": cfg_scale, "motion_bucket_id": bucket_id}
    headers = {"Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}"}
    print(f'Processing generation: {i}')

    data = aiohttp.FormData()
    data.add_field('image', buffer, filename='image.jpg')
    for key, value in body.items():
        data.add_field(key, str(value))

    async with session.post(url, headers=headers, data=data) as response:
        if response.status != 200:
            raise Exception(f"Non-200 response: {await response.text()}")
        data = await response.json()
        return data["id"]

async def check_video_status(session, generation_id):
    while True:
        async with session.get(
                f"https://api.stability.ai/v2alpha/generation/image-to-video/result/{generation_id}",
                headers={'authorization': f"Bearer {os.getenv('STABILITY_API_KEY')}"}
        ) as response:
            if response.status == 202:
                await asyncio.sleep(5)
            elif response.status == 200:
                return await response.content.read()
            else:
                raise Exception(await response.text())

async def process_generation(text_prompt, save_dir):
    try:
        tasks = [text_to_image(text_prompt, style) for style in art_style]
        image_buffers = await asyncio.gather(*tasks)

        async with aiohttp.ClientSession() as session:
            video_tasks = [generate_video(session, image_buffer, text_prompt, i, save_dir) for i, image_buffer in enumerate(image_buffers)]
            await asyncio.gather(*video_tasks)
    except Exception as e:
        logging.error(f"An error occurred: {e}")

async def generate_video(session, image_buffer, text_prompt, i, save_dir):
    video_generation_id = await image_to_video(session, image_buffer, art_style[i])
    video_content = await check_video_status(session, video_generation_id)
    with open(os.path.join(save_dir, f"{text_prompt}_{art_style[i]}_video.mp4"), 'wb') as file:
        file.write(video_content)
        print(f"Video saved to {os.path.join(save_dir, f'{text_prompt}_{art_style[i]}_video.mp4')}")


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

async def handle_message(prompts):
    # The start time of the batch job
    start_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    # The directory to save all videos
    save_dir = os.path.join(os.getcwd(), start_time) + f"_style_preset_{bucket_id}_{str(cfg_scale).replace('.', '_')}"
    print(f"Saving videos to {save_dir}")
    # Create the directory if it does not exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for prompt_chunk in chunks(prompts, 20):
        tasks = [process_generation(prompt, save_dir) for prompt in prompt_chunk]
        await asyncio.gather(*tasks)

# Execute the function

if __name__ == "__main__":
    asyncio.run(handle_message(text_prompts))