import modal

app = modal.App("seamless-m4t-v2")

image = modal.Image.debian_slim().pip_install(
    "transformers",
    "sentencepiece",
    "torchaudio"
)


@app.cls(
    gpu="H100", 
    image=image,
    container_idle_timeout=240,
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
    
    def text_to_text(self, text: str, src_lang: str, tgt_lang: str):
        inputs = self.processor(text = text, src_lang=src_lang, return_tensors="pt").to("cuda")
        output = self.model.generate(**inputs, tgt_lang=tgt_lang, generate_speech=False)[0]
        text = self.processor.decode(tokens.tolist()[0], skip_special_tokens=True)

        return text

    @modal.asgi_app()
    def asgi_app(self):
        from fastapi import FastAPI

        app = FastAPI()
        @app.get("/translate-text")
        async def translate_text(text: str, src_lang: str, tgt_lang: str):
            output = self.text_to_text(text, src_lang, tgt_lang)

            return {"output": output}
        
        return app


