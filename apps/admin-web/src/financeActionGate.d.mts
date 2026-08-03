export type FinanceActionGate = {
  tryEnter: () => boolean;
  leave: () => void;
};

export function createFinanceActionGate(): FinanceActionGate;
