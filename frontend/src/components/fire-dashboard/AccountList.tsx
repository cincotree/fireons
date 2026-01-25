"use client";

import { useState } from "react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge"; // Assuming we have Badge or need to make one. using div for now if not.
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, Edit2, TrendingUp, TrendingDown } from "lucide-react";

interface Account {
    id: string;
    name: string;
    type: string;
    balance: number;
    currency: string;
}

interface AccountListProps {
    accounts: Account[];
}

export function AccountList({ accounts }: AccountListProps) {
    const assets = accounts.filter(a => a.type !== 'Liability');
    const liabilities = accounts.filter(a => a.type === 'Liability');

    const formatCurrency = (amount: number, currency: string) => {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: currency,
        }).format(amount);
    };

    const AccountTable = ({ data, type }: { data: Account[], type: 'asset' | 'liability' }) => (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Currency</TableHead>
                        <TableHead className="text-right">Balance</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {data.map((account) => (
                        <TableRow key={account.id}>
                            <TableCell className="font-medium">
                                <div className="flex items-center gap-2">
                                    <div className={`p-1.5 rounded-full ${type === 'asset' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                                        {type === 'asset' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                    </div>
                                    {account.name}
                                </div>
                            </TableCell>
                            <TableCell>
                                <span className="inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
                                    {account.type}
                                </span>
                            </TableCell>
                            <TableCell>
                                <span className="text-slate-500 font-medium text-sm">{account.currency}</span>
                            </TableCell>
                            <TableCell className="text-right font-medium">
                                {formatCurrency(account.balance, account.currency)}
                            </TableCell>
                            <TableCell className="text-right">
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                                    <Edit2 className="w-4 h-4 text-slate-500" />
                                </Button>
                            </TableCell>
                        </TableRow>
                    ))}
                    {data.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={4} className="h-24 text-center text-slate-500">
                                No {type === 'asset' ? 'assets' : 'liabilities'} found. Add one to get started.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    );

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-900">Your Accounts</h3>
                <Button size="sm" className="gap-1">
                    <Plus className="w-4 h-4" /> Add Account
                </Button>
            </div>

            <Tabs defaultValue="assets" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-4">
                    <TabsTrigger value="assets">Assets ({assets.length})</TabsTrigger>
                    <TabsTrigger value="liabilities">Liabilities ({liabilities.length})</TabsTrigger>
                </TabsList>
                <TabsContent value="assets">
                    <AccountTable data={assets} type="asset" />
                </TabsContent>
                <TabsContent value="liabilities">
                    <AccountTable data={liabilities} type="liability" />
                </TabsContent>
            </Tabs>
        </div>
    );
}
