from telegram import Bot, Update, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ParseMode, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram.utils.request import Request
from sqlalchemy import create_engine, Column, String, Enum, Integer, BigInteger, ForeignKey, Boolean, Index
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from contextlib import contextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from web3 import Web3
from threading import Thread
import logging
import enum
import time
import requests
import base64
import io
import json
from PIL import Image
import os

load_dotenv()
app_wallet_address = os.getenv('APP_WALLET_ADDRESS')

# Setup the bot
request = Request(con_pool_size=20)
bot = Bot(token=os.getenv('BOT_TOKEN'), request=request)
bot_admin_username = os.getenv('BOT_ADMIN_USERNAME')
# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Web3
infura_api_key = os.environ.get('INFURA_API_KEY')
w3 = Web3(Web3.HTTPProvider(f'https://goerli.infura.io/v3/{infura_api_key}'))
print(w3.isConnected()) 
# Your contract details
with open('abi.json', 'r') as abi_definition:
    contract_abi = json.load(abi_definition)
contract_address = os.getenv("CONTRACT_ADDRESS")
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Setup database
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True, unique=True)
    name = Column(String(255), nullable=True)
    username = Column(String(255), unique=True)
    status = Column(Enum('VIP', 'Regular'), default='Regular')
    wallet_address = Column(String(255), nullable=True)
    is_subscribed = Column(Boolean, default=False)
    message_id = Column(BigInteger, nullable=True)
    update_count = Column(Integer, default=0)
    credit = Column(Integer, default=30)

    __table_args__ = (Index('idx_username','username'),)

