<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import { wrapLabel } from '../labels'

const items = ref([])
const papers = ref([])
const err = ref('')
const busy = ref(false)
const openRev = ref(null)
const openHist = ref(null)
const versions = ref({})

const blank = () => ({ name: '', overlap: 1.15, wrap_style: 'cross', paper_id: null, note: '' })
const form = reactive(blank())
const revForm = reactive({ overlap: 1.15, wrap_style: 'cross', paper_id: null, note: '' })

async function load() {
  err.value = ''
  try {
    items.value = (await getJSON('/api/recipes')).items
  } catch (e) {
    err.value = String(e.message || e)
  }
}

onMounted(async () => {
  try {
    papers.value = (await getJSON('/api/papers')).items
    if (papers.value.length) form.paper_id = papers.value[0].id
  } catch (e) {
    err.value = String(e.message || e)
  }
  load()
})

async function createRecipe() {
  err.value = ''
  busy.value = true
  try {
    await postJSON('/api/recipes', { ...form })
    Object.assign(form, blank())
    if (papers.value.length) form.paper_id = papers.value[0].id
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

function startRev(r) {
  openRev.value = openRev.value === r.id ? null : r.id
  revForm.overlap = r.overlap
  revForm.wrap_style = r.wrap_style
  revForm.paper_id = r.paper_id
  revForm.note = ''
}

async function bump(r) {
  err.value = ''
  busy.value = true
  try {
    await postJSON(`/api/recipes/${r.id}/versions`, { ...revForm })
    openRev.value = null
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

async function toggleActive(r) {
  err.value = ''
  busy.value = true
  try {
    await postJSON(`/api/recipes/${r.id}/active`, { active: !r.active })
    await load()
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

async function toggleHist(r) {
  if (openHist.value === r.id) {
    openHist.value = null
    return
  }
  openHist.value = r.id
  if (!versions.value[r.id]) {
    try {
      versions.value[r.id] = (await getJSON(`/api/recipes/${r.id}/versions`)).items
    } catch (e) {
      err.value = String(e.message || e)
    }
  }
}
</script>

<template>
  <div class="page">
    <h1>包装配方</h1>
    <p class="lede">配方绑定折边系数、丝带样式与默认纸卷。编辑只能升版（v1 起），历史版本永不改写。</p>
    <p v-if="err" class="bad">{{ err }}</p>

    <h2>新建配方</h2>
    <div class="row">
      <label class="field">名称
        <input v-model="form.name" type="text" placeholder="如：标准十字包" />
      </label>
      <label class="field">折边系数
        <input v-model.number="form.overlap" type="number" step="0.01" min="0.01" />
      </label>
      <label class="field">丝带样式
        <select v-model="form.wrap_style">
          <option value="cross">十字</option>
          <option value="band">单条</option>
        </select>
      </label>
      <label class="field">默认纸卷
        <select v-model.number="form.paper_id">
          <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </label>
      <button :disabled="busy" @click="createRecipe">新建（v1）</button>
    </div>

    <p v-if="!items.length" class="empty">还没有配方，先新建一个。</p>
    <ul v-if="items.length" class="item-list">
      <li v-for="r in items" :key="r.id" style="display:block">
        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:baseline">
          <span>
            <strong>{{ r.name }}</strong>
            <span class="pill" style="margin-left:.5rem">v{{ r.current_rev }}</span>
            <span v-if="!r.active" class="pill warn" style="margin-left:.35rem">停用</span>
          </span>
          <span class="meta">
            ×{{ r.overlap }} · {{ wrapLabel(r.wrap_style) }} · {{ r.paper_name ?? '纸卷#' + r.paper_id }}
          </span>
        </div>
        <div class="row" style="margin:.6rem 0 .2rem">
          <button class="ghost" @click="startRev(r)">升版</button>
          <button class="ghost" @click="toggleActive(r)">{{ r.active ? '停用' : '启用' }}</button>
          <button class="ghost" @click="toggleHist(r)">版本史</button>
        </div>

        <div v-if="openRev === r.id" class="row" style="margin:.4rem 0 .6rem">
          <label class="field">折边系数
            <input v-model.number="revForm.overlap" type="number" step="0.01" min="0.01" />
          </label>
          <label class="field">丝带样式
            <select v-model="revForm.wrap_style">
              <option value="cross">十字</option>
              <option value="band">单条</option>
            </select>
          </label>
          <label class="field">默认纸卷
            <select v-model.number="revForm.paper_id">
              <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </label>
          <button class="ribbon" :disabled="busy" @click="bump(r)">存为 v{{ r.current_rev + 1 }}</button>
        </div>

        <ul v-if="openHist === r.id" class="item-list" style="margin:.2rem 0 .8rem">
          <li v-for="v in versions[r.id] || []" :key="v.rev">
            <span>v{{ v.rev }}</span>
            <span class="meta">
              ×{{ v.overlap }} · {{ wrapLabel(v.wrap_style) }} · {{ v.paper_name ?? '纸卷#' + v.paper_id }}
              · {{ v.created_at?.slice(0, 10) }}
            </span>
          </li>
        </ul>
      </li>
    </ul>
  </div>
</template>
