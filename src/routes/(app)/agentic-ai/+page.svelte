<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getModels as getChatModels } from '$lib/apis';
	import {
		createAgenticWorkflow,
		deleteAgenticWorkflow,
		getAgenticWorkflows,
		updateAgenticWorkflow,
		type AgenticWorkflow,
		type AgenticWorkflowForm,
		type AgenticWorkflowNode
	} from '$lib/apis/agentic-workflows';
	import { getAgents, type Agent } from '$lib/apis/agents';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { models, showSidebar, user } from '$lib/stores';

	const whisperModels = ['tiny', 'base', 'small', 'medium', 'large-v3', 'distil-large-v3'];
	let loaded = false;
	let saving = false;
	let workflows: AgenticWorkflow[] = [];
	let agents: Agent[] = [];
	let selectedId: string | null = null;
	let name = '';
	let description = '';
	let toolName = '';
	let isActive = true;
	let visibleInChat = true;
	let nodes: AgenticWorkflowNode[] = [];
	let timeoutSeconds = 3600;
	let maxRetries = 3;

	const selectableModels = () =>
		($models ?? []).filter(
			(model) =>
				!(model as any).agent &&
				!(model as any).agentic_workflow &&
				(model as any).owned_by !== 'arena'
		);
	const modelReference = (model: any) => {
		if (model.id.includes('/')) return model.id;
		if (model.owned_by === 'ollama') return `ollama/${model.id}`;
		if (model.owned_by && !['platform', 'local', 'unknown'].includes(model.owned_by)) {
			return `${model.owned_by}/${model.id}`;
		}
		return model.id;
	};
	const agentById = (id: string) => agents.find((agent) => agent.id === id);
	const isWhisperAgent = (agent?: Agent) =>
		!!agent &&
		(agent.config.model.kind === 'whisper' ||
			/transkrip|transcript|whisper|speech.to.text|\basr\b/i.test(
				`${agent.name} ${agent.description ?? ''} ${agent.config.openclaw.agent_id} ${agent.config.model.model_id}`
			));

	const resetDraft = () => {
		selectedId = null;
		name = 'Aliran Agent Baharu';
		description = '';
		toolName = `aliran_agent_${Date.now().toString().slice(-6)}`;
		isActive = true;
		visibleInChat = true;
		nodes = [];
		timeoutSeconds = 3600;
		maxRetries = 3;
	};

	const selectWorkflow = (workflow: AgenticWorkflow) => {
		selectedId = workflow.id;
		name = workflow.name;
		description = workflow.description ?? '';
		toolName = workflow.tool_name;
		isActive = workflow.is_active;
		visibleInChat = workflow.config.visible_in_chat ?? true;
		nodes = (workflow.config.nodes ?? []).map((node) => ({ ...node }));
		timeoutSeconds = workflow.config.timeout_seconds;
		maxRetries = workflow.config.max_retries;
	};

	const addAgent = (agent: Agent) => {
		nodes = [
			...nodes,
			{
				agent_id: agent.id,
				model_id: isWhisperAgent(agent)
					? agent.config.model.stt_model || 'base'
					: agent.config.model.model_id,
				instruction: ''
			}
		];
	};

	const changeNodeAgent = (index: number, agentId: string) => {
		const agent = agentById(agentId);
		if (!agent) return;
		nodes = nodes.map((node, position) =>
			position === index
				? {
						agent_id: agent.id,
						model_id: isWhisperAgent(agent)
							? agent.config.model.stt_model || 'base'
							: agent.config.model.model_id,
						instruction: node.instruction
					}
				: node
		);
	};

	const moveNode = (index: number, direction: -1 | 1) => {
		const destination = index + direction;
		if (destination < 0 || destination >= nodes.length) return;
		const reordered = [...nodes];
		[reordered[index], reordered[destination]] = [reordered[destination], reordered[index]];
		nodes = reordered;
	};

	const removeNode = (index: number) => {
		nodes = nodes.filter((_, position) => position !== index);
	};

	const form = (): AgenticWorkflowForm => ({
		name,
		description: description || null,
		tool_name: toolName,
		is_active: isActive,
		config: {
			engine: 'langgraph',
			trigger: 'openclaw-tool',
			task_queue: 'pengurusan-ai-agents',
			timeout_seconds: timeoutSeconds,
			max_retries: maxRetries,
			nodes,
			visible_in_chat: visibleInChat,
			executor_agent_id: '',
			allowed_agent_ids: []
		}
	});

	const save = async () => {
		if (!name.trim() || !toolName.trim()) return toast.error('Nama dan ID workflow diperlukan.');
		if (!nodes.length) return toast.error('Tambah sekurang-kurangnya satu agent ke aliran.');
		if (nodes.some((node) => !node.agent_id || !node.model_id)) {
			return toast.error('Setiap langkah mesti mempunyai agent dan model.');
		}
		if (nodes.some((node) => !agentById(node.agent_id)?.is_active)) {
			return toast.error('Aktifkan semua agent yang digunakan melalui Konfigurasi Agent dahulu.');
		}
		saving = true;
		try {
			const saved = selectedId
				? await updateAgenticWorkflow(localStorage.token, selectedId, form())
				: await createAgenticWorkflow(localStorage.token, form());
			workflows = selectedId
				? workflows.map((item) => (item.id === saved.id ? saved : item))
				: [saved, ...workflows];
			selectWorkflow(saved);
			models.set(await getChatModels(localStorage.token, null, false, true));
			toast.success('Aliran agent disimpan dan kini boleh dipilih dalam chat.');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};

	const remove = async () => {
		if (!selectedId || !confirm('Padam aliran agent ini?')) return;
		try {
			await deleteAgenticWorkflow(localStorage.token, selectedId);
			workflows = workflows.filter((item) => item.id !== selectedId);
			models.set(await getChatModels(localStorage.token, null, false, true));
			if (workflows.length) selectWorkflow(workflows[0]);
			else resetDraft();
			toast.success('Aliran agent dipadam.');
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') return goto('/');
		try {
			[workflows, agents] = await Promise.all([
				getAgenticWorkflows(localStorage.token),
				getAgents(localStorage.token)
			]);
			agents = agents.filter((agent) => agent.is_active && agent.config.openclaw.agent_id);
			models.set(await getChatModels(localStorage.token, null, false, true));
			if (workflows.length) selectWorkflow(workflows[0]);
			else resetDraft();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loaded = true;
		}
	});
</script>

{#if !loaded}
	<div class="flex h-screen w-full items-center justify-center"><Spinner className="size-6" /></div>
{:else}
	<div
		class="flex h-screen w-full bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100 {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''}"
	>
		<aside
			class="hidden w-80 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 lg:flex"
		>
			<div class="border-b border-gray-200 p-5 dark:border-gray-800">
				<div class="flex items-start justify-between gap-3">
					<div>
						<h1 class="text-lg font-semibold">Konfigurasi Agentic AI</h1>
						<p class="mt-1 text-xs text-gray-500">Susun agent OpenClaw sebagai satu aliran</p>
					</div>
					<button class="primary-button" on:click={resetDraft}>+ Baharu</button>
				</div>
			</div>
			<div class="flex-1 space-y-2 overflow-y-auto p-3">
				{#each workflows as workflow}
					<button
						class="w-full rounded-xl border p-3 text-left {selectedId === workflow.id
							? 'border-blue-400 bg-blue-50 dark:bg-blue-950/30'
							: 'border-transparent hover:bg-gray-100 dark:hover:bg-gray-800'}"
						on:click={() => selectWorkflow(workflow)}
					>
						<div class="flex items-center gap-2">
							<span
								class="size-2 rounded-full {workflow.is_active ? 'bg-emerald-500' : 'bg-gray-400'}"
							></span><span class="truncate text-sm font-medium">{workflow.name}</span>
						</div>
						<p class="mt-1 text-xs text-gray-500">{workflow.config.nodes?.length ?? 0} agent</p>
					</button>
				{/each}
				{#if !workflows.length}<div class="py-10 text-center text-sm text-gray-500">
						Belum ada aliran agent.
					</div>{/if}
			</div>
		</aside>

		<main class="min-w-0 flex-1 overflow-y-auto">
			<header
				class="sticky top-0 z-20 flex items-center justify-between border-b border-gray-200 bg-white/90 px-5 py-3 backdrop-blur dark:border-gray-800 dark:bg-gray-900/90"
			>
				<div>
					<div class="font-semibold">{selectedId ? name : 'Aliran baharu'}</div>
					<div class="text-xs text-gray-500">
						Agent pertama → output → agent berikutnya → respons chat
					</div>
				</div>
				<div class="flex gap-2">
					{#if selectedId}<button class="secondary-button text-red-600" on:click={remove}
							>Padam</button
						>{/if}<button class="primary-button" disabled={saving} on:click={save}
						>{saving ? 'Menyimpan…' : 'Simpan'}</button
					>
				</div>
			</header>

			<div class="mx-auto max-w-6xl space-y-5 p-4 md:p-7">
				<section class="panel">
					<div class="flex flex-wrap items-start justify-between gap-4">
						<div>
							<h2 class="section-title">1. Tetapan aliran</h2>
							<p class="mt-1 text-xs text-gray-500">
								Aliran aktif dan dipaparkan dalam chat selepas disimpan.
							</p>
						</div>
						<div class="flex gap-4 text-sm">
							<label class="flex items-center gap-2"
								><input type="checkbox" bind:checked={isActive} /> Aktif</label
							><label class="flex items-center gap-2"
								><input type="checkbox" bind:checked={visibleInChat} /> Papar dalam chat</label
							>
						</div>
					</div>
					<div class="mt-5 grid gap-4 md:grid-cols-2">
						<label
							><span class="field-label">Nama aliran</span><input
								class="field"
								bind:value={name}
							/></label
						>
						<label
							><span class="field-label">ID workflow</span><input
								class="field font-mono"
								bind:value={toolName}
								pattern="[a-z][a-z0-9_]*"
							/></label
						>
						<label class="md:col-span-2"
							><span class="field-label">Penerangan</span><input
								class="field"
								bind:value={description}
							/></label
						>
					</div>
				</section>

				<section class="panel">
					<h2 class="section-title">2. Agent tersedia</h2>
					<p class="mt-1 text-xs text-gray-500">
						Hanya agent OpenClaw yang benar-benar telah dicipta dan disegerakkan dipaparkan. Klik
						mengikut urutan yang anda mahu.
					</p>
					<div class="mt-4 flex flex-wrap gap-2">
						{#each agents as agent}<button class="secondary-button" on:click={() => addAgent(agent)}
								>+ {agent.name}<span class="ml-1 text-gray-500"
									>{agent.config.openclaw.agent_id}{agent.is_active ? '' : ' · tidak aktif'}</span
								></button
							>{/each}
						{#if !agents.length}<span class="text-sm text-gray-500"
								>Tiada agent. Cipta dalam OpenClaw, kemudian Sync di Konfigurasi Agent.</span
							>{/if}
					</div>
				</section>

				<section class="panel">
					<div class="flex items-start justify-between gap-3">
						<div>
							<h2 class="section-title">3. Aliran agent LangGraph</h2>
							<p class="mt-1 text-xs text-gray-500">
								Susunan baris ialah susunan pelaksanaan sebenar melalui Temporal.
							</p>
						</div>
						<div class="flex gap-2 text-xs">
							<span class="architecture-chip">LangGraph</span><span>→</span><span
								class="architecture-chip">Temporal</span
							>
						</div>
					</div>
					{#if !nodes.length}
						<div
							class="mt-5 rounded-xl border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500 dark:border-gray-700"
						>
							Klik agent tersedia untuk menambahkannya ke aliran.
						</div>
					{:else}
						<div
							class="mt-5 overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700"
						>
							{#each nodes as node, index}
								{@const nodeAgent = agentById(node.agent_id)}
								<div class="flow-row">
									<div class="flex items-center gap-3">
										<span
											class="flex size-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300"
											>{index + 1}</span
										><select
											class="field"
											value={node.agent_id}
											on:change={(event) => changeNodeAgent(index, event.currentTarget.value)}
											>{#each agents as agent}<option value={agent.id}
													>{agent.name} · {agent.config.openclaw.agent_id}</option
												>{/each}</select
										>
									</div>
									<div class="space-y-2">
										{#if isWhisperAgent(nodeAgent)}
											<select class="field" bind:value={node.model_id}
												>{#each whisperModels as variant}<option value={variant}
														>Whisper · {variant}</option
													>{/each}</select
											>
										{:else}
											<select class="field" bind:value={node.model_id}
												>{#if node.model_id && !selectableModels().some((model) => modelReference(model) === node.model_id)}<option
														value={node.model_id}>{node.model_id}</option
													>{/if}{#each selectableModels() as model}<option
														value={modelReference(model)}
														>{model.name ?? model.id} · {modelReference(model)}</option
													>{/each}</select
											>
										{/if}
										<input
											class="field"
											bind:value={node.instruction}
											placeholder="Arahan tambahan untuk langkah ini (pilihan)"
										/>
									</div>
									<div class="flex gap-1">
										<button
											class="secondary-button"
											disabled={index === 0}
											on:click={() => moveNode(index, -1)}>↑</button
										><button
											class="secondary-button"
											disabled={index === nodes.length - 1}
											on:click={() => moveNode(index, 1)}>↓</button
										><button
											class="secondary-button text-red-600"
											on:click={() => removeNode(index)}>Buang</button
										>
									</div>
								</div>
							{/each}
						</div>
					{/if}
					<div class="mt-5 grid gap-4 md:grid-cols-2">
						<label
							><span class="field-label">Timeout workflow (saat)</span><input
								class="field"
								type="number"
								min="30"
								bind:value={timeoutSeconds}
							/></label
						><label
							><span class="field-label">Retry setiap agent</span><input
								class="field"
								type="number"
								min="0"
								max="20"
								bind:value={maxRetries}
							/></label
						>
					</div>
					<div
						class="mt-4 rounded-xl bg-blue-50 p-3 text-xs text-blue-800 dark:bg-blue-950/30 dark:text-blue-200"
					>
						Contoh: tambah <strong>pegawai-ringkasan</strong> dahulu, kemudian
						<strong>main</strong>. Output pegawai-ringkasan akan diberikan kepada main sebelum
						jawapan akhir dipaparkan dalam chat.
					</div>
				</section>
			</div>
		</main>
	</div>
{/if}

<style>
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
	:global(.dark .field) {
		border-color: rgb(55 65 81);
		background: rgb(17 24 39);
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
	:global(.primary-button:disabled),
	:global(.secondary-button:disabled) {
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
	:global(.architecture-chip) {
		border: 1px solid rgb(209 213 219);
		border-radius: 9999px;
		padding: 0.3rem 0.6rem;
	}
	:global(.flow-row) {
		display: grid;
		grid-template-columns: minmax(16rem, 0.9fr) minmax(20rem, 1.3fr) auto;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		border-bottom: 1px solid rgb(229 231 235);
	}
	:global(.flow-row:last-child) {
		border-bottom: 0;
	}
	:global(.dark .flow-row) {
		border-color: rgb(31 41 55);
	}
	@media (max-width: 767px) {
		:global(.flow-row) {
			grid-template-columns: 1fr;
		}
	}
</style>
