import { CERTIFIER_LABELS, type Certifier } from '../data/types'
import { useSectionOpen } from '../filters/useSectionOpen'
import { EMPTY_FILTERS, isEmpty, type Filters, type MatchMode } from '../filters/types'
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

/** Count of products that would match if this option were also selected. */
export interface FacetCounts {
  certifiers: Record<string, number>
  allergens: Record<string, number>
  flags: Record<string, number>
}

/**
 * Collapsible, with state remembered in localStorage per section (see
 * useSectionOpen). A user who never touches "Brand" should get to close it
 * once and have it stay closed on their next visit.
 */
function Section({
  title,
  children,
  hint,
  defaultOpen = true,
  activeSummary,
}: {
  title: string
  children: React.ReactNode
  hint?: string
  defaultOpen?: boolean
  /** Short summary shown next to the title when the section is collapsed and has an active selection, e.g. "2 selected". */
  activeSummary?: string
}) {
  const [open, toggle] = useSectionOpen(title, defaultOpen)

  return (
    <div className="border-b border-line py-1 first:pt-0 last:border-0">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 py-2 text-left"
      >
        <span className="flex items-center gap-2">
          <h3 className="font-mono text-[0.72rem] uppercase tracking-[0.08em] text-ink-soft">{title}</h3>
          {!open && activeSummary && (
            <span className="rounded-full bg-accent-soft px-1.5 py-0.5 font-mono text-[0.64rem] text-accent">
              {activeSummary}
            </span>
          )}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className={`shrink-0 text-ink-soft transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
          aria-hidden
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="pb-3">
          {hint && <p className="mb-2 text-[0.72rem] leading-snug text-ink-soft/80">{hint}</p>}
          {children}
        </div>
      )}
    </div>
  )
}

function MatchModeToggle({ value, onChange }: { value: MatchMode; onChange: (m: MatchMode) => void }) {
  return (
    <div className="mb-2 inline-flex overflow-hidden rounded border border-line-strong" role="group">
      {(['all', 'any'] as MatchMode[]).map((m) => (
        <button
          key={m}
          type="button"
          aria-pressed={value === m}
          onClick={() => onChange(m)}
          className={`px-2 py-0.5 font-mono text-[0.68rem] uppercase tracking-wide transition-colors ${
            value === m ? 'bg-accent text-paper-raised' : 'bg-paper text-ink-soft hover:text-ink'
          }`}
        >
          Match {m}
        </button>
      ))}
    </div>
  )
}

function Checkbox({
  checked,
  onChange,
  label,
  count,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  count?: number
}) {
  // Zero-result options stay visible but inert: hiding them would make the
  // catalogue feel arbitrary, while letting them be clicked leads straight to
  // an empty grid.
  const disabled = count === 0 && !checked
  return (
    <label
      className={`flex items-center gap-2 py-1 text-[0.84rem] ${
        disabled ? 'cursor-not-allowed text-ink-soft/50' : 'text-ink'
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="h-3.5 w-3.5 accent-accent"
      />
      <span className="flex-1">{label}</span>
      {count != null && <span className="font-mono text-[0.72rem] tabular-nums text-ink-soft">{count}</span>}
    </label>
  )
}

/**
 * The filter controls only — no outer chrome. Rendered inside a sticky
 * sidebar on desktop and a drawer sheet on mobile (see FilterPanel), so this
 * component stays agnostic to which one it's in.
 */
export function FilterBar({
  filters,
  onChange,
  ingredientOptions,
  brandOptions,
  counts,
}: {
  filters: Filters
  onChange: (next: Filters) => void
  ingredientOptions: string[]
  brandOptions: string[]
  counts: FacetCounts
}) {
  function patch(partial: Partial<Filters>) {
    onChange({ ...filters, ...partial })
  }

  function toggleInList<T>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
  }

  return (
    <div>
      <div className="flex items-center justify-between pb-2">
        <span className="font-mono text-[0.72rem] uppercase tracking-[0.08em] text-ink-soft">Filters</span>
        {!isEmpty(filters) && (
          <button
            type="button"
            onClick={() => onChange({ ...EMPTY_FILTERS, sort: filters.sort })}
            className="font-mono text-[0.72rem] uppercase tracking-wide text-accent hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      <Section
        title="Has ingredient"
        activeSummary={filters.includeIngredients.length ? `${filters.includeIngredients.length}` : undefined}
      >
        <MatchModeToggle
          value={filters.ingredientMatchMode}
          onChange={(m) => patch({ ingredientMatchMode: m })}
        />
        <TagSearchInput
          options={ingredientOptions}
          selected={filters.includeIngredients}
          onChange={(v) => patch({ includeIngredients: v })}
          placeholder="e.g. stevia"
        />
      </Section>

      <Section
        title="Does not have ingredient"
        activeSummary={filters.excludeIngredients.length ? `${filters.excludeIngredients.length}` : undefined}
      >
        <TagSearchInput
          options={ingredientOptions}
          selected={filters.excludeIngredients}
          onChange={(v) => patch({ excludeIngredients: v })}
          placeholder="e.g. sucralose"
        />
      </Section>

      <Section
        title="Certification"
        activeSummary={filters.certifiers.length ? `${filters.certifiers.length}` : undefined}
        hint={
          filters.certMatchMode === 'all'
            ? 'Match all: products carrying every certification you select.'
            : 'Match any: products carrying at least one.'
        }
      >
        <MatchModeToggle value={filters.certMatchMode} onChange={(m) => patch({ certMatchMode: m })} />
        {CERTIFIERS.map((c) => (
          <Checkbox
            key={c}
            checked={filters.certifiers.includes(c)}
            onChange={() => patch({ certifiers: toggleInList(filters.certifiers, c) })}
            label={CERTIFIER_LABELS[c]}
            count={counts.certifiers[c] ?? 0}
          />
        ))}
        <div className="mt-1.5 border-t border-line pt-1.5">
          <Checkbox
            checked={filters.noCertOnly}
            onChange={(v) => patch({ noCertOnly: v })}
            label="No independent certification"
            count={counts.flags.noCert}
          />
        </div>
      </Section>

      <Section title="Brand" defaultOpen={false} activeSummary={filters.brands.length ? `${filters.brands.length}` : undefined}>
        <TagSearchInput
          options={brandOptions}
          selected={filters.brands}
          onChange={(v) => patch({ brands: v })}
          placeholder="Search brands"
        />
      </Section>

      <Section
        title="Exclude allergen"
        activeSummary={filters.excludeAllergens.length ? `${filters.excludeAllergens.length}` : undefined}
        hint="Uses declared allergens plus any detected in the ingredient list."
      >
        {ALLERGENS.map((a) => (
          <Checkbox
            key={a}
            checked={filters.excludeAllergens.includes(a)}
            onChange={() => patch({ excludeAllergens: toggleInList(filters.excludeAllergens, a) })}
            label={a}
            count={counts.allergens[a] ?? 0}
          />
        ))}
        {filters.excludeAllergens.length > 0 && (
          <div className="mt-1.5 border-t border-line pt-1.5">
            <Checkbox
              checked={filters.requireAllergenDeclaration}
              onChange={(v) => patch({ requireAllergenDeclaration: v })}
              label="Only labels that declare allergens"
            />
            <p className="mt-1 text-[0.72rem] leading-snug text-ink-soft/80">
              Many labels declare nothing at all. Absence of a statement isn't a
              statement of absence.
            </p>
          </div>
        )}
      </Section>

      <Section title="Flags">
        <Checkbox
          checked={filters.noArtificialSweetener}
          onChange={(v) => patch({ noArtificialSweetener: v })}
          label="No artificial sweetener"
          count={counts.flags.noArtificialSweetener}
        />
        <Checkbox
          checked={filters.noProprietaryBlend}
          onChange={(v) => patch({ noProprietaryBlend: v })}
          label="No proprietary blend"
          count={counts.flags.noProprietaryBlend}
        />
        <Checkbox
          checked={filters.onMarketOnly}
          onChange={(v) => patch({ onMarketOnly: v })}
          label="On market only"
          count={counts.flags.onMarketOnly}
        />
      </Section>

      <Section title="Min. protein by weight" defaultOpen={false} activeSummary={filters.minProteinPct != null ? `≥${filters.minProteinPct}%` : undefined}>
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            max={100}
            value={filters.minProteinPct ?? ''}
            onChange={(e) => patch({ minProteinPct: e.target.value === '' ? null : Number(e.target.value) })}
            placeholder="0"
            aria-label="Minimum protein percentage by weight"
            className="w-20 rounded border border-line-strong bg-paper px-2 py-1 text-[0.84rem] text-ink focus:border-accent focus:outline-none"
          />
          <span className="text-[0.82rem] text-ink-soft">%</span>
        </div>
      </Section>
    </div>
  )
}
