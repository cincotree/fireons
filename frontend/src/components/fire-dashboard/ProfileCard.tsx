"use client";

import { User, Users, Calendar, Flag } from "lucide-react";

export function ProfileCard() {
    return (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-none relative overflow-hidden h-full hover:border-slate-300 transition-colors">
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h3 className="text-lg font-bold text-slate-900">Personal Profile</h3>
                    <p className="text-sm text-slate-500">FIRE Planning Parameters</p>
                </div>
                <div className="h-10 w-10 bg-indigo-50 rounded-full flex items-center justify-center text-indigo-600">
                    <User className="w-5 h-5" />
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-slate-500 text-xs uppercase tracking-wide font-semibold">
                        <Calendar className="w-3 h-3" /> Age
                    </div>
                    <p className="text-xl font-bold text-slate-800">32 <span className="text-sm font-normal text-slate-400">/ 45</span></p>
                </div>

                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-slate-500 text-xs uppercase tracking-wide font-semibold">
                        <Users className="w-3 h-3" /> Dependents
                    </div>
                    <p className="text-xl font-bold text-slate-800">2 <span className="text-sm font-normal text-slate-400">Partners</span></p>
                </div>

                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-slate-500 text-xs uppercase tracking-wide font-semibold">
                        <Flag className="w-3 h-3" /> Target
                    </div>
                    <p className="text-xl font-bold text-emerald-600">$1.5M</p>
                </div>

                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-slate-500 text-xs uppercase tracking-wide font-semibold">
                        Savings Rate
                    </div>
                    <p className="text-xl font-bold text-blue-600">35%</p>
                </div>
            </div>
        </div>
    );
}
