<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import { wrapLabel } from '../labels'

const props = defineProps({ id: String })
const run = ref(null)
const err = ref('')
const recalc = ref(null)
const recalcErr = ref('')

onMounted(async () => {
  try {
    run.value = await getJSON(`/api/runs/${props.id}`)
  } catch (e) {
    err.value = String(e.message || e)
  }
})

async function verify() {
  recalcErr.value = ''
  recalc.value = null
  try {
    recalc.value = await postJSON(`/api/runs/${props.id}/recalc`, {})
  } catch (e) {
    recalcErr.value = String(e.message || e)
  }
}
</script>

<template>
  <div class="page" v-if="run">
    <h1>#{{ run.id }} {{ run.box_name }}</h1>
    <p class="lede">
      <span v-if="run.recipe_name" class="pill">{{ run.recipe_name }} v{{ run.recipe_rev }}</span>
      <span v-else class="pill">手动</span>
      <span style="margin-left:.6rem">{{ run.created_at?.replace('T', ' ').slice(0, 19) }} UTC</span>
    </p>
    <p v-if="run.note" class="meta">备注：{{ run.note }}</p>

    <ul class="item-list">
      <li><span>折边系数</span><span class="meta">×{{ run.overlap }}</span></li>
      <li><span>丝带样式</span><span class="meta">{{ wrapLabel(run.wrap_style) }}</span></li>
      <li><span>默认纸卷</span><span class="meta">{{ run.paper_name ?? '—' }}</span></li>
      <li><span>用纸面积</span><span class="meta">{{ run.paper_m2 ?? '—' }} m²</span></li>
      <li><span>丝带长度</span><span class="meta">{{ run.ribbon_m ?? '—' }} m</span></li>
    </ul>

    <div class="row" style="margin-top:1.25rem">
      <button @click="verify">再干算互证</button>
      <router-link class="btn ghost" to="/history">返回用纸档</router-link>
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
  <div class="page" v-else>
    <h1>用纸档</h1>
    <p v-if="err" class="bad">{{ err }}</p>
  </div>
</template>
