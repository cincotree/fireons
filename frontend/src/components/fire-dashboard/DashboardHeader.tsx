"use client";

import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import { format } from "date-fns";

export function DashboardHeader() {
    const currentDate = format(new Date(), "MMMM d, yyyy");

    return (
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-slate-900">FIRE Dashboard</h1>
                <p className="text-slate-500">
                    Track your journey to Financial Independence.
                </p>
            </div>

            <div className="flex items-center gap-2">
                <div className="hidden md:block text-sm text-slate-500 mr-2">
                    Data as of {currentDate}
                </div>

                <Select defaultValue="USD">
                    <SelectTrigger className="w-[100px]">
                        <SelectValue placeholder="Currency" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="USD">USD ($)</SelectItem>
                        <SelectItem value="EUR">EUR (€)</SelectItem>
                        <SelectItem value="GBP">GBP (£)</SelectItem>
                        <SelectItem value="INR">INR (₹)</SelectItem>
                    </SelectContent>
                </Select>

                <Button variant="default" className="bg-slate-900 text-white hover:bg-slate-800">
                    + Add Value
                </Button>
            </div>
        </div>
    );
}
