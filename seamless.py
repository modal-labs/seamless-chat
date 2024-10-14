import modal
from pydantic import BaseModel
from typing import Literal, Optional
from pathlib import Path

app = modal.App("seamless-chat")

backend_image = modal.Image.debian_slim().apt_install("ffmpeg").pip_install("transformers", "sentencepiece", "torchaudio", "soundfile", "numpy")
frontend_image = modal.Image.debian_slim().pip_install("jinja2")

users = modal.Dict.from_name("seamless-users", create_if_missing=True)
rooms = modal.Dict.from_name("seamless-rooms", create_if_missing=True)
message_content = modal.Dict.from_name("seamless-message-content", create_if_missing=True)
message_queue = modal.Queue.from_name("seamless-message-queue", create_if_missing=True)


room_names = [
    'dog', 'cat', 'lion', 'tiger', 'elephant', 'giraffe', 'zebra', 'monkey', 'rabbit', 
    'deer', 'bear', 'wolf', 'fox', 'squirrel', 'kangaroo', 'panda', 'koala', 
    'buffalo', 'crocodile', 'alligator', 'penguin', 
    'flamingo', 'eagle', 'owl', 'parrot', 'peacock', 'sparrow', 'duck', 'goose', 
    'chicken', 'turkey', 'cow', 'sheep', 'goat', 'horse', 'donkey', 'pig', 'bat', 
    'shark', 'whale', 'dolphin', 'octopus', 'jellyfish', 'crab', 'lobster', 'turtle', 
    'snake', 'frog', 'lizard'
]