class TransactionState(enum.Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    FAILED = "Failed"

class Transaction(Base):
    __tablename__ = 'transaction'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'))
    wallet_address = Column(String(255), nullable=False)
    txn_hash = Column(String(255), nullable=False)
    state = Column(Enum(TransactionState), default=TransactionState.PENDING, nullable=False)

    user = relationship("User", backref=backref("tokens", cascade="all, delete-orphan"))

# sqlite settings
# engine = create_engine('sqlite:///sqlalchemy_example.db')
# Base.metadata.drop_all(bind=engine)
# Base.metadata.create_all(bind=engine)

# MYSQL Config
DATABASE_URL = f"mysql+mysqlconnector://{os.getenv('MYSQL_USERNAME')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}?charset=utf8mb4"  
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Database helper functions
def add_user_to_db(user_id=None, name=None, status="Regular", username=None):
    with session_scope() as session:
        user = None
        if user_id:
            user = session.query(User).filter_by(user_id=user_id).first()

        if user:
            user.status = status
            if name:
                user.name = name
            if user_id:
                user.user_id = user_id
            if username:
                user.username = username
            session.commit()
        else:
            user = User(user_id=user_id, name=name, status=status, username=username)
            session.add(user)
            session.commit()

def update_user_to_db(user_id=None, name=None, username=None):
    with session_scope() as session:
        user = None
        if username:
            user = session.query(User).filter_by(username=username).first()

        if user:
            user.name = name
            user.user_id = user_id

def get_balance(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    with session_scope() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        balance = user.credit
        if balance > 0:
            bot.send_message(chat_id=user_id, text=f"Your current balance is <b>{balance}</b>.", parse_mode=ParseMode.HTML)
        else:
            message += "\n\nYour free credit points have exhausted, please use /buy command to buy more credits."
            bot.send_message(chat_id=user_id, text=message)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "text_prompts": [{"text": text_prompt, "weight": 1}, {"text": "bad anatomy, bad hands, three hands, three legs, bad arms, missing legs, missing arms, poorly drawn face, bad face, fused face, cloned face, worst face, three crus, extra crus, fused crus, worst feet, three feet, fused feet, fused thigh, three thigh, fused thigh, extra thigh, worst thigh, missing fingers, extra fingers, ugly fingers, long fingers, horn, extra eyes, huge eyes, 2girl, amputation, disconnected limbs, cartoon, cg, 3d, unreal, animate, ((cameras))", "weight": -1}],
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

def image_to_video(buffer):
    url = "https://api.stability.ai/v2alpha/generation/image-to-video"
    body = {"seed": 0, "cfg_scale": 2.9, "motion_bucket_id": 156}
    files = {"image": buffer}
    headers = {"Authorization": f"Bearer {os.getenv('STABILITY_API_KEY')}"}
    response = requests.post(url, headers=headers, files=files, data=body)
    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.text}")
    data = response.json()
    return data["id"]

def check_video_status(generation_id, chat_id):
    while True:
        response = requests.get(
            f"https://api.stability.ai/v2alpha/generation/image-to-video/result/{generation_id}",
            headers={'authorization': f"Bearer {os.getenv('STABILITY_API_KEY')}"}
        )
        if response.status_code == 202:
            bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
            time.sleep(5)
        elif response.status_code == 200:
            return response.content
        else:
            raise Exception(response.json())

def async_generate(update, context, text_prompt, chat_id, chat_username, conversation_mode):
    try:
        image_buffer = text_to_image(text_prompt)
        
        if conversation_mode == TXT_TO_IMG:
            # Assuming this function generates an image and returns a buffer
            logger.info(f"Sending image to user @{chat_username}")
            bot.send_message(chat_id=chat_id, text="Sending image, please wait a few secs...")
            file_path = f"{chat_id}_image.jpg"
            with open(file_path, 'wb') as file:
                file.write(image_buffer)
            with open(file_path, 'rb') as image:
                bot.send_photo(chat_id=chat_id, photo=image)
            os.remove(file_path)
            # Deduct credits
            deduct_credits(update.effective_user.id, 1)
        else:
            # Assuming this function generates a video and returns an ID for status checking
            logger.info("Generating video...")
            bot.send_message(chat_id=chat_id, text="Generating video, please wait a few minutes...")
            video_generation_id = image_to_video(image_buffer)
            video_content = check_video_status(video_generation_id, chat_id)
            file_path = f"{chat_id}_video.mp4"
            with open(file_path, 'wb') as file:
                file.write(video_content)
            with open(file_path, 'rb') as video:
                bot.send_video(chat_id=chat_id, video=video)
            os.remove(file_path)
            # Deduct credits
            deduct_credits(update.effective_user.id, 3)
        logger.info(f"Generation complete for {update.effective_user.username}!")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        bot.send_message(chat_id=chat_id, text=f"An error occurred: {e}")

def handle_generation(update: Update, context: CallbackContext) -> None:
    conversation_mode = context.user_data.get('conversation_mode')
    text_prompt = context.user_data.get('prompt')
    logger.info(f"Received prompt: {text_prompt}")
    chat_id = update.effective_chat.id
    chat_username = update.effective_user.username

    # Send initial generation message
    bot.send_message(chat_id=chat_id, text=f"Generating:\n\n<i>{text_prompt}</i>\n\nLet the magic begin 🪄", parse_mode=ParseMode.HTML)
    context.user_data.pop('prompt', None)

    # Start the generation process in a separate thread
    thread = Thread(target=async_generate, args=(update, context, text_prompt, chat_id, chat_username, conversation_mode))
    thread.start()

    return ConversationHandler.END

def deduct_credits(user_id, credits):
    with session_scope() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            user.credit -= credits
            session.commit()

# resize any image to 768x768
def resize_image(image):
    img = Image.open(image)
    img = img.resize((768, 768))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def crop_image(image, target_size=(768, 768)):
    img = Image.open(image)

    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]

    if target_ratio > img_ratio:
        new_height = int(img.width / target_ratio)
        new_width = img.width
    else:
        new_width = int(img.height * target_ratio)
        new_height = img.height

    left = (img.width - new_width) / 2
    top = (img.height - new_height) / 2

    img = img.crop((left, top, left + new_width, top + new_height))
    img = img.resize(target_size)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'txt_to_vid':
        txt_to_vid_handler(update, context)
        pass
    elif query.data == 'txt_to_img':
        txt_to_img_handler(update, context)
        pass
    elif query.data == 'prompt_vid':
        context.user_data['conversation_mode'] = TXT_TO_VID
        handle_generation(update, context)
        pass
    elif query.data == 'prompt_img':
        context.user_data['conversation_mode'] = TXT_TO_IMG
        handle_generation(update, context)
        pass

def txt_to_img_handler(update, context):
    with session_scope() as session:
        user = session.query(User).filter(User.user_id == update.effective_user.id).first()
        if user.credit < 1:
            context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have enough credit to generate a video.")
            return ConversationHandler.END
        else:
            context.user_data['conversation_mode'] = TXT_TO_IMG
            context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter a text prompt to generate a image.\nOr type `/cancel` to cancel the operation.")
            return TXT_TO_IMG

