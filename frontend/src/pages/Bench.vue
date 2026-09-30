<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import { wrapLabel } from '../labels'
import BoxUnfold from '../components/BoxUnfold.vue'

const boxes = ref([])
const recipes = ref([])
const runs = ref([])
const bid = ref(1)
const recipeId = ref(null)
const out = ref(null)
const err = ref('')
const busy = ref(false)

const selectedRecipe = computed(() => recipes.value.find((r) => r.id === recipeId.value) || null)

onMounted(async () => {
  try {
    const [bs, rs, us] = await Promise.all([
      getJSON('/api/boxes'),
      getJSON('/api/recipes/active'),
      getJSON('/api/runs'),
    ])
    boxes.value = bs.items.filter((b) => b.data_quality === 'clean')
    recipes.value = rs.items
    runs.value = us.items
    if (boxes.value.length) bid.value = boxes.value[0].id
  } catch (e) {
    err.value = String(e.message || e)
  }
})

async function go(save) {
  err.value = ''
  busy.value = true
  try {
    const rid = recipeId.value
    if (save) {
      out.value = await postJSON('/api/estimate', { box_id: bid.value, save: true, recipe_id: rid ?? null })
    } else {
      const qs = new URLSearchParams({ box_id: String(bid.value) })
      if (rid != null) qs.set('recipe_id', String(rid))
      out.value = await getJSON(`/api/estimate?${qs}`)
    }
    runs.value = (await getJSON('/api/runs')).items
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}

// —— 旧单复核 ——
const oldRunId = ref(null)
const recalc = ref(null)
const recalcErr = ref('')
const oldRun = computed(() => runs.value.find((r) => r.id === oldRunId.value) || null)

async function verify() {
  recalcErr.value = ''
  recalc.value = null
  if (oldRunId.value == null) return
  try {
    recalc.value = await postJSON(`/api/runs/${oldRunId.value}/recalc`, {})
  } catch (e) {
    recalcErr.value = String(e.message || e)
  }
}
</script>

<template>
  <div class="page">
    <h1>算纸</h1>
    <p class="lede">先试算看面积与展开，确认后再写入用纸档。可选用配方：试算与落库都吃配方当前版。</p>
    <div class="row">
      <label class="field">配方
        <select v-model.number="recipeId">
          <option :value="null">不使用配方（手动）</option>
          <option v-for="r in recipes" :key="r.id" :value="r.id">
            {{ r.name }} v{{ r.current_rev }}
          </option>
        </select>
      </label>
      <label class="field">盒型
        <select v-model.number="bid">
          <option v-for="b in boxes" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>
      </label>
      <button :disabled="busy" @click="go(false)">试算</button>
      <button class="ribbon" :disabled="busy" @click="go(true)">写入用纸档</button>
    </div>
    <p v-if="selectedRecipe" class="meta">
      当前版 v{{ selectedRecipe.current_rev }}：折边 ×{{ selectedRecipe.overlap }}
      · 丝带 {{ wrapLabel(selectedRecipe.wrap_style) }}
      · 默认纸卷 {{ selectedRecipe.paper_name ?? '纸卷#' + selectedRecipe.paper_id }}
    </p>
    <p v-if="err" class="bad">{{ err }}</p>
    <div v-if="out" class="result-board">
      <p class="meta" style="margin-bottom:.4rem">
        <span v-if="out.recipe" class="pill">{{ out.recipe.name }} v{{ out.recipe.rev }}</span>
        <span v-else class="pill">手动</span>
        <span v-if="out.paper" style="margin-left:.5rem">{{ out.paper.name }}</span>
      </p>
      <div class="figure">{{ out.paper_m2 }}<span>m²</span></div>
      <p class="stat-line" v-if="out.ribbon">
        {{ wrapLabel(out.ribbon.wrap_style) }}丝带约 {{ out.ribbon.ribbon_m ?? out.ribbon }} m
      </p>
      <BoxUnfold
        :l="out.box.length"
        :w="out.box.width"
        :h="out.box.height"
        :paper-m2="out.paper_m2"
      />
    </div>

    <h2 style="margin-top:2rem">旧单复核</h2>
    <p class="lede">选一张已写入的旧单，按其钉住的配方版再干算，与存档数值互证。</p>
    <div class="row">
      <label class="field">旧单
        <select v-model.number="oldRunId">
          <option :value="null">选择旧单…</option>
          <option v-for="r in runs" :key="r.id" :value="r.id">
            #{{ r.id }} {{ r.box_name }}{{ r.recipe_name ? ` · ${r.recipe_name} v${r.recipe_rev}` : ' · 手动' }}
          </option>
        </select>
      </label>
      <button :disabled="oldRunId == null" @click="verify">互证</button>
    </div>
    <div v-if="oldRun" class="meta" style="margin-bottom:.6rem">
      存档：折边 ×{{ oldRun.overlap }} · {{ wrapLabel(oldRun.wrap_style) }}
      <template v-if="oldRun.paper_name"> · {{ oldRun.paper_name }}</template>
      · 用纸 {{ oldRun.paper_m2 ?? '—' }} m² · 丝带 {{ oldRun.ribbon_m ?? '—' }} m
    </div>
    <p v-if="recalcErr" class="bad">{{ recalcErr }}</p>
    <div v-if="recalc" class="result-board">
      <p>
        <span class="pill" :class="{ warn: !recalc.matches }">
          {{ recalc.matches ? '一致' : '不一致' }}
        </span>
        <span v-if="recalc.reason" class="bad" style="margin-left:.6rem">{{ recalc.reason }}</span>
      </p>
      <ul v-if="recalc.recomputed" class="item-list">
        <li><span>用纸 m²</span><span class="meta">存档 {{ recalc.stored.paper_m2 }} → 重算 {{ recalc.recomputed.paper_m2 }}</span></li>
        <li><span>丝带 m</span><span class="meta">存档 {{ recalc.stored.ribbon_m }} → 重算 {{ recalc.recomputed.ribbon_m }}</span></li>
        <li><span>折边系数</span><span class="meta">存档 ×{{ recalc.stored.overlap }} → 重算 ×{{ recalc.recomputed.overlap }}</span></li>
        <li><span>丝带样式</span><span class="meta">{{ wrapLabel(recalc.stored.wrap_style) }} → {{ wrapLabel(recalc.recomputed.wrap_style) }}</span></li>
      </ul>
    </div>
  </div>
</template>
