<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { type Room } from '$lib';
	import { PUBLIC_BACKEND_URL } from '$env/static/public';

	let pollRooms: number | null = null;
	let rooms: Record<string, Room> = {};
	const createRoom = async () => {
		const response = await fetch(`${PUBLIC_BACKEND_URL}/create-room`, {
			method: 'POST'
		});

		const { roomId } = await response.json();
		goto(`/room/${roomId}`);
	};

	const getRooms = async () => {
		const response = await fetch(`${PUBLIC_BACKEND_URL}/rooms`);
		rooms = await response.json();
	};

	const joinRoom = (roomId: string) => {
		goto(`/room/${roomId}`);
	};

	onMount(() => {
		getRooms();
		pollRooms = setInterval(async () => {
			await getRooms();
		}, 5000);

		return () => pollRooms && clearInterval(pollRooms);
	});
</script>

<div class="rounded-lg p-4 w-[600px] mx-auto bg-accent">
	<div class="w-full text-center text-5xl text-white">seamless chat</div>
	<div class="text-md text-black text-center mt-2">
		A translation chat app for text and speech conversations.
	</div>
	<div class="text-md text-black text-center">
		Powered by Meta's <a
			href="https://ai.meta.com/research/publications/seamless-multilingual-expressive-and-streaming-speech-translation/"
			target="_blank"
			class="italic">SeamlessM4T</a
		>
		model and deployed on <a href="https://modal.com/" target="_blank" class="italic">Modal</a>.
	</div>
	<div class="grid grid-cols-4 gap-3 mt-4">
		{#each Object.entries(rooms) as [roomId, room]}
			{#if room.members.length > 0}
				<button
					class="p-3 flex flex-col justify-between h-28 bg-secondary hover:bg-secondary/80"
					on:click={() => joinRoom(roomId)}
				>
					<div class="flex flex-col text-black w-full text-center justify-center h-full gap-1">
						<div class="text-2xl mb-1">{room.name}</div>
						<div class="text-md text-white bg-primary px-4 py-1 rounded-full w-fit mx-auto">
							{room.members.length} user{room.members.length === 1 ? '' : 's'}
						</div>
					</div>
				</button>
			{/if}
		{/each}
	</div>
	<button
		on:click={createRoom}
		class="bg-primary hover:bg-primary/80 text-white text-xl w-full py-2 mt-4"
	>
		new room
	</button>
</div>
