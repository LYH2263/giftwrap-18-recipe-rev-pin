<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import BoxUnfold from '../components/BoxUnfold.vue'
import { wrapLabel } from '../labels'

const boxes = ref([])
const recipes = ref([])
const bid = ref(1)
const recipeId = ref(null)
const out = ref(null)
const err = ref('')
const busy = ref(false)

onMounted(async () => {
  try {
    const [bs, rs] = await Promise.all([getJSON('/api/boxes'), getJSON('/api/recipes/active')])
    boxes.value = bs.items.filter((b) => b.data_quality === 'clean')
    recipes.value = rs.items
    if (boxes.value.length) bid.value = boxes.value[0].id
  } catch (e) {
    err.value = String(e.message || e)
  }
})

async function go(save) {
  err.value = ''
  busy.value = true
  try {
    if (save) {
      out.value = await postJSON('/api/estimate', {
        box_id: bid.value,
        save: true,
        recipe_id: recipeId.value ?? undefined,
      })
    } else {
      const q = new URLSearchParams({ box_id: bid.value })
      if (recipeId.value) q.set('recipe_id', recipeId.value)
      out.value = await getJSON(`/api/estimate?${q.toString()}`)
    }
  } catch (e) {
    err.value = String(e.message || e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1>算纸</h1>
    <p class="lede">先试算看面积与展开，确认后再写入用纸档。选用配方后，折边系数、丝带样式与默认用纸取配方当前版。</p>
    <div class="row">
      <select v-model.number="bid">
        <option v-for="b in boxes" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>
      <select v-model.number="recipeId">
        <option :value="null">不使用配方</option>
        <option v-for="r in recipes" :key="r.id" :value="r.id">
          {{ r.name }} v{{ r.current_rev }} · {{ r.paper_name ?? '默认用纸' }}
        </option>
      </select>
      <button :disabled="busy" @click="go(false)">试算</button>
      <button class="ribbon" :disabled="busy" @click="go(true)">写入用纸档</button>
    </div>
    <p v-if="err" class="bad">{{ err }}</p>
    <div v-if="out" class="result-board">
      <div class="figure">{{ out.paper_m2 }}<span>m²</span></div>
      <p class="stat-line" v-if="out.recipe">
        <span class="pill">{{ out.recipe.name }} v{{ out.recipe.rev }}</span>
        默认用纸 {{ out.paper?.name ?? '—' }}
      </p>
      <p class="stat-line" v-if="out.ribbon">
        {{ wrapLabel(out.ribbon.wrap_style) }}约 {{ out.ribbon.ribbon_m ?? out.ribbon }} m
      </p>
      <BoxUnfold
        :l="out.box.length"
        :w="out.box.width"
        :h="out.box.height"
        :paper-m2="out.paper_m2"
      />
    </div>
  </div>
</template>
