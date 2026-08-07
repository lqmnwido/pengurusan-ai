<template>
	<div class="container-fluid p-4">
		<div class="row justify-content-center">
			<div class="col-12 col-xl-10">
				<div class="card shadow-sm border-0">
					<div class="card-body p-4">
						<div class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-4">
							<div>
								<h4 class="mb-1">Document Upload</h4>
								<p class="text-muted mb-0">
									Upload PDF or DOCX, send it to Open WebUI, and poll for the translated result.
								</p>
							</div>

							<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-3 py-2">
								Skote style
							</span>
						</div>

						<div class="row g-3">
							<div class="col-12 col-lg-5">
								<div class="card border h-100">
									<div class="card-body">
										<div class="mb-3">
											<label class="form-label">Open WebUI API Token</label>
											<input
												v-model="authToken"
												type="password"
												class="form-control"
												placeholder="Bearer token"
											/>
										</div>

										<div class="mb-3">
											<label class="form-label">File</label>
											<input
												type="file"
												class="form-control"
												accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
												@change="onFileChange"
											/>
											<div class="form-text">PDF and DOCX are supported by the translation API.</div>
										</div>

										<div class="row g-3">
											<div class="col-12">
												<label class="form-label">Target language</label>
												<input v-model="targetLanguage" type="text" class="form-control" placeholder="Malay" />
											</div>

											<div class="col-12">
												<label class="form-label">Source language</label>
												<input v-model="sourceLanguage" type="text" class="form-control" placeholder="auto" />
											</div>

											<div class="col-12">
												<label class="form-label">Model</label>
												<input
													v-model="model"
													type="text"
													class="form-control"
													placeholder="translategemma:4b"
												/>
											</div>
										</div>

										<div class="form-check form-switch mt-3">
											<input
												id="forceOcr"
												v-model="forceOcr"
												class="form-check-input"
												type="checkbox"
											/>
											<label class="form-check-label" for="forceOcr">Force OCR for PDF</label>
										</div>

										<div class="form-check form-switch mt-2">
											<input
												id="generateOutputFile"
												v-model="generateOutputFile"
												class="form-check-input"
												type="checkbox"
											/>
											<label class="form-check-label" for="generateOutputFile">
												Generate translated file
											</label>
										</div>

										<div class="d-flex gap-2 mt-4">
											<button
												class="btn btn-primary d-inline-flex align-items-center gap-2"
												:disabled="busy || !selectedFile || !authToken"
												@click="startUpload"
											>
												<span
													v-if="busy"
													class="spinner-border spinner-border-sm"
													role="status"
													aria-hidden="true"
												/>
												<span>{{ busy ? 'Processing' : 'Upload' }}</span>
											</button>
											<button class="btn btn-light" :disabled="busy" @click="resetForm">Reset</button>
										</div>

										<div v-if="error" class="alert alert-danger mt-3 mb-0">
											{{ error }}
										</div>
									</div>
								</div>
							</div>

							<div class="col-12 col-lg-7">
								<div class="card border h-100">
									<div class="card-body">
										<div class="d-flex justify-content-between align-items-center mb-3">
											<h6 class="mb-0">Job status</h6>
											<span class="badge" :class="statusBadgeClass">{{ statusLabel }}</span>
										</div>

										<div class="mb-3">
											<div class="small text-muted">Endpoint</div>
											<code class="d-block bg-light rounded px-2 py-2 text-break">
												{{ uploadEndpoint }}
											</code>
										</div>

										<div class="mb-3">
											<div class="small text-muted">Selected file</div>
											<div class="fw-medium">{{ selectedFile?.name || 'No file selected' }}</div>
										</div>

										<div v-if="(status === 'queued' || status === 'running') && progress.length" class="mb-3">
											<div class="small text-muted mb-2">Progress</div>
											<ul class="list-group list-group-flush border rounded">
												<li v-for="(item, index) in progress" :key="index" class="list-group-item">
													{{ item }}
												</li>
											</ul>
										</div>

										<div v-if="result" class="mb-3">
											<div class="small text-muted mb-2">Result</div>
											<div v-if="result.file" class="alert alert-success">
												Translated file created:
												<strong>{{ result.file.filename }}</strong>
												<div class="mt-2">
													<a
														class="btn btn-sm btn-outline-success"
														:href="fileContentUrl(result.file.id)"
														target="_blank"
														rel="noreferrer"
													>
														Open file
													</a>
												</div>
											</div>

											<div v-else-if="result.translation_text" class="alert alert-info mb-0">
												<pre class="mb-0 text-wrap">{{ result.translation_text }}</pre>
											</div>
										</div>

										<div v-if="review.length" class="mb-0">
											<div class="small text-muted mb-2">Review</div>
											<div class="table-responsive">
												<table class="table table-sm table-bordered align-middle">
													<thead class="table-light">
														<tr>
															<th style="width: 70px">Page</th>
															<th>Source</th>
															<th>Translated</th>
														</tr>
													</thead>
													<tbody>
														<tr v-for="(item, index) in review" :key="index">
															<td>{{ item.page ?? '-' }}</td>
															<td class="text-wrap">{{ item.source }}</td>
															<td class="text-wrap">{{ item.translated }}</td>
														</tr>
													</tbody>
												</table>
											</div>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

