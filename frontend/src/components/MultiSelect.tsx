"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Search } from "lucide-react";

interface MultiSelectProps {
  label: string;
  noun: string;
  allLabel: string;
  options: string[];
  value: string[];
  onChange: (value: string[]) => void;
  triggerClassName?: string;
}

function summarize(value: string[], allLabel: string): string {
  if (value.length === 0) return allLabel;
  if (value.length === 1) return value[0];
  return `${value[0]} +${value.length - 1}`;
}

export function MultiSelect({ label, noun, allLabel, options, value, onChange, triggerClassName = "" }: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const listId = useId();

  const visibleOptions = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return options;
    const matches = options.filter((option) => option.toLowerCase().includes(needle));
    return [
      ...matches.filter((option) => option.toLowerCase().startsWith(needle)),
      ...matches.filter((option) => !option.toLowerCase().startsWith(needle)),
    ];
  }, [options, query]);

  useEffect(() => {
    if (!open) return;
    searchInput.current?.focus();
    const onPointerDown = (event: MouseEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    document.getElementById(`${listId}-option-${activeIndex}`)?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open, listId]);

  const close = (returnFocus: boolean) => {
    setOpen(false);
    setQuery("");
    if (returnFocus) trigger.current?.focus();
  };

  const toggle = (option: string) => {
    onChange(value.includes(option) ? value.filter((item) => item !== option) : [...value, option]);
  };

  const onSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => Math.min(index + 1, Math.max(visibleOptions.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const option = visibleOptions[activeIndex];
      if (option) toggle(option);
    } else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "Tab") {
      close(false);
    }
  };

  return (
    <div ref={root} className="relative">
      <button
        ref={trigger}
        type="button"
        role="combobox"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        onClick={() => (open ? close(false) : setOpen(true))}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && !open) {
            event.preventDefault();
            setOpen(true);
          }
        }}
        className={`flex h-[52px] w-full items-center justify-between pl-4 pr-4 text-left text-[15px] ${triggerClassName}`}
      >
        <span className={`truncate ${value.length === 0 ? "text-[#2A3A35]" : "font-medium text-[#12211D]"}`}>
          {summarize(value, allLabel)}
        </span>
        <ChevronDown
          className={`ml-3 h-5 w-5 shrink-0 text-[#66766F] transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div className="absolute left-0 right-0 z-30 mt-2 overflow-hidden rounded-xl border border-[#D3DFDA] bg-white shadow-[0_16px_40px_-12px_rgba(18,33,29,0.35)]">
          <div className="relative border-b border-[#E6ECE9] p-2">
            <Search
              className="pointer-events-none absolute left-5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#66766F]"
              aria-hidden="true"
            />
            <input
              ref={searchInput}
              type="text"
              aria-label={`Search ${noun}`}
              aria-controls={listId}
              aria-activedescendant={visibleOptions.length > 0 ? `${listId}-option-${activeIndex}` : undefined}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={onSearchKeyDown}
              placeholder={`Search ${noun}...`}
              autoComplete="off"
              className="h-10 w-full rounded-lg bg-[#F6F8F7] pl-9 pr-3 text-sm text-[#12211D] placeholder:text-[#7D8C86] focus:outline-none focus:ring-2 focus:ring-[#0E6B57]"
            />
          </div>

          <ul
            id={listId}
            role="listbox"
            aria-label={label}
            aria-multiselectable="true"
            className="max-h-64 overflow-y-auto py-1"
          >
            {visibleOptions.map((option, index) => {
              const selected = value.includes(option);
              return (
                <li
                  key={option}
                  id={`${listId}-option-${index}`}
                  role="option"
                  aria-selected={selected}
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => toggle(option)}
                  className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm text-[#12211D] ${
                    index === activeIndex ? "bg-[#F0F6F3]" : ""
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded border ${
                      selected ? "border-[#0E6B57] bg-[#0E6B57] text-white" : "border-[#B9C8C2] bg-white"
                    }`}
                  >
                    {selected && <Check className="h-3 w-3" strokeWidth={3} />}
                  </span>
                  <span className={selected ? "font-medium" : ""}>{option}</span>
                </li>
              );
            })}
            {visibleOptions.length === 0 && (
              <li className="px-4 py-6 text-center text-sm text-[#66766F]" role="presentation">
                No matching {noun}.
              </li>
            )}
          </ul>

          {value.length > 0 && (
            <div className="flex items-center justify-between border-t border-[#E6ECE9] px-4 py-2.5 text-sm">
              <span className="text-[#66766F]">{value.length} selected</span>
              <button
                type="button"
                onClick={() => onChange([])}
                className="rounded font-medium text-[#0E6B57] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
              >
                Clear selection
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
