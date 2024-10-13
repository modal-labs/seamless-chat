<script lang="ts">
	import { languageOptions, type Message } from '$lib';

	export let messages: Message[];
	export let userId: string;

	const audioContext = new AudioContext();
	const playAudio = (audio: number[]) => {
		const audioBuffer = new AudioBuffer({ length: audio.length, sampleRate: 16000 });
		audioBuffer.copyToChannel(new Float32Array(audio), 0);
		const source = audioContext.createBufferSource();
		source.buffer = audioBuffer;
		source.connect(audioContext.destination);
		source.start();
	};
</script>

<div class="h-[400px] overflow-y-auto border rounded p-2">
	{#each messages as message (message.messageId)}
		<div
			class={`mb-2 p-2 rounded ${message.userId === userId ? 'bg-blue-100 ml-auto mr-2' : 'bg-gray-100 mr-auto ml-2'}`}
			style="max-width: 80%;"
		>
			<div class="flex justify-between items-center">
				<div class="flex items-center gap-2">
					<span class="font-bold">{message.userName}</span>
					<span class="text-xs text-white bg-blue-500 px-2 py-0.5 rounded-lg"
						>{languageOptions.find((l) => l.code === message.lang)?.name}</span
					>
				</div>
				<button
					class="bg-green-500 text-white px-2 py-1 rounded text-xs"
					on:click={() => playAudio(message.audio)}
				>
					play audio
				</button>
			</div>
			<p>{message.text}</p>
		</div>
	{/each}
</div>
