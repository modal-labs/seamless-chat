import modal
from pydantic import BaseModel
from typing import Literal, Optional

app = modal.App("seamless-chat")

image = modal.Image.debian_slim().apt_install("ffmpeg").pip_install("transformers", "sentencepiece", "torchaudio", "soundfile")

users = modal.Dict.from_name("seamless-users", create_if_missing=True)
rooms = modal.Dict.from_name("seamless-rooms", create_if_missing=True)
message_content = modal.Dict.from_name("seamless-message-content", create_if_missing=True)
message_queue = modal.Queue.from_name("seamless-queue", create_if_missing=True)

@app.cls(
    gpu="H100", 
    image=image,
    container_idle_timeout=240,
    timeout=3600,
    concurrency_limit=5,
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
        import uuid

        room_id = str(uuid.uuid4())
        rooms[room_id] = []
        return room_id

    def join_room(self, user_id: str, room_id: str):
        if not room_id in rooms:
            rooms[room_id] = []
        
        if user_id not in rooms[room_id]:
            rooms[room_id].append(user_id)

    def leave_room(self, user_id: str, room_id: str):
        if room_id in rooms and user_id in rooms[room_id]:
            rooms[room_id].remove(user_id)

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

        audio_buffer = io.BytesIO(base64.b64decode(audio))
        audio, orig_freq = torchaudio.load(audio_buffer)
        audio = torchaudio.functional.resample(audio, orig_freq, 16000)

        inputs = self.processor(audios=audio, return_tensors="pt").to("cuda")
        return self._translate(inputs, tgt_lang)

    def send_message(self, user_id: str, room_id: str, message_type: Literal["text", "audio"], content: str):
        user = users.get(user_id)
        message_id = str(uuid.uuid4())
        message_content[message_id] = content

        room_members = rooms.get(room_id, [])
        for member_id in room_members:
            message_queue.put({
                "user_name": user["name"],
                "message_type": message_type,
                "message_id": message_id,
                "lang": user["lang"]
            }, partition=member_id)

    async def receive_message(self, websocket, user_id: str):
        import asyncio, soundfile, base64

        tgt_lang = users.get(user_id)["lang"]

        while True:
            message = message_queue.get(partition=user_id, block=False)
            if message is None:
                await asyncio.sleep(0.1)
                continue

            content = message_content.get(message["message_id"])
            message_type = message["message_type"]
            src_lang = message["lang"]
            user_name = message["user_name"]

            result = {
                "user_name": user_name,
                "src_lang": src_lang,
            }

            if message_type == "text":
                text, audio_array = self.translate_text(content, src_lang, tgt_lang)
            elif message_type == "audio":
                text, audio_array = self.translate_audio(content, tgt_lang)
            
            with io.BytesIO() as audio_buffer:
                soundfile.write(audio_buffer, audio_array, 16000, format="WAV")
                audio_bytes = base64.b64encode(audio_buffer.getvalue()).decode("utf-8")

            result["message_text"] = text
            result["message_audio"] = audio_bytes

            await websocket.send_json(result)


    @modal.asgi_app()
    def asgi_app(self):
        from fastapi import FastAPI, Form, WebSocket
        app = FastAPI()
        
        @app.post("/join-room")
        async def join_room(user_name: str = Form(...), lang: str = Form(...), room_id: Optional[str] = Form(None)):
            user_id = self.create_user(user_name, lang)
            if room_id is None:
                room_id = self.create_room()

            self.join_room(user_id, room_id)

            return {"room_id": room_id, "user_id": user_id}
        
        @app.websocket("/chat")
        async def chat(websocket: WebSocket):
            await websocket.accept()

            receive_task = asyncio.create_task(self.receive_message(websocket, user_id))

            try:
                user_data = await websocket.receive_json()
                user_id = user_data.get("user_id")
                room_id = user_data.get("room_id")

                while True:
                    message = await websocket.receive_json()
                    self.send_message(user_id, room_id, message["message_type"], message["content"])

            except Exception as e:
                print(f"Socket disconnected: {e}")
            finally:
                self.leave_room(user_id, room_id)
                receive_task.cancel()
                await websocket.close()

        
        return app
