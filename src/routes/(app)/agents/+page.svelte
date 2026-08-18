<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { models, showSidebar, user } from '$lib/stores';
	import { getModels as getChatModels } from '$lib/apis';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import {
		getAgents,
		getOpenClawStatus,
		revokeAgentApiKey,
		rotateAgentApiKey,
		syncOpenClawAgents,
		updateAgentSettings,
		type Agent
	} from '$lib/apis/agents';

	let loaded = false;
	let syncing = false;
	let saving = false;
	let rotating = false;
	let agents: Agent[] = [];
	let selectedId: string | null = null;
	let selected: Agent | null = null;
	let openclaw: any = null;
	let search = '';
	let modelId = '';
	let sttModel = 'base';
	let isActive = false;
	let revealedApiKey = '';

	const selectableModels = () =>
		($models ?? []).filter((model) => !(model as any).agent && (model as any).owned_by !== 'arena');

	const toOpenClawModelId = (model: any) => {
		if (model.id.includes('/')) return model.id;
		if (model.owned_by === 'ollama') return `ollama/${model.id}`;
		if (model.owned_by && !['platform', 'local', 'unknown'].includes(model.owned_by)) {
			return `${model.owned_by}/${model.id}`;
		}
		return model.id;
	};

	const selectedPlatformModel = () =>
		selectableModels().find((model) => toOpenClawModelId(model) === modelId);
	const selectedProvider = () =>
		selectedPlatformModel()?.owned_by ?? (modelId.startsWith('ollama/') ? 'ollama' : null);
	const isWhisperAgent = (agent: Agent | null) =>
		!!agent &&
		(agent.config.model.kind === 'whisper' ||
			/transkrip|transcript|whisper|speech.to.text|\basr\b/i.test(
				`${agent.name} ${agent.description ?? ''} ${agent.config.openclaw.agent_id}`
			));

	$: filteredAgents = agents.filter((agent) =>
		`${agent.name} ${agent.config.openclaw.agent_id} ${agent.config.model.model_id}`
			.toLowerCase()
			.includes(search.toLowerCase())
	);
	$: endpoint = selected
		? new URL(
				`${WEBUI_API_BASE_URL}/agents/external/${selected.id}/invoke`,
				window.location.origin
			).toString()
		: '';
	$: curlExample = endpoint
		? `curl -X POST '${endpoint}' \\
  -H 'Authorization: Bearer \${AGENT_API_KEY}' \\
  -H 'Content-Type: application/json' \\
  -d '{"message":"Arahan untuk agent","session_key":"external-system-123"}'`
		: '';

	const selectAgent = (agent: Agent) => {
		selectedId = agent.id;
		selected = agent;
		const storedModel = agent.config.model.model_id;
		const platformModel = selectableModels().find((model) => model.id === storedModel);
		modelId = platformModel ? toOpenClawModelId(platformModel) : storedModel;
		sttModel = agent.config.model.stt_model || 'base';
		isActive = agent.is_active;
		revealedApiKey = '';
	};

	const replaceAgent = (agent: Agent) => {
		agents = agents.map((item) => (item.id === agent.id ? agent : item));
		selectAgent(agent);
	};

	const refreshChatModels = async () => {
		models.set(await getChatModels(localStorage.token, null, false, true));
	};

	const syncAgents = async (notify = true) => {
		syncing = true;
		try {
			agents = await syncOpenClawAgents(localStorage.token);
			await refreshChatModels();
			if (selectedId) {
				const current = agents.find((item) => item.id === selectedId);
				if (current) selectAgent(current);
				else if (agents.length) selectAgent(agents[0]);
				else selected = null;
			} else if (agents.length) {
				selectAgent(agents[0]);
			}
			if (notify) toast.success(`${agents.length} agent disegerakkan daripada OpenClaw.`);
		} catch (error) {
			if (notify) toast.error(`${error}`);
		} finally {
			syncing = false;
		}
	};

	const saveSettings = async () => {
		if (!selected || (!modelId && !isWhisperAgent(selected)))
			return toast.error('Pilih model untuk agent ini.');
		saving = true;
		try {
			const updated = await updateAgentSettings(localStorage.token, selected.id, {
				model_id: modelId || selected.config.model.model_id || 'local/whisper',
				provider: selectedProvider(),
				model_type: isWhisperAgent(selected) ? 'whisper' : 'llm',
				stt_model: isWhisperAgent(selected) ? sttModel : null,
				is_active: isActive
			});
			replaceAgent(updated);
			await refreshChatModels();
			toast.success('Model dan status agent disimpan.');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};

	const rotateKey = async () => {
		if (!selected) return;
		if (
			selected.api_key_configured &&
			!confirm('Kunci API semasa akan berhenti berfungsi serta-merta. Teruskan?')
		)
			return;
		rotating = true;
		try {
			const result = await rotateAgentApiKey(localStorage.token, selected.id);
			revealedApiKey = result.api_key;
			const refreshed = await getAgents(localStorage.token);
			agents = refreshed.filter((item) => item.config.openclaw.agent_id);
			const current = agents.find((item) => item.id === selected?.id);
			if (current) {
				selected = current;
				modelId = current.config.model.model_id;
				sttModel = current.config.model.stt_model || 'base';
				isActive = current.is_active;
			}
			toast.success('Kunci API dijana. Salin sekarang; ia tidak akan dipaparkan lagi.');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			rotating = false;
		}
	};

	const revokeKey = async () => {
		if (!selected || !confirm('Batalkan akses API untuk agent ini?')) return;
		try {
			replaceAgent(await revokeAgentApiKey(localStorage.token, selected.id));
			revealedApiKey = '';
			toast.success('Akses API dibatalkan.');
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const copy = async (value: string, label: string) => {
		await navigator.clipboard.writeText(value);
		toast.success(`${label} disalin.`);
	};

	const formatDate = (timestamp?: number | null) =>
		timestamp ? new Date(timestamp * 1000).toLocaleString() : 'Belum pernah';

	onMount(async () => {
		if ($user?.role !== 'admin') return goto('/');
		try {
			openclaw = await getOpenClawStatus(localStorage.token);
			if (openclaw?.connected) await syncAgents(false);
			else {
				agents = (await getAgents(localStorage.token)).filter(
					(item) => item.config.openclaw.agent_id
				);
				if (agents.length) selectAgent(agents[0]);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loaded = true;
		}
	});
</script>

{#if !loaded}
	<div
		class="flex h-screen max-h-[100dvh] w-full flex-1 items-center justify-center {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<Spinner className="size-6" />
	</div>
{:else}
	<div
		class="flex h-screen max-h-[100dvh] w-full max-w-full bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100 {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<aside
			class="hidden w-80 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 lg:flex"
		>
			<div class="border-b border-gray-200 p-5 dark:border-gray-800">
				<div class="flex items-start justify-between gap-3">
					<div>
						<h1 class="text-lg font-semibold">Konfigurasi Agent</h1>
						<p class="mt-1 text-xs text-gray-500">Agent dimiliki oleh OpenClaw</p>
					</div>
					<button class="primary-button" disabled={syncing} on:click={() => syncAgents()}>
						{syncing ? 'Sync…' : 'Sync'}
					</button>
				</div>
				<input class="field mt-4" bind:value={search} placeholder="Cari agent OpenClaw…" />
			</div>
			<div class="flex-1 space-y-2 overflow-y-auto p-3">
				{#each filteredAgents as agent}
					<button
						class="w-full rounded-xl border p-3 text-left transition {selectedId === agent.id
							? 'border-blue-400 bg-blue-50 dark:bg-blue-950/30'
							: 'border-transparent hover:bg-gray-100 dark:hover:bg-gray-800'}"
						on:click={() => selectAgent(agent)}
					>
						<div class="flex items-center gap-2">
							<span class="size-2 rounded-full {agent.is_active ? 'bg-emerald-500' : 'bg-gray-400'}"
							></span>
							<span class="truncate text-sm font-medium">{agent.name}</span>
						</div>
						<p class="mt-1 truncate text-xs text-gray-500">
							{agent.config.model.model_id || 'Model belum dipilih'}
						</p>
					</button>
				{/each}
				{#if !filteredAgents.length}
					<div class="py-10 text-center text-sm text-gray-500">Tiada agent OpenClaw.</div>
				{/if}
			</div>
		</aside>

		<main class="min-w-0 flex-1 overflow-y-auto">
			<header
				class="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-gray-800 dark:bg-gray-900/90 md:px-7"
			>
				<div class="flex items-center gap-3">
					<button class="md:hidden" on:click={() => showSidebar.set(!$showSidebar)}
						><SidebarIcon /></button
					>
					<div>
						<div class="font-semibold">{selected?.name || 'Senarai Agent OpenClaw'}</div>
						<div
							class="flex items-center gap-1.5 text-xs {openclaw?.connected
								? 'text-emerald-600'
								: 'text-amber-600'}"
						>
							<span
								class="size-1.5 rounded-full {openclaw?.connected
									? 'bg-emerald-500'
									: 'bg-amber-500'}"
							></span>
							{openclaw?.connected ? 'OpenClaw tersedia' : 'OpenClaw belum tersedia'}
						</div>
					</div>
				</div>
				<div class="flex gap-2">
					<button
						class="secondary-button lg:hidden"
						disabled={syncing}
						on:click={() => syncAgents()}>Sync</button
					>
					{#if selected}
						<button class="primary-button" disabled={saving} on:click={saveSettings}>
							{saving ? 'Menyimpan…' : 'Simpan'}
						</button>
					{/if}
				</div>
			</header>

			<div class="mx-auto max-w-5xl p-4 md:p-7">
				{#if agents.length}
					<label class="mb-5 block lg:hidden">
						<span class="field-label">Pilih agent</span>
						<select
							class="field"
							value={selectedId ?? ''}
							on:change={(event) => {
								const agent = agents.find((item) => item.id === event.currentTarget.value);
								if (agent) selectAgent(agent);
							}}
						>
							{#each agents as agent}<option value={agent.id}>{agent.name}</option>{/each}
						</select>
					</label>
				{/if}

				{#if !openclaw?.connected}
					<div
						class="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20"
					>
						<div class="text-sm font-medium">OpenClaw belum bersedia</div>
						<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">{openclaw?.message}</p>
					</div>
				{/if}

				{#if !selected}
					<div
						class="rounded-2xl border border-dashed border-gray-300 py-16 text-center dark:border-gray-700"
					>
						<div class="text-4xl">🦞</div>
						<h2 class="mt-4 font-semibold">Cipta agent dalam OpenClaw</h2>
						<p class="mx-auto mt-2 max-w-lg text-sm text-gray-500">
							Identiti, arahan, tools, skills dan orchestration agent diurus oleh OpenClaw. Selepas
							mencipta agent, kembali ke halaman ini dan tekan Sync.
						</p>
						<code class="mt-5 inline-block rounded-lg bg-gray-900 px-4 py-2 text-xs text-white"
							>make openclaw-setup</code
						>
					</div>
				{:else}
					<div class="space-y-5">
						<section class="panel">
							<div class="flex items-start justify-between gap-4">
								<div>
									<h2 class="section-title">Agent OpenClaw</h2>
									<p class="mt-1 text-xs text-gray-500">
										Identiti dan kebolehan agent diurus terus dalam OpenClaw.
									</p>
								</div>
								<span
									class="rounded-full px-2.5 py-1 text-xs {isActive
										? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
										: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}"
								>
									{isActive ? 'Aktif' : 'Tidak aktif'}
								</span>
							</div>
							<div class="mt-5 grid gap-4 md:grid-cols-2">
								<div>
									<span class="field-label">Nama</span>
									<div class="readonly-field">{selected.name}</div>
								</div>
								<div>
									<span class="field-label">OpenClaw Agent ID</span>
									<div class="readonly-field font-mono">{selected.config.openclaw.agent_id}</div>
								</div>
								<div class="md:col-span-2">
									<span class="field-label">Workspace</span>
									<div class="readonly-field break-all font-mono text-xs">
										{selected.config.openclaw.workspace}
									</div>
								</div>
							</div>
						</section>

						<section class="panel">
							<div class="flex items-start justify-between gap-3">
								<div>
									<h2 class="section-title">Model dan status</h2>
									<p class="mt-1 text-xs text-gray-500">
										Hanya tetapan penggunaan Pengurusan AI disimpan di sini.
									</p>
								</div>
								<button class="text-xs text-blue-600" on:click={() => goto('/workspace/models')}
									>Urus model →</button
								>
							</div>
							<div class="mt-5 grid gap-4 md:grid-cols-2">
								<label>
									<span class="field-label">Model utama</span>
									{#if isWhisperAgent(selected)}
										<select class="field" bind:value={sttModel}>
											{#each ['tiny', 'base', 'small', 'medium', 'large-v3', 'distil-large-v3'] as variant}<option
													value={variant}>Whisper · {variant}</option
												>{/each}
										</select>
									{:else}<select class="field" bind:value={modelId}>
											<option value="" disabled>Pilih model</option>
											{#if modelId && !selectableModels().some((model) => toOpenClawModelId(model) === modelId)}
												<option value={modelId}>{modelId} — OpenClaw</option>
											{/if}
											{#each selectableModels() as model}<option value={toOpenClawModelId(model)}
													>{model.name ?? model.id} — {toOpenClawModelId(model)}</option
												>{/each}
										</select>{/if}
								</label>
								<label>
									<span class="field-label">Akses Pengurusan AI</span>
									<select class="field" bind:value={isActive}>
										<option value={true}>Aktif</option>
										<option value={false}>Tidak aktif</option>
									</select>
								</label>
							</div>
							<p class="field-help">
								{isWhisperAgent(selected)
									? 'Agent transkripsi dikesan; pilihan ini disimpan sebagai model Whisper worker.'
									: 'Gunakan ID penuh OpenClaw seperti deepseek/deepseek-v4-flash.'}
							</p>
						</section>

						<section class="panel">
							<div class="flex flex-wrap items-start justify-between gap-3">
								<div>
									<h2 class="section-title">API sistem luaran</h2>
									<p class="mt-1 text-xs text-gray-500">
										Akses bearer terhad kepada agent ini. Jangan gunakan token operator OpenClaw
										Gateway.
									</p>
								</div>
								<div class="flex gap-2">
									{#if selected.api_key_configured}<button
											class="secondary-button text-red-600"
											on:click={revokeKey}>Batalkan</button
										>{/if}
									<button class="primary-button" disabled={rotating} on:click={rotateKey}
										>{rotating
											? 'Menjana…'
											: selected.api_key_configured
												? 'Putar kunci'
												: 'Jana kunci'}</button
									>
								</div>
							</div>

							<div class="mt-5">
								<span class="field-label">Endpoint</span>
								<div class="flex gap-2">
									<div class="readonly-field min-w-0 flex-1 break-all font-mono text-xs">
										{endpoint}
									</div>
									<button class="secondary-button" on:click={() => copy(endpoint, 'Endpoint')}
										>Salin</button
									>
								</div>
							</div>

							{#if revealedApiKey}
								<div
									class="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/30"
								>
									<div class="text-sm font-semibold">Salin kunci ini sekarang</div>
									<p class="mt-1 text-xs text-gray-600 dark:text-gray-400">
										Kunci penuh tidak disimpan dan tidak boleh dipaparkan semula.
									</p>
									<div class="mt-3 flex gap-2">
										<div class="readonly-field min-w-0 flex-1 break-all font-mono text-xs">
											{revealedApiKey}
										</div>
										<button
											class="secondary-button"
											on:click={() => copy(revealedApiKey, 'Kunci API')}>Salin</button
										>
									</div>
								</div>
							{/if}

							<div class="mt-4 grid gap-4 text-xs md:grid-cols-3">
								<div>
									<span class="text-gray-500">Status kunci</span>
									<div class="mt-1 font-medium">
										{selected.api_key_configured
											? `Aktif · ${selected.api_key_prefix}…`
											: 'Belum dijana'}
									</div>
								</div>
								<div>
									<span class="text-gray-500">Dijana</span>
									<div class="mt-1 font-medium">{formatDate(selected.api_key_created_at)}</div>
								</div>
								<div>
									<span class="text-gray-500">Terakhir digunakan</span>
									<div class="mt-1 font-medium">{formatDate(selected.api_key_last_used_at)}</div>
								</div>
							</div>

							<div class="mt-5">
								<div class="flex items-center justify-between">
									<span class="field-label">Contoh HTTP / penyambung gaya MCP</span><button
										class="text-xs text-blue-600"
										on:click={() => copy(curlExample, 'Contoh cURL')}>Salin cURL</button
									>
								</div>
								<pre
									class="overflow-x-auto whitespace-pre-wrap rounded-xl bg-gray-950 p-4 text-xs text-gray-100">{curlExample}</pre>
								<p class="field-help">
									Gunakan satu <code>session_key</code> yang stabil bagi setiap perbualan sistem luaran.
									Respons dipulangkan sebagai JSON.
								</p>
							</div>
						</section>
					</div>
				{/if}
			</div>
		</main>
	</div>
{/if}

<style>
	:global(.field-label) {
		display: block;
		margin-bottom: 0.375rem;
		color: rgb(75 85 99);
		font-size: 0.75rem;
		font-weight: 500;
	}
	:global(.dark .field-label) {
		color: rgb(156 163 175);
	}
	:global(.field) {
		width: 100%;
		border: 1px solid rgb(209 213 219);
		border-radius: 0.625rem;
		background: transparent;
		padding: 0.625rem 0.75rem;
		font-size: 0.875rem;
		outline: none;
	}
	:global(.field:focus) {
		border-color: rgb(59 130 246);
		box-shadow: 0 0 0 1px rgb(59 130 246);
	}
	:global(.dark .field) {
		border-color: rgb(55 65 81);
		background: rgb(17 24 39);
	}
	:global(.field-help) {
		display: block;
		margin-top: 0.375rem;
		color: rgb(107 114 128);
		font-size: 0.6875rem;
	}
	:global(.panel) {
		border: 1px solid rgb(229 231 235);
		border-radius: 1rem;
		background: white;
		padding: 1.25rem;
	}
	:global(.dark .panel) {
		border-color: rgb(31 41 55);
		background: rgb(17 24 39);
	}
	:global(.section-title) {
		font-size: 1rem;
		font-weight: 600;
	}
	:global(.primary-button) {
		white-space: nowrap;
		border-radius: 0.5rem;
		background: rgb(37 99 235);
		color: white;
		padding: 0.5rem 0.875rem;
		font-size: 0.75rem;
		font-weight: 500;
	}
	:global(.primary-button:disabled) {
		opacity: 0.5;
	}
	:global(.secondary-button) {
		white-space: nowrap;
		border: 1px solid rgb(209 213 219);
		border-radius: 0.5rem;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
	}
	:global(.dark .secondary-button) {
		border-color: rgb(55 65 81);
	}
	:global(.readonly-field) {
		border: 1px solid rgb(229 231 235);
		border-radius: 0.625rem;
		background: rgb(249 250 251);
		padding: 0.625rem 0.75rem;
		font-size: 0.875rem;
	}
	:global(.dark .readonly-field) {
		border-color: rgb(55 65 81);
		background: rgb(3 7 18);
	}
</style>
