"use client";

import { useState } from "react";
import { ChevronRight, ChevronDown, Pencil } from "lucide-react";

interface Account {
  id: string;
  name: string;
  account_type: string;
  currency: string;
  balance: number | null;
  balance_in_display_currency: number | null;
}

interface TreeNode {
  name: string;
  fullPath: string;
  children: Map<string, TreeNode>;
  account: Account | null;
  isExpanded: boolean;
}

interface AccountHierarchyTreeProps {
  accounts: Account[];
  onAccountClick?: (account: Account) => void;
  currency?: string;
}

export function AccountHierarchyTree({
  accounts,
  onAccountClick,
  currency = "USD",
}: AccountHierarchyTreeProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(() => {
    const allPaths = new Set<string>();
    accounts.forEach((account) => {
      const parts = account.name.split(":");
      let currentPath = "";
      parts.forEach((part, index) => {
        currentPath = currentPath ? `${currentPath}:${part}` : part;
        if (index < parts.length - 1) {
          allPaths.add(currentPath);
        }
      });
    });
    return allPaths;
  });

  const getCurrencyColor = (currencyCode: string): string => {
    const colors: Record<string, string> = {
      USD: "#22c55e", // green
      INR: "#f97316", // orange
      EUR: "#3b82f6", // blue
      GBP: "#a855f7", // purple
    };
    return colors[currencyCode] || "#6b7280"; // default gray
  };

  const getCurrencySymbol = (currencyCode: string): string => {
    const symbols: Record<string, string> = {
      USD: "$",
      INR: "₹",
      EUR: "€",
      GBP: "£",
    };
    return symbols[currencyCode] || currencyCode;
  };

  const buildTree = (): Map<string, TreeNode> => {
    const root = new Map<string, TreeNode>();

    accounts.forEach((account) => {
      const parts = account.name.split(":");
      let currentLevel = root;
      let currentPath = "";

      parts.forEach((part, index) => {
        currentPath = currentPath ? `${currentPath}:${part}` : part;

        if (!currentLevel.has(part)) {
          currentLevel.set(part, {
            name: part,
            fullPath: currentPath,
            children: new Map(),
            account: index === parts.length - 1 ? account : null,
            isExpanded: expandedNodes.has(currentPath),
          });
        }

        if (index === parts.length - 1) {
          const node = currentLevel.get(part)!;
          node.account = account;
        }

        currentLevel = currentLevel.get(part)!.children;
      });
    });

    return root;
  };

  const toggleNode = (path: string) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const calculateNodeTotal = (node: TreeNode): number => {
    if (node.account) {
      const balance = node.account.balance_in_display_currency;
      if (balance === null || balance === undefined) {
        return 0;
      }
      const numBalance = typeof balance === 'number' ? balance : parseFloat(String(balance));
      return isNaN(numBalance) ? 0 : numBalance;
    }

    let total = 0;
    node.children.forEach((child) => {
      const childTotal = calculateNodeTotal(child);
      if (!isNaN(childTotal)) {
        total += childTotal;
      }
    });

    return total;
  };

  const renderNode = (node: TreeNode, level: number = 0) => {
    const hasChildren = node.children.size > 0;
    const isExpanded = expandedNodes.has(node.fullPath);
    const paddingLeft = level * 24;
    const nodeTotal = calculateNodeTotal(node);

    return (
      <div key={node.fullPath}>
        <div
          className={`grid grid-cols-12 gap-4 items-center py-2 px-3 hover:bg-gray-50 ${
            node.account ? "font-normal" : "font-medium"
          }`}
        >
          <div
            className="col-span-6 flex items-center gap-2 cursor-pointer"
            style={{ paddingLeft: `${paddingLeft}px` }}
            onClick={() => {
              if (hasChildren) {
                toggleNode(node.fullPath);
              } else if (node.account && onAccountClick) {
                onAccountClick(node.account);
              }
            }}
          >
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-500" strokeWidth={3} />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" strokeWidth={3} />
              )
            ) : (
              <span className="w-4" />
            )}
            {node.account && (
              <div
                className="flex items-center justify-center w-[18px] h-[18px] rounded-full text-white text-[10px] font-medium"
                style={{ backgroundColor: getCurrencyColor(node.account.currency) }}
                title={node.account.currency}
              >
                {getCurrencySymbol(node.account.currency)}
              </div>
            )}
            <span className={node.account ? "text-gray-700" : "text-gray-900"}>
              {node.name}
            </span>
            {node.account && onAccountClick && (
              <button
                className="p-1 bg-gray-200 text-blue-600 hover:bg-blue-100 rounded ml-2 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onAccountClick(node.account!);
                }}
                title="Edit"
                aria-label="Edit account"
              >
                <Pencil className="h-3 w-3" />
              </button>
            )}
          </div>
          <div className="col-span-3 text-right text-sm text-gray-600">
            {node.account && node.account.balance !== null
              ? new Intl.NumberFormat("en-US", {
                  style: "currency",
                  currency: node.account.currency,
                  minimumFractionDigits: 2,
                }).format(node.account.balance)
              : ""}
          </div>
          <div className="col-span-3 text-right text-sm font-semibold text-gray-700">
            {hasChildren && nodeTotal !== 0 ? formatCurrency(nodeTotal) : ""}
          </div>
        </div>
        {hasChildren && isExpanded && (
          <div>
            {Array.from(node.children.values()).map((child) =>
              renderNode(child, level + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  const tree = buildTree();

  if (accounts.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No accounts yet. Add accounts to see the hierarchy.
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="grid grid-cols-12 gap-4 px-3 py-2 bg-gray-50 border-b font-bold text-sm text-gray-700">
        <div className="col-span-6">Account</div>
        <div className="col-span-3 text-right">Balance</div>
        <div className="col-span-3 text-right">Total ({currency})</div>
      </div>
      {Array.from(tree.values()).map((node) => renderNode(node))}
    </div>
  );
}