def txt_to_vid_handler(update, context):
    with session_scope() as session:
        user = session.query(User).filter(User.user_id == update.effective_user.id).first()
        if user:
            if user.credit < 3:
                context.bot.send_message(chat_id=update.effective_chat.id, text="You don't have enough credit to generate a video.")
                return ConversationHandler.END
            else:
                context.user_data['conversation_mode'] = TXT_TO_VID
                context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter a text prompt to generate a video.\nOr type /cancel to cancel the operation.")
                return TXT_TO_VID
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Please use /start command to create an account first.")
            return ConversationHandler.END

def calculate_credit_points(token_amount):
    if token_amount >= 25000:
        return 500
    elif token_amount >= 10000:
        return 120
    elif token_amount >= 5000:
        return 55
    elif token_amount >= 2000:
        return 21
    elif token_amount >= 1000:
        return 10
    else:
        return 0

def buy(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    message = f"""
Click on the link below to purchase credit points with $SORAAI
https://
10 pts - 1000 $SORAAI
21 pts - 2000 $SORAAI
55 pts - 5000 $SORAAI
120 pts - 10000 $SORAAI
500 pts - 25000 $SORAAI
    """

    update.message.reply_text(message)

    with session_scope() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user and user.wallet_address:
            # User has an existing wallet address
            update.message.reply_text(f"Current Wallet Address: <code>{user.wallet_address}</code>\nDo you want to update it?\nReply with <b><u>Yes</u></b> to confirm or send a new address to update.\nOr use <a>/cancel</a> to cancel the operation.", parse_mode=ParseMode.HTML)
            return WALLET_ADDRESS
        else:
            # User does not have a wallet address
            update.message.reply_text("Please send your wallet address to bond with your user record.\nOr use /cancel to cancel the operation.")
            return WALLET_ADDRESS

def process_wallet_address(update: Update, context: CallbackContext) -> int:
    wallet_address = update.message.text
    user_id = update.effective_user.id
    
    with session_scope() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            # Check if the user replied with 'yes'
            if wallet_address.lower() == 'yes':
                if user.wallet_address:
                    # User confirmed to use the existing wallet address
                    update.message.reply_text(f"Okay, we will use your existing wallet address: <code>{user.wallet_address}</code>", parse_mode=ParseMode.HTML)
                    context.user_data['wallet_address'] = user.wallet_address
            else:
                # User confirmed but no existing wallet address found
                update.message.reply_text(f"Updated wallet address to <code>{wallet_address}</code>", parse_mode=ParseMode.HTML)
                user.wallet_address = wallet_address
                session.commit()
                context.user_data['wallet_address'] = wallet_address 

            update.message.reply_text(f"Price List for credits:\n100 tokens = 1 credit point\n500 tokens = 6\n1000 tokens = 13\n5000 tokens = 70\n10000 tokens = 150\n\nSend the token to this address: <code>{app_wallet_address}</code>\nThen send your transaction's txn hash to confirm the deposit.\nCredit will be released once the confirmation is done\nOr use <a>/cancel</a> to cancel the operation.", parse_mode=ParseMode.HTML)
            return TXN_HASH 
        else:
            update.message.reply_text("Error: User not found.")
            return ConversationHandler.END

def process_transaction(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    wallet_address = context.user_data.get('wallet_address')  
    txn_hash = update.message.text

    # Check if wallet_address is available
    if not wallet_address:
        update.message.reply_text("Wallet address not found.\nPlease start over by using <a>/buy</a>.", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    with session_scope() as session:
        user = session.query(User).filter(User.user_id == user_id).first()
        if user:
            # Create a new transaction record in the user_tokens table
            transaction = Transaction(
                user_id=user_id,
                wallet_address=wallet_address,
                txn_hash=txn_hash
            )
            session.add(transaction)
            session.commit()

            update.message.reply_text("Transaction hash received.\nWe are now verifying your transaction.\nYou will be notified once the verification is complete.", parse_mode=ParseMode.HTML)

            # Start the background thread to monitor the transaction
            thread = Thread(target=monitor_transaction, args=(user_id, txn_hash, update.message.chat_id, wallet_address))
            thread.start()
        else:
            update.message.reply_text("Error: User not found.")
    return ConversationHandler.END


def from_token_base_unit(value, decimals=9):
    return value / (10 ** decimals)

def monitor_transaction(user_id, txn_hash, chat_id, wallet_address):
    to_account = w3.toChecksumAddress(app_wallet_address)
    transaction_confirmed = False
    attempts = 0
    max_attempts = 10

    while not transaction_confirmed and attempts < max_attempts:
        try:
            receipt = w3.eth.getTransactionReceipt(txn_hash)
            if not receipt:
                time.sleep(60)
                attempts += 1
                continue
            
            if receipt['from'].lower() != wallet_address.lower():
                bot.send_message(chat_id=chat_id, text=f"The transaction did not come from the expected address. Please check your inputs and try again.")
                return

            transfer_events = contract.events.Transfer().processReceipt(receipt)
            if not transfer_events:
                time.sleep(60)
                attempts += 1
                continue

            for event in transfer_events:
                event_args = event['args']
                if event_args['to'].lower() == to_account.lower():
                    token_amount = from_token_base_unit(event_args['value'], 9)
                    credits = calculate_credit_points(token_amount)
                    if credits > 0:
                        transaction_confirmed = True
                        with session_scope() as session:
                            # Update user credits
                            user = session.query(User).filter(User.user_id == user_id).first()
                            if user:
                                user.credit += credits
                                session.commit()
                                
                            # Update the transaction record to "Confirmed"
                            transaction = session.query(Transaction).filter(Transaction.txn_hash == txn_hash).first()
                            if transaction:
                                transaction.state = TransactionState.CONFIRMED
                                session.commit()

                            # Send confirmation message to the user
                            bot.send_message(chat_id=chat_id, text=f"Your transaction has been confirmed. {credits} credit(s) have been added to your account.")
                        break
            if not transaction_confirmed:
                time.sleep(60)
                attempts += 1
        except Exception as e:
            print(f"{e}\nAttemps: {attempts}\nUser ID: {user_id}")
            attempts += 1
            time.sleep(60)
            if attempts == max_attempts:
                bot.send_message(chat_id=chat_id, text=f"An error occurred while verifying your transaction. Please contact support {bot_admin_username}.")
                return
            continue

def handle_prompt(update: Update, context: CallbackContext) -> None:

    chat_id = update.effective_chat.id
    prompt = update.message.text
    context.user_data['prompt'] = prompt

    keyboard = [
        [InlineKeyboardButton("txt-to-vid", callback_data='prompt_vid'), InlineKeyboardButton("txt-to-img", callback_data='prompt_img')],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=chat_id, text=f"Prompts received:\n\n<i>{prompt}</i>\n\nChoose txt-to-img or txt-to-vid", parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def handle_prompts_list(update: Update, context: CallbackContext) -> None:

    prompts = [
    "a futuristic drone race at sunset on the planet mars",
    "two golden retrievers podcasting on top of a mountain",
    "an instructional cooking session for homemade gnocchi hosted by a grandmother social media influencer set in a rustic Tuscan country kitchen with cinematic lighting",
    "a cat waking up its sleeping owner demanding breakfast. The owner tries to ignore the cat, but the cat tries new tactics and finally the owner pulls out a secret stash of treats from under the pillow to hold the cat off a little longer.",
    "a man BASE jumping over tropical hawaii waters. His pet macaw flies alongside him",
    "an adorable happy otter confidently stands on a surfboard wearing a yellow lifejacket, riding along turquoise tropical waters near lush tropical islands, 3D digital render art style.",
    "a flock of paper airplanes flutters through a dense jungle, weaving around trees as if they were migrating birds.",
    "a beautiful silhouette animation shows a wolf howling at the moon, feeling lonely, until it finds its pack.",
    "a corgi vlogging itself in tropical Maui.",
    "A super car driving through city streets at night with heavy rain everywhere, shot from behind the car as it drives",
    "a tortoise whose body is made of glass, with cracks that have been repaired using kintsugi, is walking on a black sand beach at sunset",
    "an older man with gray hair and glasses devours a delicious cheese burger. the bun is speckled with sesame seeds, fresh lettuce, a slice of cheese, and a golden brown beef patty. his eyes are closed in enjoyment as he takes a bite",
    "F1 Race Through San Francisco",
    "A young professional product reviewer in a well lit video studio is surrounded by gadgets and technology, sitting in front of a computer with two displays. He's holding a cinema camera as he ponders what video to make next. He is in focus",
    "",
    "A timelapse closeup of a 3D printer printing a small red cube in an office with dim lighting",
    "A scuba diver discovers a hidden futuristic shipwreck, with cybernetic marine life and advanced alien technology",
    "new York City submerged like Atlantis. Fish, whales, sea turtles and sharks swim through the streets of New York.",
    "tour of an art gallery with many beautiful works of art in different styles.",
    "a Chinese Lunar New Year celebration video with Chinese Dragon.",
    "a Samoyed and a Golden Retriever dog are playfully romping through a futuristic neon city at night. The neon lights emitted from the nearby buildings glistens off of their fur.",
    "the story of a robot’s life in a cyberpunk setting."
    ]

    keyboard = [[item] for item in prompts]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text(f"Here's some prompts for you to try: ", reply_markup=reply_markup)

def help_handler(update: Update, context: CallbackContext) -> None:
    message = f"""
Steps to generate video scenes/images ?
                
1. Simply choose module "txt-to-vid" OR "txt-to-img"
2. Enter the text prompt (a detailed prompt generates better results, /prompts for text prompt examples)
3. Let the magic begin 🪄

Processing time:
Txt-to-vid : 2-3 min
Txt-to-img : 20-30 sec

Initial free credits: 30
Consumption of credits,
Txt-to-vid : 3 credit pts.
Txt-to-img : 1 credit pts. 
"""
    update.message.reply_text(message)

def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    with session_scope() as session:
        user = session.query(User).filter(User.user_id == update.effective_user.id).first()
        if not user:
            add_user_to_db(user_id=update.effective_user.id, name=update.effective_user.first_name, username=update.effective_user.username, status="Regular")
            context.bot.send_message(chat_id=chat_id,text="✅Account created successfully.")
        else:
            update_user_to_db(user_id=update.effective_user.id, name=update.effective_user.first_name, username=update.effective_user.username)

    context.bot.send_message(chat_id=chat_id,text=f"""
Sora AI bot is powered by token $SORAAI (t.me/SoraAIPortal)

What can this bot do ?

Sora AI is a cutting-edge text-to-video & txt-to-image model, designed to transform descriptive text prompts into realistic and imaginative video scenes & and can also generate videos from still images. Sora AI exemplifies a significant advancement in AI by focusing on simulating the physical world in motion, which is crucial for addressing real-world interaction challenges.

Steps to generate video scenes ?

1. Simply enter your prompts or pick one using /prompts
2. Choose txt-to-vid or txt-to-img
3. Let the magic begin 🪄

Initial Credits: 30
txt-to-vid consumes 3 credits
txt-to-img consumes 1 credit
Credit points can be purchased with $SORAAI (use command /buy for detailed instruction)
    """)

def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'The operation has been cancelled.', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

TXT_TO_IMG = 1
TXT_TO_VID = 2
WALLET_ADDRESS, TXN_HASH = range(2)
txt_to_img_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(txt_to_img_handler, pattern='txt_to_img'),
        CommandHandler('txt_to_img', txt_to_img_handler)    
    ],
    states={
        TXT_TO_IMG: [MessageHandler(Filters.text & ~Filters.command, handle_generation)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    run_async=True
)

txt_to_vid_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(txt_to_vid_handler, pattern='txt_to_vid'),
        CommandHandler('txt_to_vid', txt_to_vid_handler)  
    ],
    states={
        TXT_TO_VID: [MessageHandler(Filters.text & ~Filters.command, handle_generation)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    run_async=True
)

buy_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('buy', buy)],
    states={
        WALLET_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, process_wallet_address)],
        TXN_HASH: [MessageHandler(Filters.text & ~Filters.command, process_transaction)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    run_async=True
)


def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot=bot, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Register command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", get_balance))
    dp.add_handler(CommandHandler("prompts", handle_prompts_list))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_prompt, run_async=True))
    dp.add_handler(txt_to_vid_conversation_handler)
    dp.add_handler(txt_to_img_conversation_handler)
    dp.add_handler(buy_conversation_handler)
    # dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_generation))
    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()