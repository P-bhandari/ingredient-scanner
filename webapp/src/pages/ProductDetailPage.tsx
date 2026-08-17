import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FavoriteButton } from '../components/FavoriteButton'
import { ProductPhoto } from '../components/ProductPhoto'
import { TrustDetail } from '../components/TrustBadge'
import { allergenStatus, allergensFor, proteinPctByWeight } from '../data/derived'
import { CATEGORY_LABELS, INGREDIENT_CATEGORY_LABELS, type Ingredient } from '../data/types'
import { useDataset } from '../data/useDataset'
import { useDocumentTitle } from '../useDocumentTitle'

const MACRO_ROWS: Array<{ key: keyof import('../data/types').Macros; label: string; unit: string }> = [
  { key: 'calories', label: 'Calories', unit: '' },
  { key: 'protein_g', label: 'Protein', unit: 'g' },
  { key: 'total_fat_g', label: 'Total fat', unit: 'g' },
  { key: 'saturated_fat_g', label: 'Saturated fat', unit: 'g' },
  { key: 'total_carbs_g', label: 'Total carbs', unit: 'g' },
  { key: 'sugar_g', label: 'Sugar', unit: 'g' },
  { key: 'added_sugar_g', label: 'Added sugar', unit: 'g' },
  { key: 'fibre_g', label: 'Fibre', unit: 'g' },
  { key: 'cholesterol_mg', label: 'Cholesterol', unit: 'mg' },
  { key: 'sodium_mg', label: 'Sodium', unit: 'mg' },
  { key: 'calcium_mg', label: 'Calcium', unit: 'mg' },
  { key: 'potassium_mg', label: 'Potassium', unit: 'mg' },
]

function IngredientRow({ ingredient }: { ingredient: Ingredient }) {
  return (
    <li
      className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 border-b border-line py-2 last:border-0"
      style={{ paddingLeft: `${ingredient.depth * 16}px` }}
    >
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="text-[0.9rem] text-ink">{ingredient.name}</span>
        {ingredient.is_proprietary_blend && (
          <span className="font-mono text-[0.62rem] uppercase tracking-wide text-claim">proprietary blend</span>
        )}
        <span className="flex flex-wrap gap-1">
          {ingredient.categories
            .filter((c) => c !== 'macro')
            .map((c) => (
              <span
                key={c}
                className="rounded-[3px] bg-code-bg px-1.5 py-0.5 font-mono text-[0.62rem] uppercase tracking-wide text-ink-soft"
              >
                {INGREDIENT_CATEGORY_LABELS[c]}
              </span>
            ))}
        </span>
      </div>
      {ingredient.quantity != null && (
        <span className="font-mono text-[0.78rem] tabular-nums text-ink-soft">
          {ingredient.quantity} {ingredient.unit}
        </span>
      )}
    </li>
  )
}

