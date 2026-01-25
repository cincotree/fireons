"use client";

import { useState, useMemo } from "react";
import {
    ChevronRight,
    ChevronDown,
    MoreHorizontal,
    Plus,
    TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { buildAccountTree, AccountNode } from "@/lib/hierarchyUtils";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

interface AccountTreeProps {
    accounts: any[];
    onSelectAccount?: (account: any) => void;
}

export function AccountTree({ accounts, onSelectAccount }: AccountTreeProps) {
    const treeData = useMemo(() => buildAccountTree(accounts), [accounts]);

    // State for expanded nodes - default open root nodes
    const [expanded, setExpanded] = useState<Record<string, boolean>>({});

    const toggleExpand = (id: string) => {
        setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
    };

    // Initialize all to expanded for better overview initially for "Beancount" feel
    useMemo(() => {
        const allIds: Record<string, boolean> = {};
        const traverse = (nodes: AccountNode[]) => {
            nodes.forEach(n => {
                allIds[n.id] = true;
                traverse(n.children);
            });
        }
        traverse(treeData);
        setExpanded(allIds);
    }, [treeData]);


    const formatCurrency = (val: number, currency: string) => {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 0 }).format(val);
    };

    const TreeNode = ({ node, level }: { node: AccountNode, level: number }) => {
        const isLeaf = node.children.length === 0;
        const isOpen = expanded[node.id];
        // Check if node is essentially a grouping node (no raw account) or a real account
        const isGroup = !node.rawAccount;

        return (
            <>
                <TableRow
                    className="hover:bg-slate-50 group transition-colors cursor-pointer"
                    onClick={() => {
                        // If it's a leaf/account, select it. otherwise toggle.
                        if (isLeaf && node.rawAccount && onSelectAccount) {
                            onSelectAccount(node.rawAccount);
                        } else if (!isLeaf) {
                            toggleExpand(node.id);
                        }
                    }}
                >
                    <TableCell className="p-2">
                        <div
                            className="flex items-center gap-1 select-none"
                            style={{ paddingLeft: `${level * 20}px` }}
                            onClick={(e) => {
                                // chevron click always toggles
                                if (!isLeaf) {
                                    e.stopPropagation();
                                    toggleExpand(node.id);
                                }
                            }}
                        >
                            <div className="w-5 h-5 flex items-center justify-center shrink-0 text-slate-400 hover:text-slate-600">
                                {!isLeaf && (isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />)}
                            </div>
                            <span className={`font-medium ${isGroup ? 'text-slate-600' : 'text-slate-900'} ${isLeaf ? 'hover:text-indigo-600 hover:underline' : ''}`}>
                                {node.name}
                            </span>
                            {isGroup && <span className="text-xs text-slate-400 font-normal ml-2">({node.children.length})</span>}
                        </div>
                    </TableCell>

                    <TableCell className="p-2 text-right font-mono text-slate-600">
                        {/* Only show self-balance if it differs from total or if it's a leaf */}
                        {isLeaf && node.balance !== 0 ? formatCurrency(node.balance, node.currency) : <span className="text-slate-300">-</span>}
                    </TableCell>

                    <TableCell className="p-2 text-right font-bold text-slate-900 font-mono bg-slate-50/50">
                        {formatCurrency(node.total, node.currency)}
                    </TableCell>

                    <TableCell className="p-2 text-center">
                        {/* Quick Actions */}
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" title="Add Value" onClick={(e) => { e.stopPropagation(); /* TODO */ }}>
                                <Plus className="w-4 h-4 text-emerald-600" />
                            </Button>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" title="Chart" onClick={(e) => { e.stopPropagation(); onSelectAccount?.(node.rawAccount); }}>
                                <TrendingUp className="w-4 h-4 text-indigo-600" />
                            </Button>
                            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" title="Edit" onClick={(e) => { e.stopPropagation(); /* TODO */ }}>
                                <MoreHorizontal className="w-4 h-4 text-slate-400" />
                            </Button>
                        </div>
                    </TableCell>
                </TableRow>

                {isOpen && node.children.map(child => (
                    <TreeNode key={child.id} node={child} level={level + 1} />
                ))}
            </>
        );
    };

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-none overflow-hidden">
            <div className="p-4 border-b border-slate-200 flex justify-between items-center bg-slate-50/50">
                <h3 className="font-bold text-slate-800">Accounts Hierarchy</h3>
                <Button size="sm" className="gap-2 bg-indigo-600 hover:bg-indigo-700 text-white border-0">
                    <Plus className="w-4 h-4" /> Add Account
                </Button>
            </div>
            <Table>
                <TableHeader>
                    <TableRow className="bg-slate-50 hover:bg-slate-50">
                        <TableHead className="w-[400px]">Account</TableHead>
                        <TableHead className="text-right">Balance</TableHead>
                        <TableHead className="text-right">Total (Rollup)</TableHead>
                        <TableHead className="w-[100px] text-right">Actions</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {treeData.map(node => (
                        <TreeNode key={node.id} node={node} level={0} />
                    ))}
                    {treeData.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={4} className="h-24 text-center text-slate-400">
                                No accounts found. Use the hierarchical naming format (e.g., 'Assets:Bank:Name').
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    );
}
