<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let showPassword = false;
	let showConfirmPassword = false;

	let ldapUsername = '';
	const AUTH_APP_LOGO_URL = 'https://dev.d-reams.com/img/logo-d.7378c4bf.png';
	const AUTH_LOGIN_LOGO_URL = 'https://dev.d-reams.com/img/logo-light-inside.7841f3f2.png';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		document.querySelectorAll<HTMLImageElement>('[data-auth-brand]').forEach((logo) => {
			logo.src = AUTH_LOGIN_LOGO_URL;
			logo.style.filter = '';
			logo.style.borderRadius = '0';
		});
		document.querySelectorAll<HTMLImageElement>('[data-auth-logo]').forEach((logo) => {
			logo.src = AUTH_APP_LOGO_URL;
			logo.style.filter = '';
			logo.style.borderRadius = '0';
		});
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		// Auto-redirect to SSO when OAUTH_AUTO_REDIRECT is enabled and the
		// deployment is unambiguously SSO-only (single provider, no login form,
		// no LDAP). Suppressed by ?form=, ?error=, onboarding, trusted-header
		// auth, or an existing session/token.
		if ($config?.oauth?.auto_redirect && !form && !error) {
			const providers = Object.keys($config?.oauth?.providers ?? {});
			if (
				providers.length === 1 &&
				$config?.features?.auth !== false &&
				$config?.features?.enable_login_form === false &&
				!$config?.features?.enable_ldap &&
				!$config?.features?.auth_trusted_header &&
				!$config?.onboarding &&
				!localStorage.token &&
				!document.cookie.split('; ').some((c) => c.startsWith('token='))
			) {
				window.location.href = `${WEBUI_BASE_URL}/oauth/${providers[0]}/login`;
				return;
			}
		}

		loaded = true;
		setLogoImage();

		if (($config?.features?.auth_trusted_header ?? false) || $config?.features?.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
	<link crossorigin="anonymous" rel="icon" href={AUTH_APP_LOGO_URL} />
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] relative bg-[var(--auth-page-bg)]" id="auth-page">
	<div class="w-full h-full absolute top-0 left-0 bg-[var(--auth-page-bg)]"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	{#if loaded}
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-[var(--auth-page-text)]"
			id="auth-container"
		>
			<div class="w-full px-10 min-h-screen flex flex-col text-center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full sm:max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium text-[var(--auth-page-text)]"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
						<div class="my-auto flex flex-col justify-center items-center">
							<div class="auth-panel sm:max-w-md my-auto w-full">
								{#if $config?.metadata?.auth_logo_position === 'center'}
									<div class="flex justify-center mb-6">
										<img
											id="logo"
											data-auth-brand
											crossorigin="anonymous"
											src={AUTH_LOGIN_LOGO_URL}
											class="h-10 w-auto object-contain"
											alt="{$WEBUI_NAME} logo"
										/>
									</div>
								{/if}
							<form
								class=" flex flex-col justify-center"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								<div class="mb-1">
									<div class="mb-5 flex flex-col items-center gap-3 text-center">
										<img
											data-auth-brand
											crossorigin="anonymous"
											src={AUTH_LOGIN_LOGO_URL}
											class="h-10 w-auto object-contain"
											alt="D-Reams logo"
										/>
										<div class="text-[1.625rem] leading-tight font-semibold">
											{#if $config?.onboarding ?? false}
												{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
											{:else if mode === 'ldap'}
												{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
											{:else if mode === 'signin'}
												{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
											{:else}
												{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
											{/if}
										</div>

									{#if $config?.onboarding ?? false}
										<div class="mt-1 text-xs font-medium text-[var(--auth-page-muted)]">
											ⓘ {$WEBUI_NAME}
											{$i18n.t(
												'does not make any external connections, and your data stays securely on your locally hosted server.'
											)}
										</div>
									{/if}
								</div>

								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<div class="flex flex-col mt-4">
										{#if mode === 'signup'}
											<div class="mb-2">
												<label for="name" class="auth-label"
													>{$i18n.t('Name')}</label
												>
											<input
													bind:value={name}
													type="text"
													id="name"
													class="auth-input my-0.5 w-full text-sm outline-hidden"
													autocomplete="name"
													placeholder={$i18n.t('Enter Your Full Name')}
													required
												/>
											</div>
										{/if}

										{#if mode === 'ldap'}
											<div class="mb-2">
												<label for="username" class="auth-label"
													>{$i18n.t('Username')}</label
												>
											<input
													bind:value={ldapUsername}
													type="text"
													class="auth-input my-0.5 w-full text-sm outline-hidden"
													autocomplete="username"
													name="username"
													id="username"
													placeholder={$i18n.t('Enter Your Username')}
													required
												/>
											</div>
										{:else}
											<div class="mb-2">
												<label for="email" class="auth-label"
													>{$i18n.t('Email')}</label
												>
											<input
													bind:value={email}
													type="email"
													id="email"
													class="auth-input my-0.5 w-full text-sm outline-hidden"
													autocomplete="email"
													name="email"
													placeholder={$i18n.t('Enter Your Email')}
													required
												/>
											</div>
										{/if}

										<div>
											<label for="password" class="auth-label"
												>{$i18n.t('Password')}</label
											>
											<div class="auth-password-input my-0.5 w-full">
												<input
													bind:value={password}
													type={showPassword ? 'text' : 'password'}
													id="password"
													class="auth-password-native text-sm outline-hidden"
													autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
													name="password"
													placeholder={$i18n.t('Enter Your Password')}
													required
													aria-required="true"
												/>
												<button
													class="auth-password-toggle"
													type="button"
													aria-pressed={showPassword}
													aria-label={$i18n.t('Make password visible in the user interface')}
													on:click={(e) => {
														e.preventDefault();
														showPassword = !showPassword;
													}}
												>
													{#if showPassword}
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 16 16"
															fill="currentColor"
															aria-hidden="true"
															class="size-4"
														>
															<path
																fill-rule="evenodd"
																d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l10.5 10.5a.75.75 0 1 0 1.06-1.06l-1.322-1.323a7.012 7.012 0 0 0 2.16-3.11.87.87 0 0 0 0-.567A7.003 7.003 0 0 0 4.82 3.76l-1.54-1.54Zm3.196 3.195 1.135 1.136A1.502 1.502 0 0 1 9.45 8.389l1.136 1.135a3 3 0 0 0-4.109-4.109Z"
																clip-rule="evenodd"
															/>
															<path
																d="m7.812 10.994 1.816 1.816A7.003 7.003 0 0 1 1.38 8.28a.87.87 0 0 1 0-.566 6.985 6.985 0 0 1 1.113-2.039l2.513 2.513a3 3 0 0 0 2.806 2.806Z"
															/>
														</svg>
													{:else}
														<svg
															xmlns="http://www.w3.org/2000/svg"
															viewBox="0 0 16 16"
															fill="currentColor"
															class="size-4"
															aria-hidden="true"
														>
															<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
															<path
																fill-rule="evenodd"
																d="M1.38 8.28a.87.87 0 0 1 0-.566 7.003 7.003 0 0 1 13.238.006.87.87 0 0 1 0 .566A7.003 7.003 0 0 1 1.379 8.28ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
																clip-rule="evenodd"
															/>
														</svg>
													{/if}
												</button>
											</div>
										</div>

										{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
											<div class="mt-2">
												<label
													for="confirm-password"
													class="auth-label"
													>{$i18n.t('Confirm Password')}</label
												>
												<div class="auth-password-input my-0.5 w-full">
													<input
														bind:value={confirmPassword}
														type={showConfirmPassword ? 'text' : 'password'}
														id="confirm-password"
														class="auth-password-native text-sm outline-hidden"
														autocomplete="new-password"
														name="confirm-password"
														placeholder={$i18n.t('Confirm Your Password')}
														required
													/>
													<button
														class="auth-password-toggle"
														type="button"
														aria-pressed={showConfirmPassword}
														aria-label={$i18n.t('Make password visible in the user interface')}
														on:click={(e) => {
															e.preventDefault();
															showConfirmPassword = !showConfirmPassword;
														}}
													>
														{#if showConfirmPassword}
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																aria-hidden="true"
																class="size-4"
															>
																<path
																	fill-rule="evenodd"
																	d="M3.28 2.22a.75.75 0 0 0-1.06 1.06l10.5 10.5a.75.75 0 1 0 1.06-1.06l-1.322-1.323a7.012 7.012 0 0 0 2.16-3.11.87.87 0 0 0 0-.567A7.003 7.003 0 0 0 4.82 3.76l-1.54-1.54Zm3.196 3.195 1.135 1.136A1.502 1.502 0 0 1 9.45 8.389l1.136 1.135a3 3 0 0 0-4.109-4.109Z"
																	clip-rule="evenodd"
																/>
																<path
																	d="m7.812 10.994 1.816 1.816A7.003 7.003 0 0 1 1.38 8.28a.87.87 0 0 1 0-.566 6.985 6.985 0 0 1 1.113-2.039l2.513 2.513a3 3 0 0 0 2.806 2.806Z"
																/>
															</svg>
														{:else}
															<svg
																xmlns="http://www.w3.org/2000/svg"
																viewBox="0 0 16 16"
																fill="currentColor"
																class="size-4"
																aria-hidden="true"
															>
																<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
																<path
																	fill-rule="evenodd"
																	d="M1.38 8.28a.87.87 0 0 1 0-.566 7.003 7.003 0 0 1 13.238.006.87.87 0 0 1 0 .566A7.003 7.003 0 0 1 1.379 8.28ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
																	clip-rule="evenodd"
																/>
															</svg>
														{/if}
													</button>
												</div>
											</div>
										{/if}
									</div>
								{/if}
								<div class="mt-5">
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										{#if mode === 'ldap'}
											<button
												class="auth-button transition w-full font-medium text-sm py-2.5"
												type="submit"
											>
												{$i18n.t('Authenticate')}
											</button>
										{:else}
											<button
												class="auth-button transition w-full font-medium text-sm py-2.5"
												type="submit"
											>
												{mode === 'signin'
													? $i18n.t('Sign in')
													: ($config?.onboarding ?? false)
														? $i18n.t('Create Admin Account')
														: $i18n.t('Create Account')}
											</button>

											{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
												<div class=" mt-4 text-sm text-center">
													{mode === 'signin'
														? $i18n.t("Don't have an account?")
														: $i18n.t('Already have an account?')}

													<button
														class=" font-medium underline"
														type="button"
														on:click={() => {
															if (mode === 'signin') {
																mode = 'signup';
															} else {
																mode = 'signin';
															}
														}}
													>
														{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
													</button>
												</div>
											{/if}
										{/if}
									{/if}
								</div>
							</form>

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="inline-flex items-center justify-center w-full">
									<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<span
											class="px-3 text-sm font-medium text-gray-900 dark:text-white bg-transparent"
											>{$i18n.t('or')}</span
										>
									{/if}

									<hr class="w-32 h-px my-4 border-0 dark:bg-gray-100/10 bg-gray-700/10" />
								</div>
								<div class="flex flex-col space-y-2">
									{#if $config?.oauth?.providers?.google}
										<button
											class="auth-button flex justify-center items-center transition w-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/><path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/><path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/><path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/><path fill="none" d="M0 0h48v48H0z" />
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.microsoft}
										<button
											class="auth-button flex justify-center items-center transition w-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
													x="1"
													y="11"
													width="9"
													height="9"
													fill="#00a4ef"
												/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
													x="11"
													y="11"
													width="9"
													height="9"
													fill="#ffb900"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.github}
										<button
											class="auth-button flex justify-center items-center transition w-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.oidc}
										<button
											class="auth-button flex justify-center items-center transition w-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-6 mr-3"
												aria-hidden="true"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>

											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.feishu}
										<button
											class="auth-button flex justify-center items-center transition w-full font-medium text-sm py-2.5"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
										</button>
									{/if}
								</div>
							{/if}

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div class="mt-2">
									<button
										class="flex justify-center items-center text-xs w-full text-center underline"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										<span
											>{mode === 'ldap'
												? $i18n.t('Continue with Email')
												: $i18n.t('Continue with LDAP')}</span
										>
									</button>
								</div>
							{/if}
						</div>
						{#if $config?.metadata?.login_footer}
							<div class="max-w-3xl mx-auto">
								<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		{#if !$config?.metadata?.auth_logo_position}
			<div class="fixed m-10 z-50">
				<div class="flex space-x-2">
					<div class=" self-center">
						<img
							id="logo"
							data-auth-logo
							crossorigin="anonymous"
							src={AUTH_APP_LOGO_URL}
							class="w-6 object-contain"
							alt=""
						/>
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	:global(:root) {
		--auth-page-bg: #f4f7fb;
		--auth-page-surface: rgba(255, 255, 255, 0.88);
		--auth-page-border: rgba(15, 23, 42, 0.1);
		--auth-page-text: #0f172a;
		--auth-page-muted: #64748b;
		--auth-page-input: rgba(255, 255, 255, 0.95);
		--auth-page-shadow: 0 24px 80px rgba(15, 23, 42, 0.14);
	}

	:global(html.dark),
	:global(.dark) {
		--auth-page-bg: #0b1220;
		--auth-page-surface: rgba(15, 23, 42, 0.88);
		--auth-page-border: rgba(148, 163, 184, 0.16);
		--auth-page-text: #e2e8f0;
		--auth-page-muted: #94a3b8;
		--auth-page-input: rgba(15, 23, 42, 0.92);
		--auth-page-shadow: 0 24px 80px rgba(0, 0, 0, 0.36);
	}

	@media (prefers-color-scheme: dark) {
		:global(html:not(.light):not(.dark)),
		:global(body:not(.light):not(.dark)) {
			--auth-page-bg: #0b1220;
			--auth-page-surface: rgba(15, 23, 42, 0.88);
			--auth-page-border: rgba(148, 163, 184, 0.16);
			--auth-page-text: #e2e8f0;
			--auth-page-muted: #94a3b8;
			--auth-page-input: rgba(15, 23, 42, 0.92);
			--auth-page-shadow: 0 24px 80px rgba(0, 0, 0, 0.36);
		}
	}

	#auth-page {
		background: var(--auth-page-bg);
	}

	.auth-panel {
		background: var(--auth-page-surface);
		border: 1px solid var(--auth-page-border);
		border-radius: 8px;
		box-shadow: var(--auth-page-shadow);
		padding: 2rem;
		color: var(--auth-page-text);
		backdrop-filter: blur(16px);
	}

	.auth-label {
		display: block;
		margin-bottom: 0.25rem;
		text-align: left;
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--auth-page-muted);
	}

	.auth-input {
		min-height: 3rem;
		border: 1px solid var(--auth-page-border);
		border-radius: 10px;
		background: var(--auth-page-input);
		color: var(--auth-page-text);
		padding: 0.75rem 0.875rem;
		appearance: none;
		-webkit-appearance: none;
		transition:
			border-color 120ms ease,
			box-shadow 120ms ease,
			background-color 120ms ease,
			transform 120ms ease;
	}

	.auth-input:-webkit-autofill,
	.auth-input:-webkit-autofill:hover,
	.auth-input:-webkit-autofill:focus,
	.auth-input:-webkit-autofill:active,
	.auth-password-native:-webkit-autofill,
	.auth-password-native:-webkit-autofill:hover,
	.auth-password-native:-webkit-autofill:focus,
	.auth-password-native:-webkit-autofill:active {
		-webkit-box-shadow: 0 0 0 1000px var(--auth-page-input) inset;
		-webkit-text-fill-color: var(--auth-page-text);
		caret-color: var(--auth-page-text);
		transition: background-color 9999s ease-in-out 0s;
	}

	.auth-input:focus-within,
	.auth-input:focus {
		border-color: var(--skote-primary);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--skote-primary) 22%, transparent);
	}

	.auth-input:hover {
		border-color: color-mix(in srgb, var(--auth-page-border) 70%, var(--skote-primary));
	}

	.auth-password-input {
		min-height: 3rem;
		border: 1px solid var(--auth-page-border);
		border-radius: 10px;
		background: var(--auth-page-input);
		color: var(--auth-page-text);
		padding: 0.75rem 0.875rem;
		display: flex;
		align-items: center;
		overflow: hidden;
		gap: 0.5rem;
		transition:
			border-color 120ms ease,
			box-shadow 120ms ease,
			background-color 120ms ease,
			transform 120ms ease;
	}

	.auth-password-input:hover {
		border-color: color-mix(in srgb, var(--auth-page-border) 70%, var(--skote-primary));
	}

	.auth-password-input:focus-within {
		border-color: var(--skote-primary);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--skote-primary) 22%, transparent);
	}

	.auth-password-input :global(input) {
		min-width: 0;
		flex: 1;
		border: 0;
		appearance: none;
		-webkit-appearance: none;
		background: transparent;
		color: var(--auth-page-text);
		padding: 0;
		margin: 0;
		box-shadow: none;
		outline: none;
		line-height: 1.5;
	}

	.auth-password-input :global(input::placeholder) {
		color: color-mix(in srgb, var(--auth-page-muted) 72%, transparent);
	}

	.auth-password-toggle {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--auth-page-muted);
		background: transparent;
		padding: 0;
		border: 0;
		line-height: 1;
	}

	.auth-password-toggle:hover {
		color: var(--auth-page-text);
	}

	.auth-input::placeholder {
		color: color-mix(in srgb, var(--auth-page-muted) 72%, transparent);
	}

	.auth-button {
		border-radius: 6px;
		background: var(--skote-primary);
		color: #ffffff;
	}

	.auth-button:hover {
		background: var(--skote-primary-hover);
	}

	@media (max-width: 640px) {
		.auth-panel {
			padding: 1.5rem;
		}
	}
</style>
