/* ============================================================
 * Category metadata (color, accent) used by the analytics page.
 * The label and example_claim also live in the backend's
 * /meta/categories endpoint, but those go through the data
 * layer (CategoryMeta). Colors are a presentation concern and
 * therefore live in the frontend.
 * ============================================================ */

export interface CategoryMetaFull {
  value: string
  color: string
}

const CATEGORIES: CategoryMetaFull[] = [
  { value: 'route_deviation', color: '#F0246E' },
  { value: 'no_show', color: '#1F64CC' },
  { value: 'fare_dispute', color: '#A855F7' },
  { value: 'property_damage', color: '#C2510A' },
  { value: 'safety_incident', color: '#B91C1C' },
]

const BY_VALUE = new Map(CATEGORIES.map((c) => [c.value, c] as const))

export function getCategoryMeta(value: string): CategoryMetaFull {
  return BY_VALUE.get(value) ?? { value, color: '#9398A3' }
}
