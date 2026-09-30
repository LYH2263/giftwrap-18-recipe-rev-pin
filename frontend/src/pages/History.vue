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
    <p class="lede">算纸页「写入用纸档」后的落库结果，按次钉住盒名、配方版与当时面积；点行查看详情。</p>
    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">还没有写入过。先去算纸试一单。</p>
    <ul v-else class="item-list">
      <li v-for="r in items" :key="r.id">
        <router-link :to="`/history/${r.id}`">
          {{ r.box_name }}
          <span v-if="r.recipe_id" class="pill" style="margin-left:0.5rem">{{ r.recipe_name }} v{{ r.recipe_rev }}</span>
        </router-link>
        <span class="meta">{{ r.paper_m2 ?? r.result?.paper_m2 }} m²</span>
      </li>
    </ul>
  </div>
</template>
