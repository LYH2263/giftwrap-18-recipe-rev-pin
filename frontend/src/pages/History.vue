<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'

const items = ref([])
const err = ref('')

onMounted(async () => {
  try {
    items.value = (await getJSON('/api/runs')).items
  } catch (e) {
    err.value = String(e.message || e)
  }
})
</script>

<template>
  <div class="page">
    <h1>用纸档</h1>
    <p class="lede">算纸页「写入用纸档」后的落库结果，钉住当时的配方版本、用纸与丝带数值。</p>
    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">还没有写入过。先去算纸试一单。</p>
    <ul v-else class="item-list">
      <li v-for="r in items" :key="r.id">
        <router-link :to="`/runs/${r.id}`">
          #{{ r.id }} {{ r.box_name }}
          <span v-if="r.recipe_name" class="pill" style="margin-left:.5rem">
            {{ r.recipe_name }} v{{ r.recipe_rev }}
          </span>
          <span v-else class="pill" style="margin-left:.5rem">手动</span>
        </router-link>
        <span class="meta">{{ r.paper_m2 ?? '—' }} m²</span>
      </li>
    </ul>
  </div>
</template>