export function ProductDetailPage() {
  const { id } = useParams()
  const { dataset } = useDataset()
  const [showStub, setShowStub] = useState(false)

  const product = dataset.products.find((p) => p.dsld_id === Number(id))

  // Called before any early return — hooks can't run conditionally.
  useDocumentTitle(product ? `${product.name} — ${product.brand}` : 'Product not found')

  if (!product) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16">
        <p className="text-ink-soft">Product not found.</p>
        <Link to="/" className="text-accent hover:underline">
          ‹ Back to browse
        </Link>
      </div>
    )
  }

  const pct = proteinPctByWeight(product)
  const totalIngredients = product.ingredients.length + product.other_ingredients.length
  const allergens = allergensFor(product)

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <Link to="/" className="font-mono text-[0.76rem] uppercase tracking-wide text-ink-soft hover:text-accent">
        ‹ Back to browse
      </Link>

      <div className="mt-4 flex flex-col gap-6 sm:flex-row">
        <ProductPhoto brand={product.brand} className="h-40 w-40 shrink-0 rounded-md text-4xl" />

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="font-mono text-[0.72rem] uppercase tracking-wide text-ink-soft">
                {product.brand} · {CATEGORY_LABELS[product.category]}
                {product.off_market && ' · Off market'}
              </span>
              <h1 className="mt-1 font-serif text-2xl font-semibold leading-tight text-ink">{product.name}</h1>
            </div>
            <FavoriteButton dsldId={product.dsld_id} />
          </div>

          <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 font-mono text-[0.8rem] text-ink-soft">
            {product.serving.quantity != null && (
              <div>
                <dt className="inline text-ink-soft">Serving </dt>
                <dd className="inline text-ink">
                  {product.serving.quantity} {product.serving.unit}
                  {product.serving.note ? ` (${product.serving.note})` : ''}
                </dd>
              </div>
            )}
            {pct != null ? (
              <div>
                <dt className="inline text-ink-soft">Protein by weight </dt>
                <dd className="inline text-ink">
                  {pct}%
                  {product.protein_pct_basis === 'max_serving' && (
                    <span
                      className="ml-1 text-ink-soft"
                      title="This label declares a serving range; the figure uses the upper bound, which is the basis its nutrition panel matches."
                    >
                      (max serving)
                    </span>
                  )}
                </dd>
              </div>
            ) : (
              <div>
                <dt className="inline text-ink-soft">Protein by weight </dt>
                <dd
                  className="inline text-ink-soft"
                  title="The serving isn't declared by weight, or the label's own figures are inconsistent."
                >
                  not comparable
                </dd>
              </div>
            )}
            {product.manufacturer && (
              <div>
                <dt className="inline text-ink-soft">Manufacturer </dt>
                <dd className="inline text-ink">{product.manufacturer}</dd>
              </div>
            )}
          </dl>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setShowStub(true)}
              className="rounded bg-accent px-4 py-2 font-mono text-[0.78rem] uppercase tracking-wide text-paper-raised hover:opacity-90"
            >
              Get this product
            </button>
            {product.source_url && (
              <a
                href={product.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[0.76rem] uppercase tracking-wide text-ink-soft hover:text-accent"
              >
                View DSLD source ↗
              </a>
            )}
          </div>
          {showStub && (
            <p className="mt-2 text-[0.82rem] text-ink-soft">
              Purchase link not available yet — retailer matching is a follow-up data project (see PRD §9).
            </p>
          )}
        </div>
      </div>

      <section className="mt-10">
        <h2 className="mb-3 font-serif text-lg font-semibold text-ink">Trust &amp; certification</h2>
        <TrustDetail trust={product.trust} />
      </section>

      <section className="mt-10">
        <h2 className="mb-3 font-serif text-lg font-semibold text-ink">Nutrition (per serving)</h2>
        <div className="overflow-x-auto rounded border border-line">
          <table className="w-full text-[0.86rem]">
            <tbody>
              {MACRO_ROWS.filter((row) => product.macros[row.key] != null).map((row) => (
                <tr key={row.key} className="border-b border-line last:border-0">
                  <td className="px-3 py-1.5 text-ink-soft">{row.label}</td>
                  <td className="px-3 py-1.5 text-right font-mono tabular-nums text-ink">
                    {product.macros[row.key]}
                    {row.unit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {product.nutrient_panel.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-3 font-serif text-lg font-semibold text-ink">Additional nutrients</h2>
          <p className="mb-3 text-[0.82rem] text-ink-soft">
            Declared nutrient content from the label's Nutrition Facts panel — not separately-added ingredients.
          </p>
          <div className="overflow-x-auto rounded border border-line">
            <table className="w-full text-[0.86rem]">
              <tbody>
                {product.nutrient_panel.map((n, i) => (
                  <tr key={i} className="border-b border-line last:border-0">
                    <td className="px-3 py-1.5 text-ink-soft">{n.name}</td>
                    <td className="px-3 py-1.5 text-right font-mono tabular-nums text-ink">
                      {n.quantity != null ? `${n.quantity} ${n.unit ?? ''}` : n.percent_dv != null ? `${n.percent_dv}% DV` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/*
        DSLD files a product's composition under `ingredients`, under
        `otheringredients`, or splits it across both — 43% of records leave
        the first list empty. Rendering a bare "Ingredients (0)" above the
        real contents read as though we had no data, so the two are shown as
        one list unless both are populated.
      */}
      {totalIngredients > 0 ? (
        <section className="mt-10">
          <h2 className="mb-3 font-serif text-lg font-semibold text-ink">
            Ingredients <span className="text-ink-soft">({totalIngredients})</span>
          </h2>
          <ul>
            {product.ingredients.map((ing, i) => (
              <IngredientRow key={`i${i}`} ingredient={ing} />
            ))}
            {product.other_ingredients.length > 0 && product.ingredients.length > 0 && (
              <li className="pt-3 font-mono text-[0.7rem] uppercase tracking-wide text-ink-soft">
                Other ingredients
              </li>
            )}
            {product.other_ingredients.map((ing, i) => (
              <IngredientRow key={`o${i}`} ingredient={ing} />
            ))}
          </ul>
        </section>
      ) : (
        <section className="mt-10">
          <h2 className="mb-3 font-serif text-lg font-semibold text-ink">Ingredients</h2>
          <p className="text-[0.88rem] text-ink-soft">
            No ingredient list is recorded for this label in the source database.
          </p>
        </section>
      )}

      <section className="mt-10">
        <h2 className="mb-3 font-serif text-lg font-semibold text-ink">Allergens</h2>
        {allergens.length > 0 ? (
          <ul className="flex flex-wrap gap-2">
            {allergens.map((a) => {
              const status = allergenStatus(product, a)
              return (
                <li
                  key={a}
                  className="rounded-[3px] border border-claim/30 bg-claim-bg px-2.5 py-1 text-[0.82rem] text-claim"
                >
                  {a}
                  <span className="ml-1.5 font-mono text-[0.68rem] uppercase tracking-wide opacity-80">
                    {status === 'declared' ? 'declared' : 'inferred'}
                  </span>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="text-[0.88rem] text-ink-soft">No allergens declared or detected.</p>
        )}

        {/*
          The distinction that makes this safe: silence in the source data is
          not a claim of absence, and must never be presented as one.
        */}
        {product.allergen_declaration_missing && (
          <p className="mt-3 border-l-2 border-claim bg-claim-bg px-3 py-2 text-[0.84rem] text-claim">
            This label carries no allergen statement.{' '}
            {product.allergens_detected.length > 0
              ? 'The allergens above were inferred from the product name and ingredients.'
              : 'Nothing was detected in its name or ingredients either — but absence of a statement is not a guarantee.'}{' '}
            Check the physical packaging before relying on this.
          </p>
        )}
      </section>
    </div>
  )
}
