export type ContractMutationGate = {
  tryEnter(): boolean;
  leave(): void;
  isLocked(): boolean;
};

export declare const createContractMutationGate: () => ContractMutationGate;
