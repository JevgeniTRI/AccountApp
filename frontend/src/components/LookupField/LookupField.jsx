import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, LoaderCircle } from 'lucide-react'
import './LookupField.css'

export default function LookupField({
  label,
  placeholder,
  textValue,
  selectedOption,
  onTextChange,
  onSelect,
  fetchOptions,
  disabled = false,
  helperText,
}) {
  const fieldId = useId()
  const rootRef = useRef(null)
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [options, setOptions] = useState([])

  useEffect(() => {
    if (!isOpen || disabled) {
      return undefined
    }

    let cancelled = false
    const timerId = window.setTimeout(async () => {
      setIsLoading(true)
      setLoadError('')

      try {
        const items = await fetchOptions(textValue.trim())
        if (!cancelled) {
          setOptions(items)
        }
      } catch {
        if (!cancelled) {
          setLoadError('Не удалось загрузить список')
          setOptions([])
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }, 180)

    return () => {
      cancelled = true
      window.clearTimeout(timerId)
    }
  }, [disabled, fetchOptions, isOpen, textValue])

  useEffect(() => {
    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) {
        setIsOpen(false)
      }
    }

    window.addEventListener('pointerdown', handlePointerDown)
    return () => window.removeEventListener('pointerdown', handlePointerDown)
  }, [])

  const hasExactMatch = useMemo(() => {
    const normalized = textValue.trim().toLowerCase()
    if (!normalized) {
      return false
    }
    return options.some((option) => option.label.toLowerCase() === normalized)
  }, [options, textValue])

  function handleInputChange(event) {
    const nextValue = event.target.value
    if (selectedOption && nextValue !== selectedOption.label) {
      onSelect(null)
    }
    onTextChange(nextValue)
    setIsOpen(true)
  }

  function handleOptionPick(option) {
    onSelect(option)
    onTextChange(option.label)
    setIsOpen(false)
  }

  return (
    <div className={`lookup-field ${disabled ? 'is-disabled' : ''}`} ref={rootRef}>
      {label ? (
        <label className="lookup-field__label" htmlFor={fieldId}>
          {label}
        </label>
      ) : null}

      <div className={`lookup-field__control ${isOpen ? 'is-open' : ''}`}>
        <input
          id={fieldId}
          className="lookup-field__input"
          type="text"
          value={textValue}
          onChange={handleInputChange}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
        />
        <button
          type="button"
          className="lookup-field__toggle"
          onClick={() => setIsOpen((current) => !current)}
          disabled={disabled}
          aria-label={isOpen ? 'Скрыть варианты' : 'Показать варианты'}
        >
          <ChevronDown size={16} />
        </button>
      </div>

      {(helperText || (isOpen && !disabled)) && (
        <div className="lookup-field__meta">
          {helperText ? <span>{helperText}</span> : <span>&nbsp;</span>}
        </div>
      )}

      {isOpen && !disabled ? (
        <div className="lookup-field__panel" role="listbox">
          {isLoading ? (
            <div className="lookup-field__state">
              <LoaderCircle className="lookup-field__spinner" size={16} />
              Загрузка...
            </div>
          ) : null}

          {!isLoading && loadError ? <div className="lookup-field__state">{loadError}</div> : null}

          {!isLoading && !loadError && options.length === 0 ? (
            <div className="lookup-field__state">
              {textValue.trim()
                ? 'Совпадений нет. Можно сохранить это значение как новое.'
                : 'Начните вводить или выберите из списка.'}
            </div>
          ) : null}

          {!isLoading && !loadError && options.length > 0 ? (
            <div className="lookup-field__options">
              {options.map((option) => {
                const isSelected = selectedOption?.value === option.value
                return (
                  <button
                    key={String(option.value)}
                    type="button"
                    className={`lookup-field__option ${isSelected ? 'is-selected' : ''}`}
                    onMouseDown={(event) => {
                      event.preventDefault()
                      handleOptionPick(option)
                    }}
                  >
                    <span>{option.label}</span>
                    {isSelected ? <Check size={14} /> : null}
                  </button>
                )
              })}
            </div>
          ) : null}

          {!isLoading && !loadError && !hasExactMatch && textValue.trim() ? (
            <div className="lookup-field__footer">Нового значения пока нет в справочнике.</div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
