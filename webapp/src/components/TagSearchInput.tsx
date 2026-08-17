import { useId, useMemo, useState } from 'react'

interface TagSearchInputProps {
  options: string[]
  selected: string[]
  onChange: (next: string[]) => void
  placeholder: string
}

/** Free-text add with datalist suggestions, plus removable chips for what's selected. */
export function TagSearchInput({ options, selected, onChange, placeholder }: TagSearchInputProps) {
  const [text, setText] = useState('')
  const listId = useId()

  /**
   * Filter by what's typed BEFORE capping. Capping first meant the datalist
   * held only the alphabetically-first 400 of 1,336 ingredients, so Sucralose,
   * Xanthan Gum and Stevia never appeared as suggestions — including for the
   * field whose own placeholder reads "e.g. sucralose".
   */
  const suggestions = useMemo(() => {
    const q = text.trim().toLowerCase()
    const pool = q ? options.filter((o) => o.toLowerCase().includes(q)) : options
    return pool.slice(0, 100)
  }, [options, text])

  const exactish = text.trim()
    ? options.some((o) => o.toLowerCase().includes(text.trim().toLowerCase()))
    : true

  function add(value: string) {
    const trimmed = value.trim()
    if (!trimmed) return
    if (!selected.some((s) => s.toLowerCase() === trimmed.toLowerCase())) {
      onChange([...selected, trimmed])
    }
    setText('')
  }

  return (
    <div>
      <input
        type="text"
        list={listId}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            add(text)
          }
        }}
        placeholder={placeholder}
        className="w-full rounded border border-line-strong bg-paper px-2.5 py-1.5 text-[0.82rem] text-ink placeholder:text-ink-soft focus:border-accent focus:outline-none"
      />
      <datalist id={listId}>
        {suggestions.map((opt) => (
          <option key={opt} value={opt} />
        ))}
      </datalist>

      {!exactish && (
        <p className="mt-1 text-[0.72rem] text-claim">
          No ingredient matches “{text.trim()}” — check the spelling.
        </p>
      )}

      {selected.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {selected.map((value) => (
            <li key={value}>
              <button
                type="button"
                onClick={() => onChange(selected.filter((s) => s !== value))}
                className="inline-flex items-center gap-1 rounded-[3px] border border-line-strong bg-code-bg px-2 py-1 font-mono text-[0.7rem] text-ink-soft hover:border-accent hover:text-accent"
              >
                {value}
                <span aria-hidden>×</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
