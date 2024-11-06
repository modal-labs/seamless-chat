# Seamless Chat: Run multilingual chat rooms with SeamlessM4T-V2

Chat with friends from around the world without speaking the same language!

Introducing [Seamless Chat](https://github.com/modal-labs/seamless-chat), a speech-to-speech chat app that lets you chat with all your friends in their language at the same time.

Seamless Chat is powered by Meta's [SeamlessM4T-V2](https://github.com/facebookresearch/seamless_communication/tree/main), a state-of-the-art multilingual speech-to-speech model that supports text and speech translation for over 20 languages. Thanks to Modal's WebSocket support and distributed object stores, we're able to create a scalable, low-latency chat interface.

Try out Seamless-Chat yourself [here](https://seamless.modal.chat)!

<div style="display: flex; justify-content: space-around;">
  <img src="https://modal-cdn.com/seamless-chat/bob.png" alt="Seamless-Chat Bob" width="48%">
  <img src="https://modal-cdn.com/seamless-chat/alice.png" alt="Seamless-Chat Alice" width="48%">
</div>

## Code Overview

Seamless Chat's frontend and backend are both entirely deployed on Modal. The frontend is a standard SvelteKit app and the backend is a FastAPI server that handles WebSockets for chat connections and GPU accelerated inference. Let's take a look at each of these in more detail!

### Chat Backend - SeamlessM4T on GPUs

The code that powers Seamless Chat's backend is defined with Modal's class syntax and the `@app.cls` decorator. We define methods on that class for loading the SeamlessM4T model once our container is constructed. This allows us to manage multiple WebSocket connections in a shared container while managing the overhead of starting new containers. We can also specify the maximum number of concurrent connections with the `allow_concurrent_inputs` property.

```python
@app.cls(
    gpu="H100",
    allow_concurrent_inputs=10,
    ...
)
class SeamlessM4T:
    ...
```

With the `@modal.build()` decorator, we download the model into our container image, and with the `@modal.enter()` decorator, we load the model into memory once the container is instantiated.

```python
@modal.build()
    def build(self):
        snapshot_download("facebook/seamless-m4t-v2-large")

@modal.enter()
def enter(self):
        self.processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
        self.model = SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large").to("cuda")
```

### Chat Backend - FastAPI Server

Modal makes it easy to define a ASGI server: just wrap the `@modal.asgi_app()` decorator around a function that returns a `FastAPI` app.

The main component of our server is our WebSocket endpoint for handling chat connections. Each socket connection needs to listen for incoming messages from the user along with outgoing messages from other users in the room. Using `asyncio`, we can handle both of these tasks concurrently, while also gracefully handling disconnections and errors.

```python
@app.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()

    async def recv_loop():
        while True:
            # fetch incoming messages from user's websocket
            message = await websocket.receive_json()
            ...

    async def send_loop():
        while True:
            # fetch outgoing messages from other users in the room
            ...
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
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
```

### Chat Backend - Distributed Queues

As our application scales up, we may have multiple socket connections across different containers, so we need some way to send and synchronize messages between users. To handle this, we can take advantage of Modal's [distributed queues](https://modal.com/docs/guide/dicts-and-queues#modal-queues).

We can define a Modal Queue to store messages, with a separate FIFO partition for each user. When a user sends a message, we append it to the partition associated with each member of the room. The `send_loop` method repeatedly fetches new messages from their partition and translates the messages into their target language. In an asynchronous context, we simply use the `.aio()` function suffix to fetch messages from the queue. Finally, we pass the messages through the translation model and send the response back to the user.

```python

message_queue = modal.Queue.from_name("seamless-message-queue")

async def send_loop():
    while True:
        message = await message_queue.get.aio(partition=user_id)

        text, audio_array = self.translate(message, src_lang, tgt_lang)

        message_data = {
            "messageId": message["message_id"],
            "userId": message["user_id"],
            "userName": message["user_name"],
            "lang": src_lang,
            "text": text,
            "audio": audio_array.tolist(),
        }

        await websocket.send_json(message_data)
```

### Chat Frontend - SvelteKit

Seamless Chat's frontend is a simple static SvelteKit application. We define a Modal function that is called through a `web_endpoint` with the same `@modal.asgi_app()` decorator. The function simply serves the frontend's static files in the `frontend/build` directory after running `npm run build` in the `frontend` directory.

```python
@app.function(
    mounts=[modal.Mount.from_local_dir(static_path, remote_path="/assets")],
    ...
)
@modal.asgi_app(custom_domains=["seamless.modal.chat"])
def frontend():
    web_app = FastAPI()
    web_app.mount("/", StaticFiles(directory="/assets", html=True))

    return web_app
```

## Deploy

To deploy Seamless Chat, you can simply clone the repository, compile the frontend assets and run `modal deploy`. Make sure you have the latest versions of `npm` and the modal client installed.

```bash
git clone https://github.com/modal-labs/seamless-chat

cd frontend
npm run build
cd ..

modal deploy seamless.py
```