type ReviewItem = {
	page?: number | null;
	source: string;
	translated: string;
};

type TranslationResult = {
	file?: { id: string; filename: string } | null;
	review?: ReviewItem[];
	translation_text?: string;
	used_ocr?: boolean;
};

const props = withDefaults(
	defineProps<{
		apiBaseUrl?: string;
		token?: string;
	}>(),
	{
		apiBaseUrl: '/api/v1',
		token: ''
	}
);

const authToken = ref(props.token || '');
const selectedFile = ref<File | null>(null);
const targetLanguage = ref('Malay');
const sourceLanguage = ref('auto');
const model = ref('translategemma:4b');
const forceOcr = ref(false);
const generateOutputFile = ref(true);
const busy = ref(false);
const error = ref('');
const status = ref<'idle' | 'queued' | 'running' | 'completed' | 'failed'>('idle');
const progress = ref<string[]>([]);
const result = ref<TranslationResult | null>(null);
const review = ref<ReviewItem[]>([]);

const uploadEndpoint = computed(() => `${props.apiBaseUrl.replace(/\/$/, '')}/files/translation-jobs/upload`);

const statusLabel = computed(() => {
	switch (status.value) {
		case 'queued':
			return 'Queued';
		case 'running':
			return 'Running';
		case 'completed':
			return 'Completed';
		case 'failed':
			return 'Failed';
		default:
			return 'Idle';
	}
});

const statusBadgeClass = computed(() => {
	switch (status.value) {
		case 'completed':
			return 'bg-success-subtle text-success border border-success-subtle';
		case 'failed':
			return 'bg-danger-subtle text-danger border border-danger-subtle';
		case 'queued':
		case 'running':
			return 'bg-warning-subtle text-warning border border-warning-subtle';
		default:
			return 'bg-secondary-subtle text-secondary border border-secondary-subtle';
	}
});

function onFileChange(event: Event) {
	const input = event.target as HTMLInputElement;
	selectedFile.value = input.files?.[0] ?? null;
}

function resetForm() {
	selectedFile.value = null;
	targetLanguage.value = 'Malay';
	sourceLanguage.value = 'auto';
	model.value = 'translategemma:4b';
	forceOcr.value = false;
	generateOutputFile.value = true;
	error.value = '';
	status.value = 'idle';
	progress.value = [];
	result.value = null;
	review.value = [];
}

function fileContentUrl(fileId: string) {
	return `${props.apiBaseUrl.replace(/\/$/, '')}/files/${encodeURIComponent(fileId)}/content`;
}

async function startUpload() {
	error.value = '';
	result.value = null;
	review.value = [];
	progress.value = [];

	if (!authToken.value) {
		error.value = 'Missing API token.';
		return;
	}

	if (!selectedFile.value) {
		error.value = 'Select a document first.';
		return;
	}

	busy.value = true;
	status.value = 'queued';

	try {
		const formData = new FormData();
		formData.append('file', selectedFile.value);
		formData.append('target_language', targetLanguage.value);
		formData.append('source_language', sourceLanguage.value);
		formData.append('model', model.value);
		formData.append('force_ocr', String(forceOcr.value));
		formData.append('generate_output_file', String(generateOutputFile.value));

		const response = await fetch(uploadEndpoint.value, {
			method: 'POST',
			headers: {
				authorization: `Bearer ${authToken.value}`
			},
			body: formData
		});

		if (!response.ok) {
			const payload = await response.json().catch(() => ({}));
			throw new Error(payload?.detail || payload?.message || 'Upload failed');
		}

		const payload = await response.json();
		const job = payload.job;
		if (!job?.id) {
			throw new Error('Missing job id from API response');
		}

		await pollJob(job.id);
	} catch (err: any) {
		status.value = 'failed';
		error.value = err?.message || 'Upload failed';
	} finally {
		busy.value = false;
	}
}

async function pollJob(jobId: string) {
	for (let attempt = 0; attempt < 180; attempt += 1) {
		const response = await fetch(
			`${props.apiBaseUrl.replace(/\/$/, '')}/files/translation-jobs/${encodeURIComponent(jobId)}`,
			{
				method: 'GET',
				headers: {
					authorization: `Bearer ${authToken.value}`
				}
			}
		);

		if (!response.ok) {
			const payload = await response.json().catch(() => ({}));
			throw new Error(payload?.detail || 'Failed to read job status');
		}

		const payload = await response.json();
		const job = payload.job;
		status.value = job.status;
		progress.value = job.progress ?? [];

		if (job.status === 'completed') {
			result.value = job.result ?? null;
			review.value = job.result?.review ?? [];
			return;
		}

		if (job.status === 'failed') {
			throw new Error(job.error || 'Translation failed');
		}

		await new Promise((resolve) => setTimeout(resolve, 1000));
	}

	throw new Error('Timed out waiting for translation job');
}
</script>
