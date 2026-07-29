"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Modal, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/modal";
import { UploadStatementFlow } from "@/components/UploadStatementFlow";
import { UploadCASFlow } from "@/components/UploadCASFlow";

interface ImportStatementFlowProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

type StatementChoice = "bank" | "cas" | null;

export function ImportStatementFlow({ open, onClose, onImported }: ImportStatementFlowProps) {
  const [choice, setChoice] = useState<StatementChoice>(null);

  const handleClose = () => {
    setChoice(null);
    onClose();
  };

  if (choice === "bank") {
    return <UploadStatementFlow open={open} onClose={handleClose} onImported={onImported} />;
  }

  if (choice === "cas") {
    return <UploadCASFlow open={open} onClose={handleClose} onImported={onImported} />;
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) handleClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Statement</DialogTitle>
        </DialogHeader>

        <div className="py-2 space-y-3">
          <p className="text-sm text-gray-600">What kind of statement are you importing?</p>

          <button
            className="w-full text-left border rounded px-4 py-3 hover:bg-blue-50 hover:border-blue-300 transition-colors"
            onClick={() => setChoice("bank")}
          >
            <div className="font-medium">Bank Statement</div>
            <div className="text-xs text-gray-500">
              Import a bank account statement PDF (e.g. HDFC)
            </div>
          </button>

          <button
            className="w-full text-left border rounded px-4 py-3 hover:bg-blue-50 hover:border-blue-300 transition-colors"
            onClick={() => setChoice("cas")}
          >
            <div className="font-medium">Mutual Fund CAS</div>
            <div className="text-xs text-gray-500">
              Import a Consolidated Account Statement (CAMS / KFintech / MFCentral)
            </div>
          </button>
        </div>

        <DialogFooter>
          <div className="flex gap-3 justify-end w-full">
            <Button variant="outline" onClick={handleClose}>
              Cancel
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Modal>
  );
}
