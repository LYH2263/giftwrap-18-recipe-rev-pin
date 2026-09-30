export const WRAP_LABEL = { cross: '十字', band: '单条' }

export function wrapLabel(v) {
  return WRAP_LABEL[v] || v || '—'
}
