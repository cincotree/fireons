"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getBaseHttpUrl } from "@/utils/api";

interface Account {
  id: string;
  name: string;
  account_type: string;
  currency: string;
  description: string | null;
  open_date: string;
  current_balance: number | null;
  is_active: boolean;
}

interface NewAccountRow {
  accountType: string;
  category: string;
  accountName: string;
  currency: string;
  description: string;
  balance: string;
}

interface EditingField {
  accountId: string;
  field: 'type' | 'category' | 'name' | 'currency' | 'description' | 'balance';
  value: string;
  error?: string;
}

const ASSET_CATEGORIES = [
  { id: "Cash", label: "Cash & Checking" },
  { id: "Savings", label: "Savings" },
  { id: "Retirement", label: "Retirement Accounts" },
  { id: "Investment", label: "Investment & Brokerage" },
  { id: "Deposit", label: "Fixed Deposits" },
  { id: "RealEstate", label: "Real Estate" },
  { id: "Vehicle", label: "Vehicles" },
  { id: "Crypto", label: "Cryptocurrency" },
  { id: "Other", label: "Other Assets" },
];

const LIABILITY_CATEGORIES = [
  { id: "CreditCard", label: "Credit Cards" },
  { id: "Loan", label: "Loans" },
  { id: "Mortgage", label: "Mortgage" },
  { id: "Other", label: "Other Debt" },
];

interface BalanceEntry {
  id: string;
  account_id: string;
  account_name: string;
  account_type: string;
  amount: number;
  currency: string;
  date: string;
}

interface NetWorthSummary {
  currency: string;
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
}

interface NetWorthResponse {
  as_of_date: string;
  by_currency: NetWorthSummary[];
  entries: BalanceEntry[];
}

