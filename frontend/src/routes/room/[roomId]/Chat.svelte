<script lang="ts">
	import { languageOptions, type Message } from '$lib';
	import { tick } from 'svelte';
	export let messages: Message[];
	export let userId: string;

	let chatContainer: HTMLElement;
	const audioContext = new AudioContext();
	const playAudio = (audio: number[]) => {
		const audioBuffer = new AudioBuffer({ length: audio.length, sampleRate: 16000 });
		audioBuffer.copyToChannel(new Float32Array(audio), 0);
		const source = audioContext.createBufferSource();
		source.buffer = audioBuffer;
		source.connect(audioContext.destination);
		source.start();
	};

	$: if (chatContainer && messages) {
		tick().then(() => {
			chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
		});
	}
</script>

<div bind:this={chatContainer} class="h-[450px] overflow-y-auto rounded p-2 bg-secondary">
	<div class="text-center bg-primary rounded-full py-1 hidden only:block">
		enter a text message or press record to speak
	</div>
	{#each messages as message (message.messageId)}
		<div
			class={`mb-2 p-2 rounded ${message.userId === userId ? 'bg-primary ml-auto mr-2' : 'bg-accent mr-auto ml-2'}`}
			style="max-width: 80%;"
		>
			<div class="flex justify-between items-center">
				<div class="flex items-center gap-2">
					<span class="font-bold">{message.userName}</span>
					<span class="text-xs text-black bg-neutral px-2 py-0.5 rounded-lg"
						>{languageOptions.find((l) => l.code === message.lang)?.name}</span
					>
					<button
						class="bg-neutral text-black px-2 py-0.5 rounded-lg text-xs"
						on:click={() => playAudio(message.audio)}
					>
						play audio
					</button>
				</div>
			</div>
			<div>{message.text}</div>
		</div>
	{/each}
</div>
