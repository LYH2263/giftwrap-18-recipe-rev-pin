<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import { wrapLabel } from '../labels'

const items = ref([])
const papers = ref([])
const err = ref('')
const busy = ref(false)
const form = ref({ name: '', overlap: 1.15, wrap_style: 'cross', paper_id: null })

async function load() {
  const [rs, ps] = await Promise.all([getJSON('/api/recipes'), getJSON('/api/papers')])
  items.value = rs.items
  papers.value = ps.items
  if (form.value.paper_id === null && ps.items.length) form.value.paper_id = ps.items[0].id
}

onMounted(async () => {
  try {
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  }
})

async function createRecipe() {
  err.value = ''
  busy.value = true
  try {
    await postJSON('/api/recipes', {
      name: form.value.name.trim(),
      overlap: Number(form.value.overlap),
      wrap_style: form.value.wrap_style,
      paper_id: form.value.paper_id,
    })
    form.value.name = ''
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1>包装配方</h1>
    <p class="lede">配方绑定折边系数、丝带样式与默认用纸；编辑只能升版，历史版本永不回改。用纸仅登记默认卷，不进入面积计算。</p>

    <div class="result-board" style="margin-bottom: 1.5rem">
      <strong>新建配方</strong>
      <div class="row" style="margin-top: 0.75rem; margin-bottom: 0">
        <input v-model="form.name" placeholder="配方名称" style="min-width: 180px" />
        <input v-model.number="form.overlap" type="number" step="0.01" min="0.01" placeholder="折边系数" style="min-width: 120px" />
        <select v-model="form.wrap_style" style="min-width: 130px">
          <option value="cross">十字捆扎</option>
          <option value="band">缎带单扎</option>
        </select>
        <select v-model.number="form.paper_id" style="min-width: 160px">
          <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button :disabled="busy" @click="createRecipe">新建（v1）</button>
      </div>
    </div>

    <p v-if="err" class="bad">{{ err }}</p>
    <p v-else-if="!items.length" class="empty">还没有配方。</p>
    <div v-else class="paper-grid">
      <router-link v-for="r in items" :key="r.id" class="paper-tile" :to="`/recipes/${r.id}`">
        <strong>{{ r.name }}</strong>
        <span class="meta">
          <span class="pill" :class="{ warn: r.active !== 1 }">{{ r.active === 1 ? '启用' : '停用' }}</span>
          v{{ r.current_rev }}
        </span>
        <span class="meta">折边 ×{{ r.overlap }} · {{ wrapLabel(r.wrap_style) }}</span>
        <span class="meta">默认用纸：{{ r.paper_name ?? '—' }}</span>
      </router-link>
    </div>
  </div>
</template>
