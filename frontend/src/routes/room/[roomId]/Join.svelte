<script lang="ts">
	import { goto } from '$app/navigation';
	import { languageOptions } from '$lib/index';

	export let userName: string;
	export let lang: string;
	export let joinRoom: () => Promise<void>;
</script>

<div class="w-[600px]">
	<div class="flex gap-4 mt-4">
		<div class="w-7/12">
			<label for="userName" class="text-md">name</label>
			<input
				type="text"
				id="userName"
				bind:value={userName}
				class="text-xl rounded px-2 py-1 w-full"
				placeholder="your name..."
			/>
		</div>
		<div class="w-5/12">
			<label for="language" class="text-md">language</label>
			<select
				bind:value={lang}
				id="language"
				class="text-xl rounded px-2 py-1 w-full appearance-none"
			>
				{#each languageOptions as language}
					<option value={language.code}>{language.name}</option>
				{/each}
			</select>
		</div>
	</div>
	<div class="mt-4 flex gap-2 items-center">
		<button on:click={joinRoom} class="text-xl w-full py-2"> join room </button>
		<button on:click={() => goto('/')} class="bg-tertiary text-xl w-full py-2">
			back to lobby
		</button>
	</div>
</div>
