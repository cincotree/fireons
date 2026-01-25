"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    LayoutDashboard,
    Wallet,
    TrendingUp,
} from "lucide-react";

import { DashboardHeader } from "@/components/fire-dashboard/DashboardHeader";
import { SummaryCards } from "@/components/fire-dashboard/SummaryCards";
import { NetWorthChart } from "@/components/fire-dashboard/NetWorthChart";
import { AssetAllocation } from "@/components/fire-dashboard/AssetAllocation";
import { AccountTree } from "@/components/fire-dashboard/AccountTree";
import { ProfileCard } from "@/components/fire-dashboard/ProfileCard";
import { AdvancedFireSimulator } from "@/components/fire-dashboard/AdvancedFireSimulator";
import { AIChatPanel } from "@/components/fire-dashboard/AIChatPanel";
import { AccountDetailPanel } from "@/components/fire-dashboard/AccountDetailPanel";

import {
    generateHistoricalNetWorth,
    mockAccounts,
    getAssetAllocation
} from "@/lib/fireUtils";

export default function FireDashboardClient() {
    const [historyData, setHistoryData] = useState<any[]>([]);
    const [accounts, setAccounts] = useState<any[]>([]);
    const [assetAllocation, setAssetAllocation] = useState<any[]>([]);
    const [selectedAccount, setSelectedAccount] = useState<any>(null);

    useEffect(() => {
        // Simulate data loading
        setHistoryData(generateHistoricalNetWorth(24)); // 2 years history
        setAccounts(mockAccounts);
        setAssetAllocation(getAssetAllocation(mockAccounts));
    }, []);

    // Calculate aggregates
    const totalNetWorth = accounts.reduce((acc, curr) => {
        return curr.type === 'Liability' ? acc - curr.balance : acc + curr.balance;
    }, 0);

    // Simple hardcoded target for the Summary Card for now (e.g. 1.5M)
    const fiTarget = 1500000;

    // Calculate monthly change (mocked based on last 2 history points)
    const lastMonth = historyData[historyData.length - 1]?.value || 0;
    const prevMonth = historyData[historyData.length - 2]?.value || lastMonth;
    const monthlyChange = prevMonth ? ((lastMonth - prevMonth) / prevMonth) * 100 : 0;

    return (
        <div className="min-h-screen bg-brand-50/50 font-sans">
            <div className="max-w-7xl mx-auto min-h-screen">
                <DashboardHeader />

                <div className="p-4 md:p-8">

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                        <div className="md:col-span-3">
                            <SummaryCards
                                netWorth={totalNetWorth}
                                fiNumber={fiTarget}
                                monthlyChange={parseFloat(monthlyChange.toFixed(1))}
                                currency="USD"
                            />
                        </div>
                        <div className="md:col-span-1">
                            <ProfileCard />
                        </div>
                    </div>

                    <Tabs defaultValue="overview" className="space-y-6">
                        <TabsList className="bg-white p-1 border border-slate-200 rounded-lg shadow-sm h-auto grid grid-cols-2 md:inline-flex md:grid-cols-none gap-2">
                            <TabsTrigger value="overview" className="data-[state=active]:bg-slate-100 data-[state=active]:shadow-none px-4 py-2 h-auto gap-2">
                                <LayoutDashboard className="w-4 h-4" /> Overview
                            </TabsTrigger>
                            <TabsTrigger value="accounts" className="data-[state=active]:bg-slate-100 data-[state=active]:shadow-none px-4 py-2 h-auto gap-2">
                                <Wallet className="w-4 h-4" /> Accounts
                            </TabsTrigger>
                            <TabsTrigger value="simulation" className="data-[state=active]:bg-slate-100 data-[state=active]:shadow-none px-4 py-2 h-auto gap-2">
                                <TrendingUp className="w-4 h-4" /> Simulator
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6 animate-in fade-in slide-in-from-bottom-5 duration-500">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="md:col-span-2">
                                    <NetWorthChart data={historyData} />
                                </div>
                                <div className="md:col-span-1">
                                    <AssetAllocation data={assetAllocation} />
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="accounts" className="animate-in fade-in slide-in-from-bottom-5 duration-500">
                            <AccountTree
                                accounts={accounts}
                                onSelectAccount={(acc) => setSelectedAccount(acc)}
                            />
                        </TabsContent>

                        <TabsContent value="simulation" className="animate-in fade-in slide-in-from-bottom-5 duration-500">
                            <AdvancedFireSimulator />
                        </TabsContent>

                    </Tabs>
                </div>

                <AIChatPanel />
                <AccountDetailPanel
                    account={selectedAccount}
                    onClose={() => setSelectedAccount(null)}
                />
            </div>
        </div>
    );
}
