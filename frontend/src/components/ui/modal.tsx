import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const styles = {
    dialog: {
        position: 'fixed' as const,
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        margin: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
    },
    dialogOverlay: {
        position: 'absolute' as const,
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        zIndex: 1000,
    },
    dialogContent: {
        position: 'relative' as const,
        backgroundColor: '#f9fafb',
        padding: '20px',
        borderRadius: '8px',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.1)',
        zIndex: 1002,
        maxWidth: '500px',
        maxHeight: '90vh',
        overflow: 'auto',
    },
    dialogContentWide: {
        maxWidth: '960px',
    },
    dialogClose: {
        position: 'absolute' as const,
        top: '12px',
        right: '12px',
    },
    dialogContentInner: {
        padding: '10px',
    },
    dialogHeader: {
        marginBottom: '10px',
    },
    dialogTitle: {
        margin: 0,
        fontSize: '1.5em',
        color: '#1f2937',
    },
    dialogFooter: {
        marginTop: '10px',
        textAlign: 'right' as const,
    },
};

interface DialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    children: React.ReactNode;
    size?: 'default' | 'wide';
    dismissible?: boolean;
}

interface DialogContentProps {
    children: React.ReactNode;
}

export const Modal = ({ open, onOpenChange, children, size = 'default', dismissible = false }: DialogProps) => {
    const onOpenChangeRef = useRef(onOpenChange);
    onOpenChangeRef.current = onOpenChange;

    useEffect(() => {
        if (!open || !dismissible) return;
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') onOpenChangeRef.current(false);
        };
        document.addEventListener('keydown', onKeyDown);
        return () => document.removeEventListener('keydown', onKeyDown);
    }, [open, dismissible]);

    if (!open) return null;

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onOpenChange(false);
        }
    };

    const contentStyle = size === 'wide'
        ? { ...styles.dialogContent, ...styles.dialogContentWide }
        : styles.dialogContent;

    return (
        <div style={styles.dialog} onClick={handleOverlayClick}>
            <div data-testid="modal-backdrop" style={styles.dialogOverlay} />
            <div style={contentStyle}>
                {dismissible && (
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="Close"
                        title="Close"
                        style={styles.dialogClose}
                        onClick={() => onOpenChange(false)}
                    >
                        <X className="h-4 w-4" />
                    </Button>
                )}
                {children}
            </div>
        </div>
    );
};

export const DialogContent = ({ children }: DialogContentProps) => (
    <div style={styles.dialogContentInner}>{children}</div>
);

export const DialogHeader = ({ children }: { children: React.ReactNode }) => (
    <div style={styles.dialogHeader}>{children}</div>
);

export const DialogTitle = ({ children }: { children: React.ReactNode }) => (
    <h2 style={styles.dialogTitle}>{children}</h2>
);

export const DialogFooter = ({ children }: { children: React.ReactNode }) => (
    <div style={styles.dialogFooter}>{children}</div>
);