@app.cls(
    gpu="H100", 
    image=backend_image,
    container_idle_timeout=240,
    timeout=3600,
    concurrency_limit=5,
    allow_concurrent_inputs=5,
    keep_warm=1
)
class SeamlessM4T:
    @modal.build()
    def build(self):
        from huggingface_hub import snapshot_download

        snapshot_download("facebook/seamless-m4t-v2-large")
    
    @modal.enter()
    def enter(self):
        import torch
        from transformers import AutoProcessor, SeamlessM4Tv2Model

        self.processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
        self.model = torch.compile(SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large").to("cuda"))
    

    def create_user(self, user_name: str, lang: str):
        import uuid

        user_id = str(uuid.uuid4())
        users[user_id] = {
            "name": user_name,
            "lang": lang,
        }
        return user_id
    
    def create_room(self):
        import uuid, random

        room_id = str(uuid.uuid4())
        room_name = random.choice(room_names)
        rooms[room_id] = {
            "name": room_name,
            "members": [],
        }
        return room_id, room_name

    def join_room(self, user_id: str, room_id: str):
        if user_id not in rooms[room_id]["members"]:
            rooms[room_id] = {
                "name": rooms[room_id]["name"],
                "members": rooms[room_id]["members"] + [user_id],
            }

        return rooms[room_id]

    def leave_room(self, user_id: str, room_id: str):
        if user_id in rooms[room_id]["members"]:
            members = [member for member in rooms[room_id]["members"] if member != user_id]
            rooms[room_id] = {
                "name": rooms[room_id]["name"],
                "members": members,
            }

    def _translate(self, inputs, tgt_lang: str):
        output = self.model.generate(**inputs, tgt_lang=tgt_lang, return_intermediate_token_ids=True)
        audio_array = output[0].cpu().numpy().squeeze()
        text = self.processor.decode(output[2].tolist()[0], skip_special_tokens=True)
        return text, audio_array
    
    def translate_text(self, text: str, src_lang: str, tgt_lang: str):
        inputs = self.processor(text=text, src_lang=src_lang, return_tensors="pt").to("cuda")
        return self._translate(inputs, tgt_lang)
    
    def translate_audio(self, audio: str, tgt_lang: str):
        import io, torchaudio, base64

        audio_buffer = io.BytesIO(base64.b64decode(audio.split(",")[1]))
        audio, orig_freq = torchaudio.load(audio_buffer)
        audio = torchaudio.functional.resample(audio, orig_freq, 16000)

        inputs = self.processor(audios=audio, return_tensors="pt", sampling_rate=16000).to("cuda")
        return self._translate(inputs, tgt_lang)

    def send_message(self, user_id: str, room_id: str, message_type: Literal["text", "audio"], content: str):
        import uuid

        user = users.get(user_id)
        message_id = str(uuid.uuid4())
        message_content[message_id] = content

        room_members = rooms[room_id]["members"]
        for member_id in room_members:
            message_data = {
                "user_id": user_id,
                "user_name": user["name"],
                "message_type": message_type,
                "message_id": message_id,
                "lang": user["lang"]
            }
            message_queue.put(message_data, partition=member_id)

    async def receive_message(self, websocket, user_id: str):
        import asyncio, soundfile, base64, io

        tgt_lang = users.get(user_id)["lang"]

        while True:
            message = message_queue.get(partition=user_id, block=False)
            if message is None:
                await asyncio.sleep(0.1)
                continue

            print(f"Received message {message} for {user_id}")

            content = message_content.get(message["message_id"])
            message_type = message["message_type"]
            src_lang = message["lang"]

            message_data = {
                "messageId": message["message_id"],
                "userId": message["user_id"],
                "userName": message["user_name"],
                "lang": src_lang,
            }

            if message_type == "text":
                text, audio_array = self.translate_text(content, src_lang, tgt_lang)
            elif message_type == "audio":
                text, audio_array = self.translate_audio(content, tgt_lang)

            message_data["text"] = text
            message_data["audio"] = audio_array.tolist()

            await websocket.send_json(message_data)


    @modal.asgi_app()
    def asgi_app(self):
        import asyncio
        from fastapi import FastAPI, Form, WebSocket
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI()

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.post("/create-room")
        async def create_room():
            room_id, room_name = self.create_room()
            return {"roomId": room_id}
        
        @app.post("/join-room")
        async def join_room(user_name: str = Form(...), lang: str = Form(...), room_id: str = Form(...)):
            user_id = self.create_user(user_name, lang)
            room = self.join_room(user_id, room_id)
            return {"userId": user_id}
        
        @app.get("/rooms")
        async def get_rooms():
            return {room_id: rooms[room_id] for room_id in rooms.keys()}

        @app.get("/room-info")
        async def get_room_info(room_id: str):
            return {
                "name": rooms[room_id]["name"],
                "members": {user_id: users[user_id] for user_id in rooms[room_id]["members"]}
            }

        @app.websocket("/chat")
        async def chat(websocket: WebSocket):
            await websocket.accept()

            receive_task = None
            user_id = None
            room_id = None

            try:
                user_data = await websocket.receive_json()
                user_id = user_data.get("user_id")
                room_id = user_data.get("room_id")

                receive_task = asyncio.create_task(self.receive_message(websocket, user_id))

                while True:
                    message = await websocket.receive_json()
                    self.send_message(user_id, room_id, message["message_type"], message["content"])

            except Exception as e:
                print(f"Socket disconnected: {e}")
            finally:
                if user_id and room_id:
                    self.leave_room(user_id, room_id)
                if receive_task:
                    receive_task.cancel()
                await websocket.close()

        
        return app
    
    @modal.method()
    def test_translate_text(self):
        import numpy

        text, audio_array = self.translate_text.remote("Hello, world!", "eng", "cmn")
        return text

base_path = Path(__file__).parent
static_path = base_path.joinpath("frontend", "build")

@app.function(
    mounts=[modal.Mount.from_local_dir(static_path, remote_path="/assets")],
    image=frontend_image,
    allow_concurrent_inputs=10,
    keep_warm=2
)
@modal.asgi_app()
def frontend():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    web_app = FastAPI()
    from jinja2 import Template

    with open("/assets/index.html", "r") as f:
        template_html = f.read()

    template = Template(template_html)

    with open("/assets/index.html", "w") as f:
        html = template.render()
        f.write(html)

    web_app.mount("/", StaticFiles(directory="/assets", html=True))

    return web_app  


@app.local_entrypoint()
def main():
    SeamlessM4T.test_translate_text.remote()
    print(text)
