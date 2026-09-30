import { createRouter, createWebHistory } from 'vue-router'
import Overview from './pages/Overview.vue'
import Boxes from './pages/Boxes.vue'
import BoxDetail from './pages/BoxDetail.vue'
import Papers from './pages/Papers.vue'
import Recipes from './pages/Recipes.vue'
import RecipeEdit from './pages/RecipeEdit.vue'
import Bench from './pages/Bench.vue'
import Ribbon from './pages/Ribbon.vue'
import Overlap from './pages/Overlap.vue'
import History from './pages/History.vue'
import HistoryDetail from './pages/HistoryDetail.vue'
import Settings from './pages/Settings.vue'
export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Overview },
    { path: '/boxes', component: Boxes },
    { path: '/boxes/:id', component: BoxDetail, props: true },
    { path: '/papers', component: Papers },
    { path: '/recipes', component: Recipes },
    { path: '/recipes/:id', component: RecipeEdit, props: true },
    { path: '/bench', component: Bench },
    { path: '/ribbon', component: Ribbon },
    { path: '/overlap', component: Overlap },
    { path: '/history', component: History },
    { path: '/history/:id', component: HistoryDetail, props: true },
    { path: '/settings', component: Settings },
  ],
})
