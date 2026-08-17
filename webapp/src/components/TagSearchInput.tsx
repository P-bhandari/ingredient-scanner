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

  const suggestions = useMemo(() => options.slice(0, 400), [options])

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
