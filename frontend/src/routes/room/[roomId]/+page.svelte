<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { PUBLIC_BACKEND_URL } from '$env/static/public';

	$: roomId = $page.params.roomId;

	interface Message {
		messageId: string;
		userId: string;
		userName: string;
		lang: string;
		text: string;
		audio: number[];
	}
	let messages: Message[] = [];

	let userId: string | null = null;
	let message = '';
	let connected = false;
	let socket: WebSocket;
	let lang = 'eng';
	let userName = '';
	let roomName = '';
	const languageOptions = [
		{
			name: 'english',
			code: 'eng'
		},
		{
			name: 'mandarin chinese',
			code: 'cmn'
		}
	];

	let audioContext: AudioContext;

	onMount(() => {
		audioContext = new AudioContext();
	});

	const connectSocket = () => {
		socket = new WebSocket(`${PUBLIC_BACKEND_URL}/chat`);

		socket.onopen = async () => {
			connected = true;
			await socket.send(
				JSON.stringify({
					user_id: userId,
					room_id: roomId
				})
			);
		};

		socket.onmessage = (event) => {
			const message = JSON.parse(event.data) as Message;
			messages = [...messages, message];
		};

		socket.onclose = async () => {
			connected = false;
			socket.close();

			await leaveRoom();
		};
	};

	const joinRoom = async () => {
		if (!userName || !lang) return;
		const formData = new FormData();
		formData.append('room_id', roomId);
		formData.append('user_name', userName);
		formData.append('lang', lang);
		const response = await fetch(`${PUBLIC_BACKEND_URL}/join-room`, {
			method: 'POST',
			body: formData
		});
		const data = await response.json();
		userId = data.userId;
		roomName = data.roomName;

		connectSocket();
	};

	const leaveRoom = async () => {
		if (!userId) return;

		const formData = new FormData();
		formData.append('user_id', userId);
		formData.append('room_id', roomId);

		await fetch(`${PUBLIC_BACKEND_URL}/leave-room`, {
			method: 'POST',
			body: formData
		});
		userId = null;
	};

	const sendMessage = async () => {
		if (!connected || !message) return;

		await socket.send(
			JSON.stringify({
				message_type: 'text',
				content: message
			})
		);
		message = '';
	};

	const playAudio = (audio: number[]) => {
		const audioBuffer = new AudioBuffer({ length: audio.length, sampleRate: 16000 });
		audioBuffer.copyToChannel(new Float32Array(audio), 0);
		const source = audioContext.createBufferSource();
		source.buffer = audioBuffer;
		source.connect(audioContext.destination);
		source.start();
	};
</script>

<div class="border rounded-lg p-4">
	{#if !userId}
		<div class="flex gap-4">
			<div class="w-7/12">
				<label for="userName" class="text-xs">name</label>
				<input
					type="text"
					id="userName"
					bind:value={userName}
					class="text-sm border rounded p-2 w-full"
					placeholder="enter your name..."
				/>
			</div>
			<div class="w-5/12">
				<label for="language" class="text-xs">language</label>
				<select
					bind:value={lang}
					id="language"
					class="text-sm border rounded p-2 w-full appearance-none"
				>
					{#each languageOptions as language}
						<option value={language.code}>{language.name}</option>
					{/each}
				</select>
			</div>
		</div>
		<button on:click={joinRoom} class="bg-blue-500 w-full text-white py-2 rounded-md mt-4">
			join room
		</button>
	{:else}
		<div class="text-center text-xl">{roomName}</div>
		<div class="h-[400px] overflow-y-auto border rounded p-2 mb-2 mt-4">
			{#each messages as message (message.messageId)}
				<div
					class={`mb-2 p-2 rounded ${message.userId === userId ? 'bg-blue-100 ml-auto mr-2' : 'bg-gray-100 mr-auto ml-2'}`}
					style="max-width: 80%;"
				>
					<div class="flex justify-between items-center">
						<span class="font-bold"
							>{message.userName} ({languageOptions.find((l) => l.code === message.lang)
								?.name}):</span
						>
						<button
							class="bg-green-500 text-white px-2 py-1 rounded text-xs"
							on:click={() => playAudio(message.audio)}
						>
							Play Audio
						</button>
					</div>
					<p>{message.text}</p>
				</div>
			{/each}
		</div>
		<div class="flex gap-2">
			<input
				type="text"
				id="message"
				bind:value={message}
				class="text-sm border rounded p-2 w-full"
				placeholder="enter your message..."
			/>
			<button class="bg-blue-500 text-white px-4 rounded-lg text-sm" on:click={sendMessage}>
				Send
			</button>
		</div>
	{/if}
</div>
