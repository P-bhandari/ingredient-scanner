import { CERTIFIER_LABELS, type Certifier } from '../data/types'
import { EMPTY_FILTERS, isEmpty, type Filters } from '../filters/types'
import { TagSearchInput } from './TagSearchInput'

const CERTIFIERS: Certifier[] = [
  'nsf_certified_for_sport',
  'nsf_contents_certified',
  'informed_sport',
  'informed_choice',
  'usp_verified',
  'bscg',
]

const ALLERGENS = ['milk', 'soy', 'egg', 'wheat', 'peanut', 'tree nut', 'fish', 'shellfish', 'sesame', 'gluten']

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-line py-4 first:pt-0 last:border-0">
      <h3 className="mb-2.5 font-mono text-[0.72rem] uppercase tracking-[0.08em] text-ink-soft">{title}</h3>
      {children}
    </div>
  )
}

function Checkbox({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex items-center gap-2 py-1 text-[0.84rem] text-ink">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 accent-accent"
      />
      {label}
    </label>
  )
}

export function FilterBar({
  filters,
  onChange,
  ingredientOptions,
  brandOptions,
}: {
  filters: Filters
  onChange: (next: Filters) => void
  ingredientOptions: string[]
  brandOptions: string[]
}) {
  function patch(partial: Partial<Filters>) {
    onChange({ ...filters, ...partial })
  }

  function toggleInList<T>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
  }

  return (
    <aside className="w-full shrink-0 sm:w-64">
      <div className="flex items-center justify-between pb-3">
        <span className="font-mono text-[0.72rem] uppercase tracking-[0.08em] text-ink-soft">Filters</span>
        {!isEmpty(filters) && (
          <button
            type="button"
            onClick={() => onChange(EMPTY_FILTERS)}
            className="font-mono text-[0.72rem] uppercase tracking-wide text-accent hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      <Section title="Has ingredient">
        <TagSearchInput
          options={ingredientOptions}
          selected={filters.includeIngredients}
          onChange={(v) => patch({ includeIngredients: v })}
          placeholder="e.g. stevia"
        />
      </Section>

      <Section title="Does not have ingredient">
        <TagSearchInput
          options={ingredientOptions}
          selected={filters.excludeIngredients}
          onChange={(v) => patch({ excludeIngredients: v })}
          placeholder="e.g. sucralose"
        />
      </Section>

      <Section title="Certification">
        {CERTIFIERS.map((c) => (
          <Checkbox
            key={c}
            checked={filters.certifiers.includes(c)}
            onChange={() => patch({ certifiers: toggleInList(filters.certifiers, c) })}
            label={CERTIFIER_LABELS[c]}
          />
        ))}
        <div className="mt-1.5 border-t border-line pt-1.5">
          <Checkbox
            checked={filters.noCertOnly}
            onChange={(v) => patch({ noCertOnly: v })}
            label="No independent certification"
          />
        </div>
      </Section>

      <Section title="Brand">
        <TagSearchInput
          options={brandOptions}
          selected={filters.brands}
          onChange={(v) => patch({ brands: v })}
          placeholder="Search brands"
        />
      </Section>

      <Section title="Exclude allergen">
        {ALLERGENS.map((a) => (
          <Checkbox
            key={a}
            checked={filters.excludeAllergens.includes(a)}
            onChange={() => patch({ excludeAllergens: toggleInList(filters.excludeAllergens, a) })}
            label={a}
          />
        ))}
      </Section>

      <Section title="Flags">
        <Checkbox
          checked={filters.noArtificialSweetener}
          onChange={(v) => patch({ noArtificialSweetener: v })}
          label="No artificial sweetener"
        />
        <Checkbox
          checked={filters.noProprietaryBlend}
          onChange={(v) => patch({ noProprietaryBlend: v })}
          label="No proprietary blend"
        />
        <Checkbox checked={filters.onMarketOnly} onChange={(v) => patch({ onMarketOnly: v })} label="On market only" />
      </Section>

      <Section title="Min. protein by weight">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={100}
            value={filters.minProteinPct ?? ''}
            onChange={(e) => patch({ minProteinPct: e.target.value === '' ? null : Number(e.target.value) })}
            placeholder="0"
            className="w-20 rounded border border-line-strong bg-paper px-2 py-1 text-[0.84rem] text-ink focus:border-accent focus:outline-none"
          />
          <span className="text-[0.82rem] text-ink-soft">%</span>
        </div>
      </Section>
    </aside>
  )
}
