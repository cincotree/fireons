"use client";

import * as React from "react";
import { cn } from "@/utils/cn";

interface SliderProps extends React.InputHTMLAttributes<HTMLInputElement> {
    min: number;
    max: number;
    step?: number;
    value: number;
    onValueChange: (value: number) => void;
    className?: string;
}

export function Slider({
    min,
    max,
    step = 1,
    value,
    onValueChange,
    className,
    ...props
}: SliderProps) {
    const percentage = ((value - min) / (max - min)) * 100;

    return (
        <div className={cn("relative w-full flex items-center h-6 select-none touch-none", className)}>
            {/* Track Background */}
            <div className="absolute w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                {/* Fill */}
                <div
                    className="h-full bg-slate-900"
                    style={{ width: `${percentage}%` }}
                />
            </div>

            {/* Thumb (Invisible Input) */}
            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => onValueChange(parseFloat(e.target.value))}
                className="absolute w-full h-full opacity-0 cursor-pointer z-10"
                {...props}
            />

            {/* Visible Thumb (Purely decorative/positional based on percentage) */}
            <div
                className="absolute h-5 w-5 bg-white border-2 border-slate-900 rounded-full shadow-md pointer-events-none transition-transform"
                style={{ left: `calc(${percentage}% - 10px)` }}
            />
        </div>
    );
}
