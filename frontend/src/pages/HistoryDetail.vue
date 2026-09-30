<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
import { wrapLabel } from '../labels'

const props = defineProps({ id: String })
const run = ref(null)
const err = ref('')
const check = ref(null)
const busy = ref(false)

onMounted(async () => {
  try {
    run.value = await getJSON(`/api/runs/${props.id}`)
  } catch (e) {
    err.value = String(e.message || e)
  }
})

async function recompute() {
  err.value = ''
  check.value = null
  busy.value = true
  try {
    const q = new URLSearchParams({
      box_id: run.value.box_id,
      recipe_id: run.value.recipe_id,
      recipe_rev: run.value.recipe_rev,
    })
    const re = await getJSON(`/api/estimate?${q.toString()}`)
    check.value = {
      paperOk: re.paper_m2 === run.value.paper_m2,
      ribbonOk: re.ribbon.ribbon_m === run.value.ribbon_m,
      paper_m2: re.paper_m2,
      ribbon_m: re.ribbon.ribbon_m,
    }
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
    <template v-else-if="run">
      <h1>{{ run.box_name }} <span class="meta" style="font-size:1rem">#{{ run.id }}</span></h1>
      <p class="lede">落库时钉住的配方版与当时算值；配方之后再升版也不会回刷本单。</p>

      <ul class="item-list">
        <li v-if="run.recipe_id">
          <span>配方（钉版）</span>
          <span class="meta"><span class="pill">{{ run.recipe_name }} v{{ run.recipe_rev }}</span></span>
        </li>
        <li v-if="run.paper_id">
          <span>默认用纸</span>
          <span class="meta">{{ run.paper_name ?? '纸#' + run.paper_id }}</span>
        </li>
        <li>
          <span>折边系数</span>
          <span class="meta">×{{ run.overlap }}</span>
        </li>
        <li>
          <span>丝带样式</span>
          <span class="meta">{{ wrapLabel(run.wrap_style) }}</span>
        </li>
        <li>
          <span>用纸面积</span>
          <span class="meta">{{ run.paper_m2 }} m²</span>
        </li>
        <li>
          <span>丝带长度</span>
          <span class="meta">{{ run.ribbon_m }} m</span>
        </li>
        <li v-if="run.note">
          <span>备注</span>
          <span class="meta">{{ run.note }}</span>
        </li>
        <li>
          <span>落库时间</span>
          <span class="meta">{{ fmt(run.created_at) }}</span>
        </li>
      </ul>

      <div v-if="run.recipe_id" class="result-board">
        <div class="row">
          <button :disabled="busy" @click="recompute">按钉版再干算</button>
          <template v-if="check">
            <span v-if="check.paperOk && check.ribbonOk" class="pill">互证一致</span>
            <span v-else class="pill warn">
              不一致：面积 {{ check.paper_m2 }} vs {{ run.paper_m2 }}，丝带 {{ check.ribbon_m }} vs {{ run.ribbon_m }}
            </span>
          </template>
        </div>
        <p v-if="check && check.paperOk && check.ribbonOk" class="meta">
          用钉住的 v{{ run.recipe_rev }} 重算：{{ check.paper_m2 }} m² / {{ check.ribbon_m }} m，与落库值相同。
        </p>
      </div>

      <div class="row" style="margin-top: 1.25rem">
        <router-link class="btn ghost" to="/history">返回用纸档</router-link>
      </div>
    </template>
  </div>
</template>
