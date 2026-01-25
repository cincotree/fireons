export interface AccountNode {
    id: string; // The full path e.g. "Assets:Bank:Chase"
    name: string; // "Chase"
    path: string[]; // ["Assets", "Bank", "Chase"]
    balance: number; // Self balance
    total: number; // Self + Children balance
    currency: string;
    type: 'asset' | 'liability';
    children: AccountNode[];
    rawAccount?: any; // The original account object if this node is a leaf/real account
}

export function buildAccountTree(accounts: any[]): AccountNode[] {
    const rootNodes: AccountNode[] = [];
    const startMap = new Map<string, AccountNode>();

    // Helper to find or create a node
    const getOrCreateNode = (fullPath: string, parts: string[], type: 'asset' | 'liability', currency: string): AccountNode => {
        if (startMap.has(fullPath)) return startMap.get(fullPath)!;

        const name = parts[parts.length - 1];
        const newNode: AccountNode = {
            id: fullPath,
            name,
            path: parts,
            balance: 0,
            total: 0,
            currency,
            type,
            children: [],
        };
        startMap.set(fullPath, newNode);
        return newNode;
    };

    accounts.forEach(acc => {
        const parts = acc.name.split(':');
        let currentPath = "";

        // We treat 'Assets' vs 'Liabilities' prefix primarily for Type detection, 
        // but the tree structure should respect the string.
        // If raw type says Liability, the tree root usually is Liabilities.
        const type = acc.type === 'Liability' || acc.name.startsWith('Liabilities') ? 'liability' : 'asset';

        parts.forEach((part: string, index: number) => {
            const isLast = index === parts.length - 1;
            const parentPath = currentPath;
            currentPath = currentPath ? `${currentPath}:${part}` : part;

            const node = getOrCreateNode(currentPath, parts.slice(0, index + 1), type, acc.currency);

            if (isLast) {
                // leaf (or at least the level of this account)
                node.balance += acc.balance; // += in case duplicates, though ideally unique
                node.rawAccount = acc;
            }

            // Link to parent
            if (index === 0) {
                if (!rootNodes.includes(node)) rootNodes.push(node);
            } else {
                const parent = startMap.get(parentPath);
                if (parent && !parent.children.includes(node)) {
                    parent.children.push(node);
                }
            }
        });
    });

    // Calculate totals (Rollup) - Post-order traversal
    const calculateTotals = (node: AccountNode): number => {
        let childrenTotal = 0;
        for (const child of node.children) {
            childrenTotal += calculateTotals(child);
        }
        node.total = node.balance + childrenTotal;
        return node.total;
    };

    rootNodes.forEach(node => calculateTotals(node));

    return rootNodes;
}
