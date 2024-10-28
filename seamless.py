import modal, asyncio, uuid, random, base64

from pydantic import BaseModel
from typing import Literal, Optional
from pathlib import Path
from fastapi import FastAPI, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from rooms import room_names

app = modal.App("seamless-chat")

backend_image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg")
    .pip_install("transformers", "sentencepiece", "torchaudio", "soundfile", "numpy")
)

with backend_image.imports():
    import io
    import torch
    import torchaudio
    import soundfile
    import numpy
    from huggingface_hub import snapshot_download
    from fastapi import FastAPI, Form, WebSocket, HTTPException
    from transformers import AutoProcessor, SeamlessM4Tv2Model


frontend_image = modal.Image.debian_slim().pip_install("jinja2")

with frontend_image.imports():
    from fastapi import FastAPI
    from jinja2 import Template


users = modal.Dict.from_name("seamless-users", create_if_missing=True)
rooms = modal.Dict.from_name("seamless-rooms", create_if_missing=True)
message_content = modal.Dict.from_name(
    "seamless-message-content", create_if_missing=True
)
message_queue = modal.Queue.from_name("seamless-message-queue", create_if_missing=True)

@app.cls(
    gpu="H100",
    image=backend_image,
    container_idle_timeout=240,
    timeout=3600,
    concurrency_limit=5,
    allow_concurrent_inputs=5,
    keep_warm=1,
)
class SeamlessM4T:
    @modal.build()
    def build(self):
        snapshot_download("facebook/seamless-m4t-v2-large")

    @modal.enter()
    def enter(self):
        self.processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
        self.model = torch.compile(
            SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large").to(
                "cuda"
            )
        )

    def create_user(self, user_name: str, lang: str):
        user_id = str(uuid.uuid4())
        users[user_id] = {
            "name": user_name,
            "lang": lang,
        }
        return user_id

    def create_room(self):
        room_id = str(uuid.uuid4())
        room_name = random.choice(room_names)
        rooms[room_id] = {
            "name": room_name,
            "members": [],
        }
        return room_id

    def join_room(self, user_id: str, room_id: str):
        print(f"{user_id} joined {room_id}")
        if user_id not in rooms[room_id]["members"]:
            rooms[room_id] = {
                "name": rooms[room_id]["name"],
                "members": rooms[room_id]["members"] + [user_id],
            }
        return rooms[room_id]

    def leave_room(self, user_id: str, room_id: str):
        print(f"{user_id} left {room_id}")
        if user_id in rooms[room_id]["members"]:
            members = [
                member for member in rooms[room_id]["members"] if member != user_id
            ]
            if len(members) == 0:
                rooms.pop(room_id)
                return
            rooms[room_id] = {
                "name": rooms[room_id]["name"],
                "members": members,
            }

    def _translate(self, inputs, tgt_lang: str):
        output = self.model.generate(
            **inputs, tgt_lang=tgt_lang, return_intermediate_token_ids=True
        )
        audio_array = output[0].cpu().numpy().squeeze()
        text = self.processor.decode(output[2].tolist()[0], skip_special_tokens=True)
        return text, audio_array

    def translate_text(self, text: str, src_lang: str, tgt_lang: str):
        inputs = self.processor(text=text, src_lang=src_lang, return_tensors="pt").to(
            "cuda"
        )
        return self._translate(inputs, tgt_lang)

    def translate_audio(self, audio: str, tgt_lang: str):
        audio_buffer = io.BytesIO(base64.b64decode(audio.split(",")[1]))
        audio, orig_freq = torchaudio.load(audio_buffer)
        audio = torchaudio.functional.resample(audio, orig_freq, 16000)

        inputs = self.processor(
            audios=audio, return_tensors="pt", sampling_rate=16000
        ).to("cuda")
        return self._translate(inputs, tgt_lang)

    def send_message(
        self,
        user_id: str,
        room_id: str,
        message_type: Literal["text", "audio"],
        content: str,
    ):
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
                "lang": user["lang"],
            }
            message_queue.put(message_data, partition=member_id)

    @modal.asgi_app()
    def asgi_app(self):
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.post("/create-room")
        async def create_room():
            room_id = self.create_room()

            return {"roomId": room_id}

        @app.post("/join-room")
        async def join_room(
            user_name: str = Form(...), lang: str = Form(...), room_id: str = Form(...)
        ):
            if room_id not in rooms:
                raise HTTPException(status_code=404, detail="Room not found")

            user_id = self.create_user(user_name, lang)
            room = self.join_room(user_id, room_id)

            return {"userId": user_id}

        @app.get("/rooms")
        async def get_rooms():

            return {room_id: rooms[room_id] for room_id in rooms.keys()}

        @app.get("/room-info")
        async def get_room_info(room_id: str):
            if room_id not in rooms:

                raise HTTPException(status_code=404, detail="Room not found")

            return {
                "name": rooms[room_id]["name"],
                "members": {
                    user_id: users[user_id] for user_id in rooms[room_id]["members"]
                },
            }

        @app.websocket("/chat")
        async def chat(websocket: WebSocket):
            await websocket.accept()

            user_data = await websocket.receive_json()
            user_id = user_data.get("user_id")
            room_id = user_data.get("room_id")
            tgt_lang = user_data.get("lang")

            async def send_loop():
                while True:
                    message = await message_queue.get.aio(partition=user_id)

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
                        text, audio_array = self.translate_text(
                            content, src_lang, tgt_lang
                        )
                    elif message_type == "audio":
                        text, audio_array = self.translate_audio(content, tgt_lang)

                    message_data["text"] = text
                    message_data["audio"] = audio_array.tolist()

                    await websocket.send_json(message_data)

            async def recv_loop():
                while True:
                    message = await websocket.receive_json()
                    self.send_message(
                        user_id, room_id, message["message_type"], message["content"]
                    )

            try:
                tasks = [
                    asyncio.create_task(send_loop()),
                    asyncio.create_task(recv_loop()),
                ]
                await asyncio.gather(*tasks)
            except WebSocketDisconnect:
                print(f"Socket disconnected: {user_id}")
                await websocket.close(code=1000)
            except Exception as e:
                print(f"Socket error: {e}")
                await websocket.close(code=1011)
            finally:
                print(f"Cleaning up {user_id} in {room_id}")
                if user_id and room_id:
                    self.leave_room(user_id, room_id)
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        return app


base_path = Path(__file__).parent
static_path = base_path.joinpath("frontend", "build")


@app.function(
    mounts=[modal.Mount.from_local_dir(static_path, remote_path="/assets")],
    image=frontend_image,
    allow_concurrent_inputs=10,
    keep_warm=2,
)
@modal.asgi_app(custom_domains=["seamless.modal.chat"])
def frontend():
    web_app = FastAPI()
    web_app.mount("/", StaticFiles(directory="/assets", html=True))

    return web_app