export function NetWorthDashboard() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [netWorth, setNetWorth] = useState<NetWorthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newAccountRows, setNewAccountRows] = useState<NewAccountRow[]>([]);
  const [editingField, setEditingField] = useState<EditingField | null>(null);
  const [newRowErrors, setNewRowErrors] = useState<Record<number, string>>({});

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    let token = null;
    for (let i = 0; i < 5; i++) {
      token = localStorage.getItem('token');
      if (token) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    try {
      const baseUrl = await getBaseHttpUrl();

      if (!token) {
        throw new Error("Not authenticated");
      }

      const headers = {
        'Authorization': `Bearer ${token}`,
      };

      const [accountsRes, networthRes] = await Promise.all([
        fetch(`${baseUrl}/api/networth/accounts`, { headers }),
        fetch(`${baseUrl}/api/networth/summary`, { headers }),
      ]);

      if (!accountsRes.ok || !networthRes.ok) {
        if (accountsRes.status === 401 || networthRes.status === 401) {
          localStorage.removeItem('token');
          throw new Error("Authentication failed. Please log in again.");
        }
        throw new Error("Failed to fetch data");
      }

      const accountsData = await accountsRes.json();
      const networthData = await networthRes.json();

      setAccounts(accountsData);
      setNetWorth(networthData);
    } catch (err) {
      setError("Failed to load net worth data. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const addNewAccountRow = () => {
    setNewAccountRows([
      ...newAccountRows,
      {
        accountType: "",
        category: "",
        accountName: "",
        currency: "USD",
        description: "",
        balance: "",
      },
    ]);
  };

  const removeNewAccountRow = (index: number) => {
    setNewAccountRows(newAccountRows.filter((_, i) => i !== index));
  };

  const updateNewAccountRow = (
    index: number,
    field: keyof NewAccountRow,
    value: string
  ) => {
    const updated = [...newAccountRows];
    updated[index][field] = value;
    setNewAccountRows(updated);
  };

  const saveNewAccount = async (index: number) => {
    const row = newAccountRows[index];

    if (!row.accountType || !row.category || !row.accountName.trim()) {
      setNewRowErrors({ ...newRowErrors, [index]: "Please fill in all required fields" });
      return;
    }

    setNewRowErrors({ ...newRowErrors, [index]: "" });

    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      if (!token) {
        setNewRowErrors({ ...newRowErrors, [index]: "Not authenticated. Please log in again." });
        return;
      }

      const fullAccountName = `${row.accountType}:${row.category}:${row.accountName.trim()}`;

      const accountResponse = await fetch(`${baseUrl}/api/networth/accounts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: fullAccountName,
          currency: row.currency,
          description: row.description || null,
        }),
      });

      if (!accountResponse.ok) {
        const errorData = await accountResponse.json();
        setNewRowErrors({ ...newRowErrors, [index]: errorData.detail || "Failed to create account" });
        return;
      }

      const createdAccount = await accountResponse.json();

      if (row.balance && row.balance.trim()) {
        const balanceResponse = await fetch(`${baseUrl}/api/networth/balances`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            account_id: createdAccount.id,
            amount: parseFloat(row.balance),
            currency: row.currency,
          }),
        });

        if (!balanceResponse.ok) {
          console.error("Failed to set initial balance");
        }
      }

      const updatedErrors = { ...newRowErrors };
      delete updatedErrors[index];
      setNewRowErrors(updatedErrors);
      removeNewAccountRow(index);
      await fetchData();
    } catch (err: any) {
      setNewRowErrors({ ...newRowErrors, [index]: err.message });
    }
  };

  const deleteAccount = async (accountId: string) => {
    if (!confirm("Are you sure you want to delete this account?")) {
      return;
    }

    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      if (!token) {
        throw new Error("Not authenticated");
      }

      const response = await fetch(`${baseUrl}/api/networth/accounts/${accountId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to delete account");
      }

      await fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const startEditingField = (accountId: string, field: 'type' | 'category' | 'name' | 'currency' | 'description' | 'balance', currentValue: string) => {
    setEditingField({ accountId, field, value: currentValue });
  };

  const cancelEditingField = () => {
    setEditingField(null);
  };

  const saveField = async (account: Account) => {
    if (!editingField) return;

    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      if (!token) {
        setEditingField({ ...editingField, error: "Not authenticated. Please log in again." });
        return;
      }

      if (editingField.field === 'balance') {
        if (!editingField.value.trim()) {
          setEditingField({ ...editingField, error: "Please enter a balance" });
          return;
        }

        const response = await fetch(`${baseUrl}/api/networth/balances`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            account_id: account.id,
            amount: parseFloat(editingField.value),
            currency: account.currency,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          setEditingField({ ...editingField, error: errorData.detail || "Failed to update balance" });
          return;
        }
      } else if (editingField.field === 'name' || editingField.field === 'description' || editingField.field === 'type' || editingField.field === 'category' || editingField.field === 'currency') {
        const nameParts = account.name.split(":");
        let accountType = nameParts[0] || "";
        let category = nameParts[1] || "";
        const displayName = nameParts.slice(2).join(":") || account.name;

        let newFullName = account.name;
        let newDescription = account.description;
        let newCurrency = account.currency;

        if (editingField.field === 'name') {
          if (!editingField.value.trim()) {
            setEditingField({ ...editingField, error: "Account name cannot be empty" });
            return;
          }
          newFullName = `${accountType}:${category}:${editingField.value.trim()}`;
        } else if (editingField.field === 'type') {
          if (!editingField.value) {
            setEditingField({ ...editingField, error: "Please select a type" });
            return;
          }
          accountType = editingField.value;
          newFullName = `${accountType}:${category}:${displayName}`;
        } else if (editingField.field === 'category') {
          if (!editingField.value) {
            setEditingField({ ...editingField, error: "Please select a category" });
            return;
          }
          category = editingField.value;
          newFullName = `${accountType}:${category}:${displayName}`;
        } else if (editingField.field === 'description') {
          newDescription = editingField.value.trim() || null;
        } else if (editingField.field === 'currency') {
          if (!editingField.value) {
            setEditingField({ ...editingField, error: "Please select a currency" });
            return;
          }
          newCurrency = editingField.value;
        }

        const response = await fetch(`${baseUrl}/api/networth/accounts/${account.id}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: newFullName,
            description: newDescription,
            currency: newCurrency,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          setEditingField({ ...editingField, error: errorData.detail || "Failed to update account" });
          return;
        }
      }

      setEditingField(null);
      await fetchData();
    } catch (err: any) {
      setEditingField({ ...editingField, error: err.message });
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
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Net Worth Tracker</h1>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Net Worth Summary</h2>
        {netWorth && netWorth.by_currency.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {netWorth.by_currency.map((summary) => (
              <div key={summary.currency} className="border rounded-lg p-4">
                <div className="text-sm text-gray-500 mb-2">{summary.currency}</div>
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Assets:</span>
                    <span className="font-medium text-green-600">
                      {formatCurrency(summary.total_assets, summary.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Liabilities:</span>
                    <span className="font-medium text-red-600">
                      {formatCurrency(summary.total_liabilities, summary.currency)}
                    </span>
                  </div>
                  <div className="border-t pt-2 flex justify-between">
                    <span className="font-semibold">Net Worth:</span>
                    <span
                      className={`font-bold ${
                        summary.net_worth >= 0 ? "text-green-600" : "text-red-600"
                      }`}
                    >
                      {formatCurrency(summary.net_worth, summary.currency)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">
            No net worth data available. Add accounts and set their balances to get started.
          </p>
        )}
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Accounts</h2>
            <Button onClick={addNewAccountRow} size="sm" variant="outline">
              + Add Account
            </Button>
          </div>
          {accounts.length > 0 || newAccountRows.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Account Name</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Current Balance</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((account) => {
                  const nameParts = account.name.split(":");
                  const accountType = nameParts[0] || "";
                  const category = nameParts[1] || "";
                  const displayName = nameParts.slice(2).join(":") || account.name;
                  const isEditingType = editingField?.accountId === account.id && editingField.field === 'type';
                  const isEditingCategory = editingField?.accountId === account.id && editingField.field === 'category';
                  const isEditingName = editingField?.accountId === account.id && editingField.field === 'name';
                  const isEditingCurrency = editingField?.accountId === account.id && editingField.field === 'currency';
                  const isEditingDescription = editingField?.accountId === account.id && editingField.field === 'description';
                  const isEditingBalance = editingField?.accountId === account.id && editingField.field === 'balance';

                  return (
                    <TableRow key={account.id}>
                      <TableCell>
                        {isEditingType ? (
                          <div className="relative">
                            <div className="flex items-center gap-2">
                              <select
                                className={`border rounded px-2 py-1 text-sm ${editingField.error ? 'border-red-500' : ''}`}
                                value={editingField.value}
                                onChange={(e) => setEditingField({ ...editingField, value: e.target.value, error: undefined })}
                                autoFocus
                              >
                                <option value="">Select Type</option>
                                <option value="Assets">Assets</option>
                                <option value="Liabilities">Liabilities</option>
                              </select>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => saveField(account)}
                              >
                                Save
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingField}
                                className="text-gray-600"
                              >
                                Cancel
                              </Button>
                            </div>
                            {editingField.error && (
                              <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                                {editingField.error}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span
                            className={`px-2 py-1 rounded text-xs cursor-pointer hover:ring-2 hover:ring-blue-300 ${
                              account.account_type === "Assets"
                                ? "bg-green-100 text-green-800"
                                : "bg-red-100 text-red-800"
                            }`}
                            onClick={() => startEditingField(account.id, 'type', accountType)}
                          >
                            {accountType}
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {isEditingCategory ? (
                          <div className="relative">
                            <div className="flex items-center gap-2">
                              <select
                                className={`border rounded px-2 py-1 text-sm ${editingField.error ? 'border-red-500' : ''}`}
                                value={editingField.value}
                                onChange={(e) => setEditingField({ ...editingField, value: e.target.value, error: undefined })}
                                autoFocus
                              >
                                <option value="">Select Category</option>
                                {(accountType === "Assets" ? ASSET_CATEGORIES : LIABILITY_CATEGORIES).map((cat) => (
                                  <option key={cat.id} value={cat.id}>
                                    {cat.label}
                                  </option>
                                ))}
                              </select>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => saveField(account)}
                              >
                                Save
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingField}
                                className="text-gray-600"
                              >
                                Cancel
                              </Button>
                            </div>
                            {editingField.error && (
                              <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                                {editingField.error}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div
                            className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                            onClick={() => startEditingField(account.id, 'category', category)}
                          >
                            {category}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="font-medium">
                        {isEditingName ? (
                          <div className="relative">
                            <div className="flex items-center gap-2">
                              <input
                                type="text"
                                className={`w-full border rounded px-2 py-1 text-sm ${editingField.error ? 'border-red-500' : ''}`}
                                value={editingField.value}
                                onChange={(e) => setEditingField({ ...editingField, value: e.target.value, error: undefined })}
                                autoFocus
                              />
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => saveField(account)}
                              >
                                Save
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingField}
                                className="text-gray-600"
                              >
                                Cancel
                              </Button>
                            </div>
                            {editingField.error && (
                              <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                                {editingField.error}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div
                            className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                            onClick={() => startEditingField(account.id, 'name', displayName)}
                          >
                            {displayName}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        {isEditingCurrency ? (
                          <div className="relative">
                            <div className="flex items-center gap-2">
                              <select
                                className={`border rounded px-2 py-1 text-sm ${editingField.error ? 'border-red-500' : ''}`}
                                value={editingField.value}
                                onChange={(e) => setEditingField({ ...editingField, value: e.target.value, error: undefined })}
                                autoFocus
                              >
                                <option value="USD">USD</option>
                                <option value="INR">INR</option>
                                <option value="EUR">EUR</option>
                                <option value="GBP">GBP</option>
                              </select>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => saveField(account)}
                              >
                                Save
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingField}
                                className="text-gray-600"
                              >
                                Cancel
                              </Button>
                            </div>
                            {editingField.error && (
                              <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                                {editingField.error}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div
                            className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                            onClick={() => startEditingField(account.id, 'currency', account.currency)}
                          >
                            {account.currency}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        {isEditingBalance ? (
                          <div className="relative">
                            <div className="flex items-center gap-2">
                              <input
                                type="number"
                                step="0.01"
                                className={`w-32 border rounded px-2 py-1 text-sm ${editingField.error ? 'border-red-500' : ''}`}
                                value={editingField.value}
                                onChange={(e) => setEditingField({ ...editingField, value: e.target.value, error: undefined })}
                                autoFocus
                              />
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => saveField(account)}
                              >
                                Save
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingField}
                                className="text-gray-600"
                              >
                                Cancel
                              </Button>
                            </div>
                            {editingField.error && (
                              <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                                {editingField.error}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div
                            className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                            onClick={() => startEditingField(account.id, 'balance', account.current_balance?.toString() || "")}
                          >
                            {account.current_balance !== null
                              ? formatCurrency(account.current_balance, account.currency)
                              : "Click to set"}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {isEditingDescription ? (
                          <div className="relative">
                            <div className="flex items-center gap-2">
                              <input
                                type="text"
                                className={`w-full border rounded px-2 py-1 text-sm ${editingField.error ? 'border-red-500' : ''}`}
                                value={editingField.value}
                                onChange={(e) => setEditingField({ ...editingField, value: e.target.value, error: undefined })}
                                autoFocus
                              />
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => saveField(account)}
                              >
                                Save
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingField}
                                className="text-gray-600"
                              >
                                Cancel
                              </Button>
                            </div>
                            {editingField.error && (
                              <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                                {editingField.error}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div
                            className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                            onClick={() => startEditingField(account.id, 'description', account.description || "")}
                          >
                            {account.description || "Click to add"}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteAccount(account.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {newAccountRows.map((row, index) => {
                  const categories =
                    row.accountType === "Assets"
                      ? ASSET_CATEGORIES
                      : row.accountType === "Liabilities"
                      ? LIABILITY_CATEGORIES
                      : [];
                  const rowError = newRowErrors[index];
                  const hasError = rowError && (!row.accountType || !row.category || !row.accountName.trim());

                  return (
                    <TableRow key={`new-${index}`} className="bg-blue-50">
                      <TableCell>
                        <div className="relative">
                          <select
                            className={`w-full border rounded px-2 py-1 text-sm ${hasError && !row.accountType ? 'border-red-500' : ''}`}
                            value={row.accountType}
                            onChange={(e) => {
                              updateNewAccountRow(index, "accountType", e.target.value);
                              if (rowError) {
                                const updated = { ...newRowErrors };
                                delete updated[index];
                                setNewRowErrors(updated);
                              }
                            }}
                          >
                            <option value="">Select Type</option>
                            <option value="Assets">Assets</option>
                            <option value="Liabilities">Liabilities</option>
                          </select>
                          {hasError && !row.accountType && (
                            <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                              Type is required
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="relative">
                          <select
                            className={`w-full border rounded px-2 py-1 text-sm ${hasError && !row.category ? 'border-red-500' : ''}`}
                            value={row.category}
                            onChange={(e) => {
                              updateNewAccountRow(index, "category", e.target.value);
                              if (rowError) {
                                const updated = { ...newRowErrors };
                                delete updated[index];
                                setNewRowErrors(updated);
                              }
                            }}
                            disabled={!row.accountType}
                          >
                            <option value="">Select Category</option>
                            {categories.map((cat) => (
                              <option key={cat.id} value={cat.id}>
                                {cat.label}
                              </option>
                            ))}
                          </select>
                          {hasError && !row.category && (
                            <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                              Category is required
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="relative">
                          <input
                            type="text"
                            className={`w-full border rounded px-2 py-1 text-sm ${hasError && !row.accountName.trim() ? 'border-red-500' : ''}`}
                            placeholder="Account name"
                            value={row.accountName}
                            onChange={(e) => {
                              updateNewAccountRow(index, "accountName", e.target.value);
                              if (rowError) {
                                const updated = { ...newRowErrors };
                                delete updated[index];
                                setNewRowErrors(updated);
                              }
                            }}
                          />
                          {hasError && !row.accountName.trim() && (
                            <div className="absolute left-0 top-full mt-1 bg-red-50 border border-red-300 text-red-700 text-xs px-2 py-1 rounded shadow-sm z-10 whitespace-nowrap">
                              Account name is required
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <select
                          className="w-full border rounded px-2 py-1 text-sm"
                          value={row.currency}
                          onChange={(e) => {
                            updateNewAccountRow(index, "currency", e.target.value);
                            if (rowError) {
                              const updated = { ...newRowErrors };
                              delete updated[index];
                              setNewRowErrors(updated);
                            }
                          }}
                        >
                          <option value="USD">USD</option>
                          <option value="INR">INR</option>
                          <option value="EUR">EUR</option>
                          <option value="GBP">GBP</option>
                        </select>
                      </TableCell>
                      <TableCell>
                        <input
                          type="number"
                          step="0.01"
                          className="w-32 border rounded px-2 py-1 text-sm"
                          placeholder="0.00"
                          value={row.balance}
                          onChange={(e) => {
                            updateNewAccountRow(index, "balance", e.target.value);
                            if (rowError) {
                              const updated = { ...newRowErrors };
                              delete updated[index];
                              setNewRowErrors(updated);
                            }
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <input
                          type="text"
                          className="w-full border rounded px-2 py-1 text-sm"
                          placeholder="Optional description"
                          value={row.description}
                          onChange={(e) => {
                            updateNewAccountRow(index, "description", e.target.value);
                            if (rowError) {
                              const updated = { ...newRowErrors };
                              delete updated[index];
                              setNewRowErrors(updated);
                            }
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => saveNewAccount(index)}
                          >
                            Save
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => removeNewAccountRow(index)}
                            className="text-gray-600"
                          >
                            Cancel
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          ) : (
            <p className="text-gray-500">
              No accounts yet. Click "+ Add Account" to create your first account.
            </p>
          )}
        </div>
      </div>

    </div>
  );
}
