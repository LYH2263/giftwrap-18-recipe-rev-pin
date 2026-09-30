<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import { wrapLabel } from '../labels'

const props = defineProps({ id: String })
const recipe = ref(null)
const papers = ref([])
const err = ref('')
const busy = ref(false)
const form = ref({ overlap: 1.15, wrap_style: 'cross', paper_id: null })

async function load() {
  const [r, ps] = await Promise.all([
    getJSON(`/api/recipes/${props.id}`),
    getJSON('/api/papers'),
  ])
  recipe.value = r
  papers.value = ps.items
  const cur = r.revisions.find((v) => v.rev === r.current_rev)
  if (cur) {
    form.value.overlap = cur.overlap
    form.value.wrap_style = cur.wrap_style
    form.value.paper_id = cur.paper_id
  }
}

onMounted(async () => {
  try {
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  }
})

async function bump() {
  err.value = ''
  busy.value = true
  try {
    await postJSON(`/api/recipes/${props.id}/revisions`, {
      overlap: Number(form.value.overlap),
      wrap_style: form.value.wrap_style,
      paper_id: form.value.paper_id,
    })
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

async function toggle() {
  err.value = ''
  busy.value = true
  try {
    const action = recipe.value.active === 1 ? 'deactivate' : 'activate'
    await postJSON(`/api/recipes/${props.id}/${action}`, {})
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

function fmt(ts) {
  return ts ? new Date(ts).toLocaleString() : ''
}
</script>

<template>
  <div class="page">
    <p v-if="err" class="bad">{{ err }}</p>
    <template v-else-if="recipe">
      <h1>
        {{ recipe.name }}
        <span class="pill" :class="{ warn: recipe.active !== 1 }">
          {{ recipe.active === 1 ? '启用' : '停用' }}
        </span>
      </h1>
      <p class="lede">当前 v{{ recipe.current_rev }}。每次编辑追加新版本，旧版本保留不动；算纸与落库只吃当前版。</p>

      <h2 style="font-size:1.05rem; margin-top:1.5rem">版本历史</h2>
      <ul class="item-list">
        <li v-for="v in recipe.revisions" :key="v.rev">
          <span>
            v{{ v.rev }}
            <span v-if="v.rev === recipe.current_rev" class="pill">当前</span>
          </span>
          <span class="meta">
            ×{{ v.overlap }} · {{ wrapLabel(v.wrap_style) }} · {{ v.paper_name ?? '纸#' + v.paper_id }} · {{ fmt(v.created_at) }}
          </span>
        </li>
      </ul>

      <div class="result-board">
        <strong>升版（新建 v{{ recipe.current_rev + 1 }}）</strong>
        <fieldset :disabled="recipe.active !== 1 || busy" style="border:0; padding:0; margin:0.75rem 0 0">
          <div class="row">
            <input v-model.number="form.overlap" type="number" step="0.01" min="0.01" placeholder="折边系数" style="min-width: 120px" />
            <select v-model="form.wrap_style" style="min-width: 130px">
              <option value="cross">十字捆扎</option>
              <option value="band">缎带单扎</option>
            </select>
            <select v-model.number="form.paper_id" style="min-width: 160px">
              <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <button :disabled="busy" @click="bump">保存升版</button>
          </div>
          <p v-if="recipe.active !== 1" class="meta">配方已停用，需先重新启用才能升版。</p>
        </fieldset>
        <div class="row" style="margin-top:1rem">
          <button class="ghost" :disabled="busy" @click="toggle">
            {{ recipe.active === 1 ? '停用配方' : '重新启用' }}
          </button>
        </div>
      </div>

      <div class="row" style="margin-top: 1.25rem">
        <router-link class="btn ghost" to="/recipes">返回配方</router-link>
      </div>
    </template>
  </div>
</template>
