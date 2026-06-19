<template>
  <section class="video-workbench__provider-settings" aria-label="Provider Settings">
    <div>
      <p class="video-workbench__eyebrow">Provider Settings</p>
      <h2>Nano Banana</h2>
    </div>
    <div class="video-workbench__settings-grid">
      <div class="video-workbench__field">
        <label for="nano-banana-api-key">API Key</label>
        <input
          id="nano-banana-api-key"
          v-model="nanoBananaSettings.api_key"
          type="password"
          placeholder="Nano Banana API key"
        >
      </div>
      <div class="video-workbench__field">
        <label for="nano-banana-base-url">Base URL</label>
        <input
          id="nano-banana-base-url"
          v-model="nanoBananaSettings.base_url"
          type="text"
          placeholder="https://..."
        >
      </div>
      <button
        type="button"
        data-testid="save-nano-banana-settings"
        :disabled="isSavingProviderSettings"
        @click="$emit('save-nano-banana')"
      >
        {{ isSavingProviderSettings ? '保存中...' : 'Save provider settings' }}
      </button>
    </div>
    <p v-if="providerMessage" class="video-workbench__upload-message">{{ providerMessage }}</p>
    <div class="video-workbench__settings-grid">
      <div class="video-workbench__field">
        <label for="jimeng-api-key">Jimeng API Key</label>
        <input
          id="jimeng-api-key"
          v-model="jimengSettings.api_key"
          type="password"
          placeholder="Jimeng API key"
        >
      </div>
      <div class="video-workbench__field">
        <label for="jimeng-base-url">Jimeng Base URL</label>
        <input
          id="jimeng-base-url"
          v-model="jimengSettings.base_url"
          type="text"
          placeholder="https://..."
        >
      </div>
      <div class="video-workbench__field">
        <label for="jimeng-access-key">Jimeng Access Key</label>
        <input
          id="jimeng-access-key"
          v-model="jimengSettings.access_key"
          type="password"
          placeholder="Jimeng access key"
        >
      </div>
      <div class="video-workbench__field">
        <label for="jimeng-secret-key">Jimeng Secret Key</label>
        <input
          id="jimeng-secret-key"
          v-model="jimengSettings.secret_key"
          type="password"
          placeholder="Jimeng secret key"
        >
      </div>
      <div class="video-workbench__field">
        <label for="jimeng-region">Jimeng Region</label>
        <input
          id="jimeng-region"
          v-model="jimengSettings.region"
          type="text"
          placeholder="cn-north-1"
        >
      </div>
      <div class="video-workbench__field">
        <label for="jimeng-endpoint">Jimeng Endpoint</label>
        <input
          id="jimeng-endpoint"
          v-model="jimengSettings.endpoint"
          type="text"
          placeholder="https://..."
        >
      </div>
      <div class="video-workbench__field">
        <label for="jimeng-model">Jimeng Model</label>
        <input
          id="jimeng-model"
          v-model="jimengSettings.model"
          type="text"
          placeholder="jimeng-v3"
        >
      </div>
      <label class="video-workbench__checkbox" for="jimeng-enabled">
        <input id="jimeng-enabled" v-model="jimengSettings.enabled" type="checkbox">
        Enable Jimeng
      </label>
      <button
        type="button"
        data-testid="save-jimeng-settings"
        :disabled="isSavingJimengSettings"
        @click="$emit('save-jimeng')"
      >
        {{ isSavingJimengSettings ? '保存中...' : 'Save Jimeng settings' }}
      </button>
    </div>
    <p v-if="jimengProviderMessage" class="video-workbench__upload-message">
      {{ jimengProviderMessage }}
    </p>
  </section>
</template>

<script setup>
defineProps({
  nanoBananaSettings: { type: Object, required: true },
  jimengSettings: { type: Object, required: true },
  providerMessage: { type: String, default: '' },
  jimengProviderMessage: { type: String, default: '' },
  isSavingProviderSettings: { type: Boolean, default: false },
  isSavingJimengSettings: { type: Boolean, default: false }
})

defineEmits(['save-nano-banana', 'save-jimeng'])
</script>
