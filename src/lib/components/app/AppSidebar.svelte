<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	let selected = '';
	const SIDEBAR_LOGO_URL = 'https://dev.d-reams.com/img/logo-d.7378c4bf.png';
</script>

<nav
	aria-label="App navigation"
	class="min-w-[4.5rem] bg-gray-850 dark:bg-gray-950 flex gap-2.5 flex-col pt-8 text-gray-400 border-r border-gray-900/10"
>
	<div class="flex justify-center relative">
		{#if selected === 'home'}
			<div class="absolute top-0 left-0 flex h-full">
				<div class="my-auto rounded-r-lg w-1 h-8 bg-blue-500"></div>
			</div>
		{/if}

		<Tooltip content="Home" placement="right">
			<button
				aria-label="Home"
				class="cursor-pointer p-1 transition hover:bg-gray-800 {selected === 'home'
					? 'rounded-lg bg-gray-800'
					: 'rounded-lg'}"
				on:click={() => {
					selected = 'home';

					if (window.electronAPI) {
						window.electronAPI.load('home');
					}
				}}
			>
				<img
					src={SIDEBAR_LOGO_URL}
					class="size-10 p-0.5"
					alt="logo"
					draggable="false"
				/>
			</button>
		</Tooltip>
	</div>

	<div class="-mt-1 border-t border-gray-700/70 mx-4"></div>

	<div class="flex justify-center relative group">
		{#if selected === ''}
			<div class="absolute top-0 left-0 flex h-full">
				<div class="my-auto rounded-r-lg w-1 h-8 bg-blue-500"></div>
			</div>
		{/if}
		<button
			aria-label="Chat"
			class="cursor-pointer bg-transparent p-1 rounded-lg transition hover:bg-gray-800 {selected ===
			''
				? 'bg-gray-800'
				: ''}"
			on:click={() => {
				selected = '';
			}}
		>
			<img
				src={SIDEBAR_LOGO_URL}
				class="size-9 rounded-lg"
				alt="logo"
				draggable="false"
			/>
		</button>
	</div>

	<!-- <div class="flex justify-center relative group text-gray-400">
		<button class=" cursor-pointer p-2" on:click={() => {}}>
			<Plus className="size-4" strokeWidth="2" />
		</button>
	</div> -->
</nav>
