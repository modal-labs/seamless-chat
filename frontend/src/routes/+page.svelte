<script lang="ts">
	import { goto } from '$app/navigation';
	import { PUBLIC_BACKEND_URL } from '$env/static/public';

	const createRoom = async () => {
		const response = await fetch(`${PUBLIC_BACKEND_URL}/create-room`, {
			method: 'POST'
		});

		const { roomId } = await response.json();
		goto(`/room/${roomId}`);
	};
</script>

<div class="border rounded-lg p-4">
	<div class="w-full text-center text-2xl">Seamless Chat</div>
	<button on:click={createRoom} class="bg-blue-500 w-full text-white py-2 rounded-md mt-4">
		create a new room
	</button>
</div>
