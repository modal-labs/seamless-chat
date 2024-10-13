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

<div class="rounded-lg p-4 w-[600px] mx-auto bg-tea">
	<div class="w-full text-center text-4xl">seamless chat</div>
	<div class="grid grid-cols-4 gap-3 mt-4">
		{#each Object.entries(rooms) as [roomId, room]}
			{#if room.members.length > 0}
				<button
					class="text-space p-3 flex flex-col justify-between h-28 bg-celadon hover:bg-celadon/80"
					on:click={() => joinRoom(roomId)}
				>
					<div class="flex flex-col w-full text-center justify-center h-full gap-1">
						<div class="text-2xl mb-1">{room.name}</div>
						<div class="text-md text-white bg-fern px-4 py-1 rounded-full w-fit mx-auto">
							{room.members.length} user{room.members.length === 1 ? '' : 's'}
						</div>
					</div>
				</button>
			{/if}
		{/each}
	</div>
	<button on:click={createRoom} class="bg-fern text-mint hover:bg-fern/80 w-full py-2 mt-4">
		new room
	</button>
</div>
