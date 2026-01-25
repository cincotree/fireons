"use client";

import * as React from "react";
import { cn } from "@/utils/cn"; // Assuming utility exists, otherwise I'll use simple class concat or fallback

// Simple context for Tabs
const TabsContext = React.createContext<{
    value: string;
    onValueChange: (value: string) => void;
} | null>(null);

function Tabs({
    defaultValue,
    value,
    onValueChange,
    children,
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement> & {
    defaultValue?: string;
    value?: string;
    onValueChange?: (value: string) => void;
}) {
    const [stateValue, setStateValue] = React.useState(defaultValue || "");

    const handleValueChange = React.useCallback(
        (val: string) => {
            if (onValueChange) {
                onValueChange(val);
            } else {
                setStateValue(val);
            }
        },
        [onValueChange]
    );

    const activeValue = value !== undefined ? value : stateValue;

    return (
        <TabsContext.Provider value={{ value: activeValue, onValueChange: handleValueChange }}>
            <div className={cn("", className)} {...props}>
                {children}
            </div>
        </TabsContext.Provider>
    );
}

const TabsList = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
    <div
        ref={ref}
        className={cn(
            "inline-flex h-10 items-center justify-center rounded-md bg-slate-100 p-1 text-slate-500",
            className
        )}
        {...props}
    />
));
TabsList.displayName = "TabsList";

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    value: string;
}

const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
    ({ className, value, ...props }, ref) => {
        const context = React.useContext(TabsContext);
        if (!context) throw new Error("TabsTrigger must be used within Tabs");

        const isActive = context.value === value;

        return (
            <button
                ref={ref}
                type="button"
                onClick={() => context.onValueChange(value)}
                className={cn(
                    "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
                    isActive
                        ? "bg-white text-slate-950 shadow-sm"
                        : "hover:bg-slate-200 hover:text-slate-900",
                    className
                )}
                {...props}
            />
        );
    }
);
TabsTrigger.displayName = "TabsTrigger";

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
    value: string;
}

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
    ({ className, value, children, ...props }, ref) => {
        const context = React.useContext(TabsContext);
        if (!context) throw new Error("TabsContent must be used within Tabs");

        if (context.value !== value) return null;

        return (
            <div
                ref={ref}
                className={cn(
                    "mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2",
                    className
                )}
                {...props}
            >
                {children}
            </div>
        );
    }
);
TabsContent.displayName = "TabsContent";

export { Tabs, TabsList, TabsTrigger, TabsContent };
