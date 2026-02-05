"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Modal, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/modal";
import { getBaseHttpUrl } from "@/utils/api";
import { NetWorthChart } from "@/components/NetWorthChart";
import { AssetAllocationChart } from "@/components/AssetAllocationChart";
import { AccountHierarchyTree } from "@/components/AccountHierarchyTree";

interface Account {
  id: string;
  name: string;
  account_type: string;
  currency: string;
  description: string | null;
  open_date: string;
  balance: number | null;
  balance_in_display_currency: number | null;
  display_currency: string | null;
  is_active: boolean;
}

export function NetWorthDashboard() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedCurrency, setSelectedCurrency] = useState("USD");
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [newAccountType, setNewAccountType] = useState<"Assets" | "Liabilities">("Assets");
  const [newAccountCategory, setNewAccountCategory] = useState("");
  const [newAccountSubcategory, setNewAccountSubcategory] = useState("");
  const [isNewCategory, setIsNewCategory] = useState(false);
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountDescription, setNewAccountDescription] = useState("");
  const [newAccountCurrency, setNewAccountCurrency] = useState("USD");
  const [balanceAmount, setBalanceAmount] = useState("");
  const [originalBalance, setOriginalBalance] = useState<number | null>(null);
  const [isCloseConfirmOpen, setIsCloseConfirmOpen] = useState(false);
  const [accountToClose, setAccountToClose] = useState<Account | null>(null);

  useEffect(() => {
    fetchData();
  }, [selectedCurrency]);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const accountsRes = await fetch(`${baseUrl}/api/accounts?display_currency=${selectedCurrency}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!accountsRes.ok) {
        throw new Error("Failed to fetch data");
      }

      const accountsData = await accountsRes.json();
      setAccounts(accountsData);
    } catch (err) {
      console.error("Error fetching data:", err);
      setError("Failed to load net worth data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const getExistingCategories = (type: "Assets" | "Liabilities") => {
    const categories = new Set<string>();
    accounts.forEach((account) => {
      const parts = account.name.split(":");
      if (parts[0] === type && parts.length > 1) {
        categories.add(parts[1]);
      }
    });
    return Array.from(categories).sort();
  };

  const openAccountModal = (account?: Account) => {
    if (account) {
      setEditingAccount(account);
      setSelectedAccount(account);
      const parts = account.name.split(":");
      setNewAccountType(parts[0] as "Assets" | "Liabilities");
      setNewAccountCategory(parts[1] || "");
      setNewAccountSubcategory(parts.slice(2).join(":"));
      setNewAccountName(account.name);
      setNewAccountDescription(account.description || "");
      setNewAccountCurrency(account.currency);
      setBalanceAmount(account.balance?.toString() || "");
      setOriginalBalance(account.balance ?? null);
      setIsNewCategory(false);
    } else {
      setEditingAccount(null);
      setSelectedAccount(null);
      setNewAccountType("Assets");
      setNewAccountCategory("");
      setNewAccountSubcategory("");
      setNewAccountName("");
      setNewAccountDescription("");
      setNewAccountCurrency(selectedCurrency);
      setBalanceAmount("");
      setOriginalBalance(null);
      setIsNewCategory(false);
    }
    setIsAccountModalOpen(true);
  };

  const handleSaveAccount = async () => {
    let accountName = "";

    if (!isNewCategory && !newAccountCategory) {
      alert("Please select or create a category");
      return;
    }

    if (isNewCategory && !newAccountCategory.trim()) {
      alert("Please enter a category name");
      return;
    }

    if (!newAccountSubcategory.trim()) {
      alert("Please enter an account name");
      return;
    }

    accountName = `${newAccountType}:${newAccountCategory}:${newAccountSubcategory}`;

    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      if (editingAccount) {
        const updateResponse = await fetch(`${baseUrl}/api/accounts/${editingAccount.id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: accountName,
            currency: newAccountCurrency,
            description: newAccountDescription || null,
          }),
        });

        if (!updateResponse.ok) {
          const errorData = await updateResponse.json();
          throw new Error(errorData.detail || "Failed to update account");
        }

        // Only create a new balance entry if the balance has actually changed
        const newBalance = balanceAmount ? parseFloat(balanceAmount) : null;
        const hasBalanceChanged = newBalance !== originalBalance;

        if (hasBalanceChanged && newBalance !== null && newBalance !== 0) {
          const balanceResponse = await fetch(`${baseUrl}/api/accounts/${editingAccount.id}/balance`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              amount: newBalance,
              currency: newAccountCurrency,
            }),
          });

          if (!balanceResponse.ok) {
            const errorData = await balanceResponse.json();
            throw new Error(errorData.detail || "Failed to update balance");
          }
        }
      } else {
        const response = await fetch(`${baseUrl}/api/accounts`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: accountName,
            currency: newAccountCurrency,
            description: newAccountDescription || null,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to create account");
        }

        const newAccount = await response.json();

        if (balanceAmount && parseFloat(balanceAmount) !== 0) {
          const balanceResponse = await fetch(`${baseUrl}/api/accounts/${newAccount.id}/balance`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              amount: parseFloat(balanceAmount),
              currency: newAccountCurrency,
            }),
          });

          if (!balanceResponse.ok) {
            const errorData = await balanceResponse.json();
            throw new Error(errorData.detail || "Failed to set balance");
          }
        }
      }

      setNewAccountType("Assets");
      setNewAccountCategory("");
      setNewAccountSubcategory("");
      setNewAccountName("");
      setNewAccountDescription("");
      setNewAccountCurrency("USD");
      setBalanceAmount("");
      setIsNewCategory(false);
      setEditingAccount(null);
      setSelectedAccount(null);
      setIsAccountModalOpen(false);
      await fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRequestCloseAccount = (account: Account) => {
    setAccountToClose(account);
    setIsCloseConfirmOpen(true);
  };

  const handleConfirmCloseAccount = async () => {
    if (!accountToClose) return;

    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const response = await fetch(
        `${baseUrl}/api/accounts/${accountToClose.id}/close`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to close account");
      }

      setIsCloseConfirmOpen(false);
      setAccountToClose(null);
      await fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 2,
    }).format(amount);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <p className="text-lg">Loading net worth data...</p>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-end">
        <select
          className="border rounded-lg pl-3 pr-10 py-1.5 text-sm appearance-none bg-white"
          style={{ backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`, backgroundPosition: 'right 0.5rem center', backgroundRepeat: 'no-repeat', backgroundSize: '1.5em 1.5em' }}
          value={selectedCurrency}
          onChange={(e) => setSelectedCurrency(e.target.value)}
        >
          <option value="USD">$ USD</option>
          <option value="INR">₹ INR</option>
          <option value="EUR">€ EUR</option>
          <option value="GBP">£ GBP</option>
        </select>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Net Worth Summary ({selectedCurrency})</h2>
        {accounts.length > 0 ? (() => {
          const totalAssets = accounts
            .filter(a => a.account_type === "Assets")
            .reduce((sum, a) => sum + (a.balance_in_display_currency != null ? Number(a.balance_in_display_currency) : 0), 0);
          const totalLiabilities = accounts
            .filter(a => a.account_type === "Liabilities")
            .reduce((sum, a) => sum + (a.balance_in_display_currency != null ? Number(a.balance_in_display_currency) : 0), 0);
          const netWorthValue = totalAssets - totalLiabilities;

          return (
            <div className="border rounded-lg p-4">
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Assets:</span>
                  <span className="font-medium text-green-600">
                    {formatCurrency(totalAssets, selectedCurrency)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Liabilities:</span>
                  <span className="font-medium text-red-600">
                    {formatCurrency(totalLiabilities, selectedCurrency)}
                  </span>
                </div>
                <div className="border-t pt-2 flex justify-between">
                  <span className="font-semibold">Net Worth:</span>
                  <span
                    className={`font-bold ${
                      netWorthValue >= 0 ? "text-green-600" : "text-red-600"
                    }`}
                  >
                    {formatCurrency(netWorthValue, selectedCurrency)}
                  </span>
                </div>
              </div>
            </div>
          );
        })() : (
          <p className="text-gray-500">
            No net worth data available. Add accounts and set their balances to get started.
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6 md:col-span-2">
          <h2 className="text-xl font-semibold mb-4">Growth trend</h2>
          <NetWorthChart currency={selectedCurrency} />
        </div>

        <div className="bg-white rounded-lg shadow p-6 md:col-span-1">
          <h2 className="text-xl font-semibold mb-4">Asset Allocation</h2>
          <AssetAllocationChart currency={selectedCurrency} />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Account Hierarchy</h2>
          <Button
            onClick={() => openAccountModal()}
            className="bg-gray-200 text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
          >
            Add Account
          </Button>
        </div>
        <AccountHierarchyTree
          accounts={accounts}
          onAccountClick={openAccountModal}
          currency={selectedCurrency}
        />
      </div>

      <Modal open={isAccountModalOpen} onOpenChange={setIsAccountModalOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{editingAccount ? "Edit Account" : "Add New Account"}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Row 1: Account Type and Category */}
              <div>
                <label className="block text-sm font-medium mb-1">Account Type *</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={newAccountType}
                  onChange={(e) => {
                    setNewAccountType(e.target.value as "Assets" | "Liabilities");
                    setNewAccountCategory("");
                    setIsNewCategory(false);
                  }}
                >
                  <option value="Assets">Assets</option>
                  <option value="Liabilities">Liabilities</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Category *</label>
                {!isNewCategory ? (
                  <select
                    className="w-full border rounded px-3 py-2"
                    value={newAccountCategory}
                    onChange={(e) => {
                      if (e.target.value === "_new_") {
                        setIsNewCategory(true);
                        setNewAccountCategory("");
                      } else {
                        setNewAccountCategory(e.target.value);
                      }
                    }}
                  >
                    <option value="">Select</option>
                    {getExistingCategories(newAccountType).map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                    <option value="_new_">+ Create New Category</option>
                  </select>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Category name"
                      className="flex-1 border rounded px-3 py-2"
                      value={newAccountCategory}
                      onChange={(e) => setNewAccountCategory(e.target.value)}
                    />
                    <button
                      type="button"
                      className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded"
                      onClick={() => {
                        setIsNewCategory(false);
                        setNewAccountCategory("");
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>

              {/* Row 2: Account Name and Currency */}
              <div>
                <label className="block text-sm font-medium mb-1">Account Name *</label>
                <input
                  type="text"
                  placeholder="e.g., Savings, Checking, Home Loan"
                  className="w-full border rounded px-3 py-2"
                  value={newAccountSubcategory}
                  onChange={(e) => setNewAccountSubcategory(e.target.value)}
                />
                {newAccountCategory && newAccountSubcategory && (
                  <p className="text-xs text-gray-500 mt-1">
                    Full name: {newAccountType}:{newAccountCategory}:{newAccountSubcategory}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Currency *</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={newAccountCurrency}
                  onChange={(e) => setNewAccountCurrency(e.target.value)}
                >
                  <option value="USD">$ USD</option>
                  <option value="INR">₹ INR</option>
                  <option value="EUR">€ EUR</option>
                  <option value="GBP">£ GBP</option>
                </select>
              </div>

              {/* Row 3: Current Balance (single column, left aligned) */}
              <div>
                <label className="block text-sm font-medium mb-1">
                  Current Balance ({newAccountCurrency})
                </label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  className="w-full border rounded px-3 py-2"
                  value={balanceAmount}
                  onChange={(e) => setBalanceAmount(e.target.value)}
                />
              </div>

              {/* Row 4: Description (full width) */}
              <div className="col-span-2">
                <label className="block text-sm font-medium mb-1">
                  Description (Optional)
                </label>
                <textarea
                  className="w-full border rounded px-3 py-2"
                  rows={3}
                  placeholder="Add notes about this account..."
                  value={newAccountDescription}
                  onChange={(e) => setNewAccountDescription(e.target.value)}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <div className="flex items-center justify-between w-full">
              {editingAccount ? (
                <button
                  type="button"
                  className="text-sm text-red-500 hover:text-red-700 transition-colors"
                  onClick={() => {
                    setIsAccountModalOpen(false);
                    handleRequestCloseAccount(editingAccount);
                  }}
                >
                  Remove account? click here
                </button>
              ) : <span />}
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setIsAccountModalOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveAccount}
                  className="bg-gray-200 text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
                >
                  {editingAccount ? "Save Changes" : "Create Account"}
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Modal>

      <Modal open={isCloseConfirmOpen} onOpenChange={setIsCloseConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Close Account</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-gray-700">
              Are you sure you want to close <span className="font-semibold">{accountToClose?.name}</span>?
            </p>
            <p className="text-sm text-gray-500 mt-2">
              The account will be marked as closed and hidden from the dashboard, but all historical data will be preserved.
            </p>
          </div>
          <DialogFooter>
            <div className="flex gap-3 justify-end w-full">
              <Button variant="outline" onClick={() => setIsCloseConfirmOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleConfirmCloseAccount}
                className="bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                Close Account
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Modal>
    </div>
  );
}
