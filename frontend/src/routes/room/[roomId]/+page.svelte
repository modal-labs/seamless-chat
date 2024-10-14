<script lang="ts">
	import WaveSurfer from 'wavesurfer.js';

	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { PUBLIC_BACKEND_URL } from '$env/static/public';
	import { languageOptions, type Message, type User } from '$lib';
	import { goto } from '$app/navigation';
	import Chat from './Chat.svelte';
	import Join from './Join.svelte';

	let messages: Message[] = [];
	let roomId = $page.params.roomId;
	let userId: string | null = null;
	let messageType: 'text' | 'audio' = 'text';
	let message = '';
	let connected = false;
	let socket: WebSocket;
	let lang = 'eng';
	let userName = '';
	let roomName = '';
	let audioContainer: HTMLElement;
	let wavesurfer: WaveSurfer | null = null;
	let members: Record<string, User> = {};
	let pollMembers: number | null = null;

	$: if (audioContainer) {
		wavesurfer = WaveSurfer.create({
			container: audioContainer,
			waveColor: '#748465',
			normalize: true,
			barWidth: 4,
			barRadius: 4,
			barGap: 2,
			interact: false,
			cursorWidth: 0,
			height: 24
		});
	}

	let isRecording = false;
	let mediaRecorder: MediaRecorder | null = null;
	let audioChunks: Blob[] = [];

	onMount(() => {
		setupMediaRecorder();

		getRoomInfo();
		pollMembers = setInterval(getRoomInfo, 3000);

		return () => pollMembers && clearInterval(pollMembers);
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
		};
	};

	const getRoomInfo = async () => {
		const response = await fetch(`${PUBLIC_BACKEND_URL}/room-info?room_id=${roomId}`);
		const roomInfo = await response.json();
		roomName = roomInfo.name;
		members = roomInfo.members;
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

		connectSocket();
	};

	const leaveRoom = async () => {
		if (!userId) return;
		socket.close();
		messages = [];
		userId = null;
	};

	const sendMessage = async () => {
		if (!connected || !message) return;

		await socket.send(
			JSON.stringify({
				message_type: messageType,
				content: message
			})
		);
		message = '';
		messageType = 'text';
		isRecording = false;
	};

	const setupMediaRecorder = async () => {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			mediaRecorder = new MediaRecorder(stream);

			mediaRecorder.onstart = () => {
				wavesurfer?.empty();
			};

			mediaRecorder.ondataavailable = (event) => {
				audioChunks.push(event.data);
			};

			mediaRecorder.onstop = () => {
				const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
				const reader = new FileReader();

				wavesurfer?.loadBlob(audioBlob);

				reader.onloadend = () => {
					if (typeof reader.result === 'string') {
						message = reader.result;
					}
				};
				reader.readAsDataURL(audioBlob);

				audioChunks = [];
			};
		} catch (error) {
			console.error('Error setting up media recorder:', error);
		}
	};

	const toggleRecording = () => {
		if (!mediaRecorder) return;
		if (isRecording) {
			mediaRecorder.stop();
		} else {
			audioChunks = [];
			mediaRecorder.start();
			messageType = 'audio';
		}
		isRecording = !isRecording;
	};
</script>

<div class="w-fit mx-auto rounded-lg p-4 bg-accent">
	<div class="text-center text-5xl text-white">{roomName}</div>
	{#if !userId}
		<Join bind:userName bind:lang {joinRoom} />
	{:else}
		<div class="flex gap-2 justify-center mt-4">
			<div class="w-[200px] flex flex-col gap-2 items-center p-4">
				<button on:click={leaveRoom} class="px-4 text-sm h-8 w-full"> edit user </button>
				<button
					on:click={() => {
						leaveRoom();
						goto('/');
					}}
					class="bg-tertiary px-4 rounded-lg text-sm h-8 w-full"
				>
					back to lobby
				</button>
			</div>
			<div class="w-[600px]">
				<Chat {messages} {userId} />
				<div class="flex gap-2 h-8 mt-4">
					<button class="px-4 rounded-lg text-sm w-28" on:click={toggleRecording}>
						{isRecording ? 'stop' : 'record'}
					</button>
					{#if messageType === 'text'}
						<input
							type="text"
							id="message"
							bind:value={message}
							class="text-sm rounded p-1 px-2 w-full"
							placeholder="your message..."
						/>
					{:else if messageType === 'audio'}
						{#if isRecording}
							<input
								type="text"
								disabled
								class="text-sm rounded p-1 px-2 w-full"
								placeholder="recording..."
							/>
						{:else}
							<div class="bg-white w-full rounded p-1 px-2" bind:this={audioContainer} />
						{/if}
					{/if}

					<button
						class="px-4 rounded-lg text-sm bg-tertiary"
						on:click={() => {
							message = '';
							messageType = 'text';
						}}
					>
						reset
					</button>
					<button class="px-4 rounded-lg text-sm" on:click={sendMessage}> send </button>
				</div>
			</div>
			<div class="w-[200px] flex flex-col gap-2 p-4">
				<div class="text-center text-xl">
					online users ({Object.keys(members).length})
				</div>
				{#each Object.keys(members).sort( (a, b) => (a === userId ? -1 : b === userId ? 1 : 0) ) as memberId}
					{@const member = members[memberId]}
					<div class="flex gap-2 items-center">
						<span class="font-bold"
							>{member.name}
							{#if memberId === userId}
								(you)
							{/if}
						</span>
						<span class="text-xs bg-primary px-2 py-0.5 rounded-lg"
							>{languageOptions.find((l) => l.code === member.lang)?.name}</span
						>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
